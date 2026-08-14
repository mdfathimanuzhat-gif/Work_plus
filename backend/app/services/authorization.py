"""Authenticated principal and reusable authorization checks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.errors import APIError
from app.models.employee import Employee
from app.models.user_account import UserAccount

ROLE_PRIORITY = ("ADMIN", "HR", "TEAM_LEAD", "EMPLOYEE")


@dataclass(frozen=True)
class AuthenticatedUser:
    account: UserAccount
    employee: Employee
    roles: tuple[str, ...]
    permissions: frozenset[str]

    @property
    def account_id(self) -> uuid.UUID:
        return self.account.id

    @property
    def employee_id(self) -> uuid.UUID:
        return self.employee.id

    @property
    def organization_id(self) -> uuid.UUID:
        return self.employee.organization_id

    @property
    def primary_role(self) -> str:
        return primary_role(self.roles)

    @property
    def led_team_ids(self) -> frozenset[uuid.UUID]:
        return frozenset(team.id for team in self.employee.led_teams)


def primary_role(roles: tuple[str, ...] | list[str]) -> str:
    role_set = set(roles)
    for name in ROLE_PRIORITY:
        if name in role_set:
            return name
    return next(iter(roles), "EMPLOYEE")


def has_role(user: AuthenticatedUser, *role_names: str) -> bool:
    allowed = {name.upper() for name in role_names}
    return any(role in allowed for role in user.roles)


def has_permission(user: AuthenticatedUser, *permission_names: str) -> bool:
    return any(name in user.permissions for name in permission_names)


def require_role(user: AuthenticatedUser, *role_names: str) -> None:
    if not has_role(user, *role_names):
        raise APIError(403, "forbidden", "You do not have access to this resource")


def require_permission(user: AuthenticatedUser, *permission_names: str) -> None:
    if not has_permission(user, *permission_names):
        raise APIError(403, "forbidden", "You do not have access to this resource")


def can_view_employee(user: AuthenticatedUser, target: Employee) -> bool:
    if target.organization_id != user.organization_id:
        return False
    if has_role(user, "ADMIN") or has_permission(user, "employee.manage_organization"):
        return True
    if target.id == user.employee_id and has_permission(user, "employee.view_own"):
        return True
    if has_permission(user, "employee.view_team"):
        if user.employee.team_id is not None and target.team_id == user.employee.team_id:
            return True
        if target.team_id is not None and target.team_id in user.led_team_ids:
            return True
    return False


def ensure_can_view_employee(user: AuthenticatedUser, target: Employee | None) -> Employee:
    if target is None or target.organization_id != user.organization_id:
        raise APIError(404, "not_found", "Employee not found")
    if not can_view_employee(user, target):
        raise APIError(403, "forbidden", "You do not have access to this employee")
    return target
