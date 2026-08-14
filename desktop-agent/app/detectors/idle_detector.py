"""Idle start/end from the Windows last-input tick count.

GetLastInputInfo reports the tick of the last keyboard or mouse input. This
module never records keystrokes, mouse coordinates, or screen content — only
whether the idle threshold has been crossed.

Polling is required: Windows does not raise an event when the user becomes idle.
The poll interval is configurable and independent of the idle threshold.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from typing import Protocol

from app.models import EventType

logger = logging.getLogger("workpulse.agent.idle")

RecordFn = Callable[..., object]


class IdleClock(Protocol):
    def idle_seconds(self) -> float: ...


class WindowsIdleClock:
    """Read idle time via user32.GetLastInputInfo (Windows only)."""

    def idle_seconds(self) -> float:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            raise OSError("GetLastInputInfo failed")
        tick = ctypes.windll.kernel32.GetTickCount()
        elapsed_ms = (tick - info.dwTime) & 0xFFFFFFFF
        return elapsed_ms / 1000.0


class IdleDetector:
    """Emit IDLE_START / IDLE_END when crossing the configured threshold."""

    def __init__(
        self,
        *,
        threshold_seconds: int,
        poll_interval_seconds: float,
        record: RecordFn,
        clock: IdleClock | None = None,
        is_locked: Callable[[], bool] | None = None,
    ) -> None:
        self._threshold = threshold_seconds
        self._poll_interval = poll_interval_seconds
        self._record = record
        self._clock = clock
        self._is_locked = is_locked or (lambda: False)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._idle = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="workpulse-idle", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self._poll_interval + 1)

    def poll_once(self) -> None:
        """Evaluate idle state once. Used by tests and the background loop."""
        try:
            idle_seconds = self._clock_seconds()
        except Exception:
            logger.exception("Idle time query failed")
            return
        try:
            locked = bool(self._is_locked())
        except Exception:
            logger.exception("Lock-state probe failed")
            locked = False
        if locked:
            if self._idle:
                self._idle = False
                self._safe_record(EventType.IDLE_END, reason="session_locked")
            return
        if not self._idle and idle_seconds >= self._threshold:
            self._idle = True
            self._safe_record(EventType.IDLE_START, idle_seconds=round(idle_seconds, 1))
        elif self._idle and idle_seconds < self._threshold:
            self._idle = False
            self._safe_record(EventType.IDLE_END)

    def _clock_seconds(self) -> float:
        clock = self._clock
        if clock is None:
            if sys.platform != "win32":
                raise RuntimeError("Windows idle clock is unavailable on this platform")
            clock = WindowsIdleClock()
            self._clock = clock
        return clock.idle_seconds()

    def _safe_record(self, event_type: EventType, **metadata: object) -> None:
        try:
            self._record(event_type, metadata=metadata or None, source="idle")
        except Exception:
            logger.exception("Failed to record %s", event_type.value)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self._poll_interval)
