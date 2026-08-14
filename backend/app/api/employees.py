"""Employee profile routes with server-side data isolation."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.database.session import get_db
from app.schemas.employee import EmployeeResponse
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[EmployeeResponse]:
    employees = employee_service.list_visible_employees(session, user)
    return [EmployeeResponse.model_validate(employee) for employee in employees]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: uuid.UUID,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> EmployeeResponse:
    employee = employee_service.get_visible_employee(session, user, employee_id)
    return EmployeeResponse.model_validate(employee)
