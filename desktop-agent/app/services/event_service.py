"""Record attendance-related system events with de-duplication.

This service does not calculate worked time, talk to FastAPI, or write to
PostgreSQL. Detectors call `record()`; unexpected sequences are logged and
still stored so the agent does not crash.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from app.device import DeviceIdentity
from app.logger import log_event_line
from app.models import AgentEvent, EventType

Listener = Callable[[AgentEvent], None]
logger = logging.getLogger("workpulse.agent.events.service")


@dataclass
class SessionSnapshot:
    logged_in: bool = False
    locked: bool = False
    idle: bool = False
    sleeping: bool = False
    powering_off: bool = False


@dataclass
class EventService:
    device: DeviceIdentity
    _state: SessionSnapshot = field(default_factory=SessionSnapshot)
    _events: list[AgentEvent] = field(default_factory=list)
    _listeners: list[Listener] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    @property
    def events(self) -> list[AgentEvent]:
        with self._lock:
            return list(self._events)

    @property
    def state(self) -> SessionSnapshot:
        with self._lock:
            return SessionSnapshot(
                logged_in=self._state.logged_in,
                locked=self._state.locked,
                idle=self._state.idle,
                sleeping=self._state.sleeping,
                powering_off=self._state.powering_off,
            )

    def record(
        self,
        event_type: EventType,
        *,
        metadata: dict | None = None,
        source: str = "detector",
    ) -> AgentEvent | None:
        """Record an event unless it duplicates the current state."""
        extra = dict(metadata or {})
        extra.setdefault("source", source)
        with self._lock:
            if self._is_duplicate(event_type):
                logger.info("Ignoring duplicate %s", event_type.value)
                return None
            anomaly = self._anomaly_for(event_type)
            if anomaly:
                extra["anomaly"] = anomaly
                logger.warning("Unexpected sequence: %s (%s)", event_type.value, anomaly)
            event = AgentEvent.create(
                event_type,
                device_identifier=self.device.device_identifier,
                device_name=self.device.device_name,
                operating_system=self.device.operating_system,
                username=self.device.username,
                metadata=extra,
            )
            self._apply_state(event_type)
            self._events.append(event)
        self._persist(event)
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:
                logger.exception("Event listener failed for %s", event.event_id)
        return event

    def _is_duplicate(self, event_type: EventType) -> bool:
        state = self._state
        if event_type is EventType.WINDOWS_LOGIN:
            return state.logged_in
        if event_type is EventType.WINDOWS_LOGOUT:
            return (not state.logged_in) and any(
                item.event_type is EventType.WINDOWS_LOGOUT for item in self._events
            )
        if event_type is EventType.SYSTEM_LOCK:
            return state.locked
        if event_type is EventType.SYSTEM_UNLOCK:
            return (not state.locked) and self._last_type() is EventType.SYSTEM_UNLOCK
        if event_type is EventType.SYSTEM_SLEEP:
            return state.sleeping
        if event_type is EventType.SYSTEM_WAKE:
            return (not state.sleeping) and self._last_type() is EventType.SYSTEM_WAKE
        if event_type is EventType.IDLE_START:
            return state.idle
        if event_type is EventType.IDLE_END:
            return (not state.idle) and self._last_type() is EventType.IDLE_END
        if event_type is EventType.SYSTEM_SHUTDOWN:
            return self._last_type() is EventType.SYSTEM_SHUTDOWN
        if event_type is EventType.SYSTEM_RESTART:
            return self._last_type() is EventType.SYSTEM_RESTART
        return False

    def _last_type(self) -> EventType | None:
        if not self._events:
            return None
        return self._events[-1].event_type

    def _anomaly_for(self, event_type: EventType) -> str | None:
        state = self._state
        if event_type is EventType.SYSTEM_UNLOCK and not state.locked:
            return "unlock_without_lock"
        if event_type is EventType.WINDOWS_LOGOUT and not state.logged_in:
            return "logout_without_login"
        if event_type is EventType.SYSTEM_SHUTDOWN and state.logged_in:
            return "shutdown_without_logout"
        if event_type is EventType.SYSTEM_RESTART and state.logged_in:
            return "restart_without_logout"
        if event_type is EventType.SYSTEM_WAKE and not state.sleeping:
            return "wake_without_sleep"
        if event_type is EventType.SYSTEM_SLEEP and not state.logged_in:
            return "sleep_without_login"
        if event_type is EventType.IDLE_END and not state.idle:
            return "idle_end_without_idle_start"
        if event_type is EventType.SYSTEM_UNLOCK and not state.logged_in:
            return "unlock_without_login"
        return None

    def _apply_state(self, event_type: EventType) -> None:
        if event_type is EventType.WINDOWS_LOGIN:
            self._state.logged_in = True
            self._state.powering_off = False
        elif event_type is EventType.WINDOWS_LOGOUT:
            self._state.logged_in = False
            self._state.locked = False
            self._state.idle = False
        elif event_type is EventType.SYSTEM_LOCK:
            self._state.locked = True
        elif event_type is EventType.SYSTEM_UNLOCK:
            self._state.locked = False
        elif event_type is EventType.SYSTEM_SLEEP:
            self._state.sleeping = True
        elif event_type is EventType.SYSTEM_WAKE:
            self._state.sleeping = False
        elif event_type is EventType.IDLE_START:
            self._state.idle = True
        elif event_type is EventType.IDLE_END:
            self._state.idle = False
        elif event_type in {EventType.SYSTEM_SHUTDOWN, EventType.SYSTEM_RESTART}:
            self._state.powering_off = True
            self._state.logged_in = False
            self._state.locked = False
            self._state.idle = False
            self._state.sleeping = False

    def _persist(self, event: AgentEvent) -> None:
        try:
            log_event_line(event)
        except Exception:
            logger.exception("Failed to write event log for %s", event.event_id)
