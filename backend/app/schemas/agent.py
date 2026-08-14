"""Pydantic schemas for desktop-agent enrollment and event ingestion."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AttendanceEventType

AGENT_EVENT_TYPES = (
    "WINDOWS_LOGIN",
    "WINDOWS_LOGOUT",
    "SYSTEM_LOCK",
    "SYSTEM_UNLOCK",
    "SYSTEM_SHUTDOWN",
    "SYSTEM_RESTART",
    "SYSTEM_SLEEP",
    "SYSTEM_WAKE",
    "IDLE_START",
    "IDLE_END",
)

AGENT_TO_SERVER_EVENT: dict[str, AttendanceEventType] = {
    "WINDOWS_LOGIN": AttendanceEventType.LOGIN,
    "WINDOWS_LOGOUT": AttendanceEventType.LOGOUT,
    "SYSTEM_LOCK": AttendanceEventType.LOCK,
    "SYSTEM_UNLOCK": AttendanceEventType.UNLOCK,
    "SYSTEM_SHUTDOWN": AttendanceEventType.SHUTDOWN,
    "SYSTEM_RESTART": AttendanceEventType.RESTART,
    "SYSTEM_SLEEP": AttendanceEventType.SLEEP,
    "SYSTEM_WAKE": AttendanceEventType.WAKE,
    "IDLE_START": AttendanceEventType.IDLE_START,
    "IDLE_END": AttendanceEventType.IDLE_END,
}


class DeviceEnrollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_identifier: str = Field(min_length=1, max_length=255)
    device_name: str = Field(min_length=1, max_length=255)
    operating_system: str | None = Field(default=None, max_length=100)


class DeviceEnrollResponse(BaseModel):
    device_id: uuid.UUID
    device_identifier: str
    device_secret: str
    message: str = "Store the device secret locally. It is not shown again."


class DeviceTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_identifier: str = Field(min_length=1, max_length=255)
    device_secret: str = Field(min_length=1, max_length=512)


class DeviceTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AgentEventItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID
    event_type: str
    event_timestamp: datetime
    device_identifier: str = Field(min_length=1, max_length=255)
    device_name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def event_type_must_be_known(cls, value: str) -> str:
        name = value.strip().upper()
        if name not in AGENT_EVENT_TYPES:
            raise ValueError("Invalid event type")
        return name

    @field_validator("event_timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_timestamp must include a timezone (UTC)")
        return value.astimezone(timezone.utc)

    @field_validator("metadata")
    @classmethod
    def metadata_must_be_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        blocked = {"password", "password_hash", "token", "secret", "jwt"}
        return {key: item for key, item in value.items() if key.lower() not in blocked}


class AgentEventBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=255)
    events: list[AgentEventItem] = Field(min_length=1)


class AgentEventResult(BaseModel):
    event_id: uuid.UUID
    status: Literal["accepted", "duplicate", "failed"]
    reason: str | None = None


class AgentEventBatchResponse(BaseModel):
    accepted: int
    duplicates: int
    failed: int
    results: list[AgentEventResult]
