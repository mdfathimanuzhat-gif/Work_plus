"""Department routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.database.session import get_db
from app.schemas.org import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[DepartmentResponse]:
    departments = department_service.list_visible_departments(session, user)
    return [department_service.serialize_department(department) for department in departments]


@router.post("", response_model=DepartmentResponse, status_code=201)
def create_department(
    body: DepartmentCreate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> DepartmentResponse:
    department = department_service.create_department(session, user, body)
    session.commit()
    return department_service.serialize_department(department)


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: uuid.UUID,
    body: DepartmentUpdate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
) -> DepartmentResponse:
    department = department_service.update_department(session, user, department_id, body)
    session.commit()
    return department_service.serialize_department(department)
