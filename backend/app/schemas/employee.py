"""Employee API schemas. Password hashes are never included."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import EmploymentStatus


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
    team_id: uuid.UUID | None
    manager_id: uuid.UUID | None
    joining_date: date | None
    employment_status: EmploymentStatus
    is_active: bool
