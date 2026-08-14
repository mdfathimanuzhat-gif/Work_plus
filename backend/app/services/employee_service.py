"""Employee query use cases with server-side data isolation."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.repositories import employee as employee_repository
from app.services.authorization import (
    AuthenticatedUser,
    can_view_employee,
    ensure_can_view_employee,
    has_permission,
    has_role,
    require_permission,
)


def get_visible_employee(session: Session, user: AuthenticatedUser, employee_id: uuid.UUID) -> Employee:
    target = employee_repository.get_employee_by_id(session, employee_id)
    return ensure_can_view_employee(user, target)


def list_visible_employees(session: Session, user: AuthenticatedUser) -> list[Employee]:
    require_permission(
        user,
        "employee.view_own",
        "employee.view_team",
        "employee.manage_organization",
    )
    if has_role(user, "ADMIN") or has_permission(user, "employee.manage_organization"):
        return employee_repository.list_employees_in_organization(session, user.organization_id)

    visible: dict[uuid.UUID, Employee] = {}
    if has_permission(user, "employee.view_own"):
        visible[user.employee_id] = user.employee

    team_ids: set[uuid.UUID] = set(user.led_team_ids)
    if has_permission(user, "employee.view_team") and user.employee.team_id is not None:
        team_ids.add(user.employee.team_id)
    for team_id in team_ids:
        for employee in employee_repository.list_employees_on_team(session, team_id):
            if can_view_employee(user, employee):
                visible[employee.id] = employee

    return sorted(visible.values(), key=lambda employee: employee.employee_code)
