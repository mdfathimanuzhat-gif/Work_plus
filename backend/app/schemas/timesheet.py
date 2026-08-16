"""Timesheet and approval request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TimesheetApprovalStatus, TimesheetStatus


class TimesheetCreate(BaseModel):
    date: date
    project: str = Field(min_length=1, max_length=255)
    task: str = Field(min_length=1, max_length=255)
    description: str | None = None
    hours: Decimal = Field(ge=0, le=Decimal("9999.99"), decimal_places=2)


class TimesheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    date: date
    project: str
    task: str
    description: str | None
    hours: Decimal
    status: TimesheetStatus
    submitted_at: datetime | None
    created_at: datetime


class TimesheetApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timesheet_id: uuid.UUID
    reviewer_id: uuid.UUID
    status: TimesheetApprovalStatus
    comments: str | None
    reviewed_at: datetime | None


class TimesheetDetailOut(TimesheetOut):
    approvals: list[TimesheetApprovalOut] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    status: TimesheetApprovalStatus
    comments: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("status")
    @classmethod
    def require_decision(cls, value: TimesheetApprovalStatus) -> TimesheetApprovalStatus:
        if value not in (TimesheetApprovalStatus.APPROVED, TimesheetApprovalStatus.REJECTED):
            raise ValueError("status must be APPROVED or REJECTED")
        return value
