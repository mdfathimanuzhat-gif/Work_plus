"""Employee data-access helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee


def get_employee_by_id(session: Session, employee_id: uuid.UUID) -> Employee | None:
    return session.get(Employee, employee_id)


def list_employees_in_organization(session: Session, organization_id: uuid.UUID) -> list[Employee]:
    statement = (
        select(Employee)
        .where(Employee.organization_id == organization_id)
        .order_by(Employee.employee_code)
    )
    return list(session.scalars(statement))


def list_employees_on_team(session: Session, team_id: uuid.UUID) -> list[Employee]:
    statement = (
        select(Employee)
        .where(Employee.team_id == team_id)
        .order_by(Employee.employee_code)
    )
    return list(session.scalars(statement))
