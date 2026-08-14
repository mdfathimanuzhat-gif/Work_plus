"""Employee API schemas. Password hashes are never included."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EmploymentStatus


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@") or " " in email:
        raise ValueError("Invalid email")
    return email


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    department_id: uuid.UUID | None
    department_name: str | None = None
    team_id: uuid.UUID | None
    team_name: str | None = None
    manager_id: uuid.UUID | None
    manager_name: str | None = None
    joining_date: date | None
    employment_status: EmploymentStatus
    is_active: bool
    account_status: str
    roles: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    email: str
    phone: str | None = Field(default=None, max_length=50)
    department_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    joining_date: date | None = None
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    role: str = "EMPLOYEE"
    password: str | None = None

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("employee_code")
    @classmethod
    def code_must_be_stripped(cls, value: str) -> str:
        return value.strip()

    @field_validator("role")
    @classmethod
    def role_must_be_known(cls, value: str) -> str:
        return value.strip().upper()


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = None
    department_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    joining_date: date | None = None
    employment_status: EmploymentStatus | None = None
    is_active: bool | None = None
    role: str | None = None

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _normalize_email(value)

    @field_validator("role")
    @classmethod
    def role_must_be_known(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()
