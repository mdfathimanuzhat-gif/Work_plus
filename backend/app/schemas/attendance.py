"""Pydantic schemas for calculated attendance. Durations are integer seconds."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AttendanceEventType, AttendanceSessionStatus, AttendanceStatus
from app.services.attendance_engine import WorkState


class AttendanceSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attendance_id: uuid.UUID
    employee_id: uuid.UUID
    device_id: uuid.UUID | None
    session_start: datetime
    session_end: datetime | None
    session_duration_seconds: int
    locked_seconds: int
    idle_seconds: int
    sleep_seconds: int
    active_seconds: int
    status: AttendanceSessionStatus
    ended_reason: str | None


class AttendanceAnomalyResponse(BaseModel):
    code: str
    message: str
    event_time: datetime
    event_type: str


class AttendanceDayResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    attendance_date: date
    first_login_time: datetime | None
    last_logout_time: datetime | None
    total_session_seconds: int
    total_locked_seconds: int
    total_idle_seconds: int
    total_sleep_seconds: int
    total_active_seconds: int
    session_count: int
    status: AttendanceStatus
    is_complete: bool
    calculated_at: datetime | None
    anomalies: list[AttendanceAnomalyResponse] = Field(default_factory=list)
    sessions: list[AttendanceSessionResponse] = Field(default_factory=list)


class LiveAttendanceResponse(BaseModel):
    employee_id: uuid.UUID
    state: WorkState
    as_of: datetime
    attendance_date: date
    timezone: str


class TeamAttendanceResponse(BaseModel):
    attendance_date: date
    records: list[AttendanceDayResponse]


class AttendanceEventOut(BaseModel):
    event_type: AttendanceEventType
    event_timestamp: datetime
    device_id: uuid.UUID | None
    device_name: str | None = None
