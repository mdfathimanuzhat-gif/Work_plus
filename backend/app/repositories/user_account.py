"""User account persistence helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import Employee
from app.models.rbac import EmployeeRole, Role
from app.models.user_account import UserAccount


def get_account_by_email(session: Session, email: str) -> UserAccount | None:
    statement = select(UserAccount).where(func.lower(UserAccount.email) == email.lower())
    return session.scalar(statement)


def get_account_by_id(session: Session, account_id: uuid.UUID) -> UserAccount | None:
    return session.get(UserAccount, account_id)


def get_account_with_authorization(session: Session, account_id: uuid.UUID) -> UserAccount | None:
    statement = (
        select(UserAccount)
        .options(
            selectinload(UserAccount.employee)
            .selectinload(Employee.employee_roles)
            .selectinload(EmployeeRole.role)
            .selectinload(Role.permissions),
            selectinload(UserAccount.employee).selectinload(Employee.led_teams),
        )
        .where(UserAccount.id == account_id)
    )
    return session.scalar(statement)
