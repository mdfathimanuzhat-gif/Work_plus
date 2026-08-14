"""Local attendance-event representation.

These records are stored in local SQLite and synchronized to the WorkPulse API
when connectivity allows. They are not used to calculate attendance totals yet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    WINDOWS_LOGIN = "WINDOWS_LOGIN"
    WINDOWS_LOGOUT = "WINDOWS_LOGOUT"
    SYSTEM_LOCK = "SYSTEM_LOCK"
    SYSTEM_UNLOCK = "SYSTEM_UNLOCK"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    SYSTEM_RESTART = "SYSTEM_RESTART"
    SYSTEM_SLEEP = "SYSTEM_SLEEP"
    SYSTEM_WAKE = "SYSTEM_WAKE"
    IDLE_START = "IDLE_START"
    IDLE_END = "IDLE_END"


# Test-mode aliases accepted by the simulator only.
EVENT_ALIASES: dict[str, EventType] = {
    "SYSTEM_LOGOUT": EventType.WINDOWS_LOGOUT,
    "LOGIN": EventType.WINDOWS_LOGIN,
    "LOGOUT": EventType.WINDOWS_LOGOUT,
    "LOCK": EventType.SYSTEM_LOCK,
    "UNLOCK": EventType.SYSTEM_UNLOCK,
    "SHUTDOWN": EventType.SYSTEM_SHUTDOWN,
    "RESTART": EventType.SYSTEM_RESTART,
    "SLEEP": EventType.SYSTEM_SLEEP,
    "WAKE": EventType.SYSTEM_WAKE,
}


def parse_event_type(value: str) -> EventType:
    """Parse a canonical event type or a documented test-mode alias."""
    key = value.strip().upper()
    if key in EVENT_ALIASES:
        return EVENT_ALIASES[key]
    return EventType(key)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(moment: datetime) -> str:
    """Return an ISO-8601 UTC timestamp with a Z suffix."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class AgentEvent:
    event_id: str
    event_type: EventType
    event_timestamp: datetime
    device_identifier: str
    device_name: str
    operating_system: str
    username: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: EventType,
        *,
        device_identifier: str,
        device_name: str,
        operating_system: str,
        username: str,
        metadata: dict[str, Any] | None = None,
        event_timestamp: datetime | None = None,
        event_id: str | None = None,
    ) -> AgentEvent:
        return cls(
            event_id=event_id or str(uuid.uuid4()),
            event_type=event_type,
            event_timestamp=event_timestamp or utc_now(),
            device_identifier=device_identifier,
            device_name=device_name,
            operating_system=operating_system,
            username=username,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_timestamp": format_utc(self.event_timestamp),
            "device_identifier": self.device_identifier,
            "device_name": self.device_name,
            "operating_system": self.operating_system,
            "username": self.username,
            "metadata": self.metadata,
        }
