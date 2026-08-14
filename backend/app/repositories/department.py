"""Department persistence helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department


def get_department_by_id(session: Session, department_id: uuid.UUID) -> Department | None:
    return session.get(Department, department_id)


def get_department_by_code(
    session: Session, organization_id: uuid.UUID, code: str
) -> Department | None:
    return session.scalar(
        select(Department).where(
            Department.organization_id == organization_id,
            Department.code == code,
        )
    )


def list_departments(session: Session, organization_id: uuid.UUID) -> list[Department]:
    statement = (
        select(Department)
        .where(Department.organization_id == organization_id)
        .order_by(Department.name)
    )
    return list(session.scalars(statement))
