"""Department management use cases."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.department import Department
from app.repositories import department as department_repository
from app.schemas.org import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services.authorization import (
    AuthenticatedUser,
    can_manage_departments,
    can_view_department,
)


def serialize_department(department: Department) -> DepartmentResponse:
    return DepartmentResponse.model_validate(department)


def list_visible_departments(session: Session, user: AuthenticatedUser) -> list[Department]:
    departments = department_repository.list_departments(session, user.organization_id)
    return [department for department in departments if can_view_department(user, department.id)]


def create_department(session: Session, user: AuthenticatedUser, payload: DepartmentCreate) -> Department:
    if not can_manage_departments(user):
        raise APIError(403, "forbidden", "You do not have access to this resource")
    code = payload.code.strip().upper()
    if department_repository.get_department_by_code(session, user.organization_id, code):
        raise APIError(409, "duplicate_department", "Department code already exists")
    department = Department(
        organization_id=user.organization_id,
        name=payload.name.strip(),
        code=code,
        description=payload.description,
        is_active=True,
    )
    session.add(department)
    try:
        session.flush()
    except IntegrityError as exc:
        raise APIError(409, "duplicate_department", "Department code already exists") from exc
    return department


def update_department(
    session: Session,
    user: AuthenticatedUser,
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
) -> Department:
    if not can_manage_departments(user):
        raise APIError(403, "forbidden", "You do not have access to this resource")
    department = department_repository.get_department_by_id(session, department_id)
    if department is None or department.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Department not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(department, field, value.strip() if isinstance(value, str) else value)
    session.flush()
    return department
