"""Employee profile and directory routes with server-side data isolation."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.database.session import get_db
from app.models.enums import EmploymentStatus
from app.schemas.auth import MessageResponse
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
    search: str | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    team_id: uuid.UUID | None = Query(default=None),
    employment_status: EmploymentStatus | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> list[EmployeeResponse]:
    employees = employee_service.list_visible_employees(
        session,
        user,
        search=search,
        department_id=department_id,
        team_id=team_id,
        employment_status=employment_status,
        is_active=is_active,
    )
    return [employee_service.serialize_employee(employee) for employee in employees]


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(
    body: EmployeeCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> EmployeeResponse:
    employee = employee_service.create_employee(session, user, body)
    session.commit()
    return employee_service.serialize_employee(employee)


@router.get("/me", response_model=EmployeeResponse)
def get_my_profile(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> EmployeeResponse:
    employee = employee_service.get_visible_employee(session, user, user.employee_id)
    return employee_service.serialize_employee(employee)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: uuid.UUID,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> EmployeeResponse:
    employee = employee_service.get_visible_employee(session, user, employee_id)
    return employee_service.serialize_employee(employee)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: uuid.UUID,
    body: EmployeeUpdate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> EmployeeResponse:
    employee = employee_service.update_employee(session, user, employee_id, body)
    session.commit()
    return employee_service.serialize_employee(employee)


@router.post("/{employee_id}/deactivate", response_model=MessageResponse)
def deactivate_employee(
    employee_id: uuid.UUID,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    employee_service.deactivate_employee(session, user, employee_id)
    session.commit()
    return MessageResponse(message="Employee deactivated")
