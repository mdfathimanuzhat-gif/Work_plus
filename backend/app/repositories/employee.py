"""Employee data-access helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.models.rbac import EmployeeRole


def _detail_options() -> tuple:
    return (
        selectinload(Employee.department),
        selectinload(Employee.team),
        selectinload(Employee.manager),
        selectinload(Employee.account),
        selectinload(Employee.employee_roles).selectinload(EmployeeRole.role),
    )


def get_employee_by_id(session: Session, employee_id: uuid.UUID) -> Employee | None:
    return session.scalar(
        select(Employee).options(*_detail_options()).where(Employee.id == employee_id)
    )


def get_employee_by_code(
    session: Session, organization_id: uuid.UUID, employee_code: str
) -> Employee | None:
    return session.scalar(
        select(Employee).where(
            Employee.organization_id == organization_id,
            Employee.employee_code == employee_code,
        )
    )


def get_employee_by_email(
    session: Session, organization_id: uuid.UUID, email: str
) -> Employee | None:
    return session.scalar(
        select(Employee).where(
            Employee.organization_id == organization_id,
            Employee.email == email.lower(),
        )
    )


def list_employees_in_organization(session: Session, organization_id: uuid.UUID) -> list[Employee]:
    statement = (
        select(Employee)
        .options(*_detail_options())
        .where(Employee.organization_id == organization_id)
        .order_by(Employee.employee_code)
    )
    return list(session.scalars(statement).unique())


def list_employees_on_team(session: Session, team_id: uuid.UUID) -> list[Employee]:
    statement = (
        select(Employee)
        .options(*_detail_options())
        .where(Employee.team_id == team_id)
        .order_by(Employee.employee_code)
    )
    return list(session.scalars(statement).unique())


def search_employees(
    session: Session,
    organization_id: uuid.UUID,
    *,
    search: str | None = None,
    department_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    employment_status: EmploymentStatus | None = None,
    is_active: bool | None = None,
) -> list[Employee]:
    statement: Select[tuple[Employee]] = (
        select(Employee)
        .options(*_detail_options())
        .where(Employee.organization_id == organization_id)
    )
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Employee.employee_code.ilike(pattern),
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                Employee.email.ilike(pattern),
            )
        )
    if department_id is not None:
        statement = statement.where(Employee.department_id == department_id)
    if team_id is not None:
        statement = statement.where(Employee.team_id == team_id)
    if employment_status is not None:
        statement = statement.where(Employee.employment_status == employment_status)
    if is_active is not None:
        statement = statement.where(Employee.is_active == is_active)
    return list(session.scalars(statement.order_by(Employee.employee_code)).unique())
