"""Pydantic schemas for authentication requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@") or " " in email:
            raise ValueError("Invalid email")
        return email


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: uuid.UUID
    employee_id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    employee_code: str
    team_id: uuid.UUID | None
    department_id: uuid.UUID | None
    roles: list[str]
    permissions: list[str]
    last_login_at: datetime | None


class MessageResponse(BaseModel):
    message: str
