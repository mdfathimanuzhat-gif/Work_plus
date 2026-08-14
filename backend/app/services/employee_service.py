"""Employee management use cases with server-side data isolation."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.models.rbac import EmployeeRole
from app.repositories import department as department_repository
from app.repositories import employee as employee_repository
from app.repositories import role as role_repository
from app.repositories import team as team_repository
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.auth_service import create_account
from app.services.authorization import (
    AuthenticatedUser,
    can_assign_roles,
    can_manage_employees,
    can_view_employee,
    ensure_can_view_employee,
    has_permission,
)

_SELF_ALLOWED_FIELDS = {"first_name", "last_name", "phone"}


def serialize_employee(employee: Employee) -> EmployeeResponse:
    manager = employee.manager
    account = employee.account
    if account is None:
        account_status = "NONE"
    elif account.is_active:
        account_status = "ACTIVE"
    else:
        account_status = "INACTIVE"
    roles = [assignment.role.name for assignment in employee.employee_roles]
    manager_name = f"{manager.first_name} {manager.last_name}" if manager else None
    return EmployeeResponse(
        id=employee.id,
        organization_id=employee.organization_id,
        employee_code=employee.employee_code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        phone=employee.phone,
        department_id=employee.department_id,
        department_name=employee.department.name if employee.department else None,
        team_id=employee.team_id,
        team_name=employee.team.name if employee.team else None,
        manager_id=employee.manager_id,
        manager_name=manager_name,
        joining_date=employee.joining_date,
        employment_status=employee.employment_status,
        is_active=employee.is_active,
        account_status=account_status,
        roles=roles,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def get_visible_employee(session: Session, user: AuthenticatedUser, employee_id: uuid.UUID) -> Employee:
    target = employee_repository.get_employee_by_id(session, employee_id)
    return ensure_can_view_employee(user, target)


def list_visible_employees(
    session: Session,
    user: AuthenticatedUser,
    *,
    search: str | None = None,
    department_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    employment_status: EmploymentStatus | None = None,
    is_active: bool | None = None,
) -> list[Employee]:
    if can_manage_employees(user):
        employees = employee_repository.search_employees(
            session,
            user.organization_id,
            search=search,
            department_id=department_id,
            team_id=team_id,
            employment_status=employment_status,
            is_active=is_active,
        )
        return employees

    if has_permission(user, "employee.view_team"):
        employees = employee_repository.search_employees(
            session,
            user.organization_id,
            search=search,
            department_id=department_id,
            team_id=team_id,
            employment_status=employment_status,
            is_active=is_active,
        )
        return [employee for employee in employees if can_view_employee(user, employee)]

    if has_permission(user, "employee.view_own"):
        employee = employee_repository.get_employee_by_id(session, user.employee_id)
        return [employee] if employee is not None else []

    raise APIError(403, "forbidden", "You do not have access to the employee directory")


def _validate_department(session: Session, user: AuthenticatedUser, department_id: uuid.UUID):
    department = department_repository.get_department_by_id(session, department_id)
    if department is None or department.organization_id != user.organization_id:
        raise APIError(400, "invalid_department", "Department is invalid for this organization")
    if not department.is_active:
        raise APIError(400, "invalid_department", "Department is inactive")
    return department


def _validate_team(session: Session, user: AuthenticatedUser, team_id: uuid.UUID, department_id: uuid.UUID | None):
    team = team_repository.get_team_by_id(session, team_id)
    if team is None or team.organization_id != user.organization_id:
        raise APIError(400, "invalid_team", "Team is invalid for this organization")
    if not team.is_active:
        raise APIError(400, "invalid_team", "Cannot assign an inactive team")
    if department_id is not None and team.department_id is not None and team.department_id != department_id:
        raise APIError(400, "invalid_team", "Team does not belong to the selected department")
    return team


def _role_names(employee: Employee) -> set[str]:
    return {assignment.role.name for assignment in employee.employee_roles}


def _validate_manager(session: Session, user: AuthenticatedUser, manager_id: uuid.UUID) -> Employee:
    manager = employee_repository.get_employee_by_id(session, manager_id)
    if manager is None or manager.organization_id != user.organization_id:
        raise APIError(400, "invalid_manager", "Reporting manager is invalid for this organization")
    if not manager.is_active:
        raise APIError(400, "invalid_manager", "Reporting manager is inactive")
    if not _role_names(manager).intersection({"TEAM_LEAD", "ADMIN"}):
        raise APIError(400, "invalid_manager", "Reporting manager must be a Team Lead")
    return manager


def _assign_role(session: Session, employee: Employee, role_name: str) -> None:
    role = role_repository.get_role_by_name(session, role_name)
    if role is None:
        raise APIError(400, "invalid_role", "Role is invalid")
    employee.employee_roles.clear()
    session.flush()
    session.add(EmployeeRole(employee_id=employee.id, role_id=role.id))


def create_employee(session: Session, user: AuthenticatedUser, payload: EmployeeCreate) -> Employee:
    if not can_manage_employees(user):
        raise APIError(403, "forbidden", "You do not have access to this resource")
    if payload.role != "EMPLOYEE" and not can_assign_roles(user):
        raise APIError(403, "forbidden", "You cannot assign this role")

    department_id = payload.department_id
    team_id = payload.team_id
    if department_id is not None:
        _validate_department(session, user, department_id)
    if team_id is not None:
        team = _validate_team(session, user, team_id, department_id)
        if department_id is None and team.department_id is not None:
            department_id = team.department_id
    if payload.manager_id is not None:
        _validate_manager(session, user, payload.manager_id)

    if employee_repository.get_employee_by_code(session, user.organization_id, payload.employee_code):
        raise APIError(409, "duplicate_employee_code", "Employee code already exists in this organization")
    if employee_repository.get_employee_by_email(session, user.organization_id, payload.email):
        raise APIError(409, "duplicate_email", "Email already exists in this organization")

    employee = Employee(
        organization_id=user.organization_id,
        employee_code=payload.employee_code,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=payload.email,
        phone=payload.phone,
        department_id=department_id,
        team_id=team_id,
        manager_id=payload.manager_id,
        joining_date=payload.joining_date,
        employment_status=payload.employment_status,
        is_active=payload.employment_status != EmploymentStatus.TERMINATED,
    )
    session.add(employee)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise APIError(409, "duplicate_employee", "Employee code or email already exists") from exc

    _assign_role(session, employee, payload.role)
    if payload.password:
        create_account(
            session,
            employee_id=employee.id,
            email=payload.email,
            password=payload.password,
        )
    return employee_repository.get_employee_by_id(session, employee.id) or employee


def update_employee(
    session: Session,
    user: AuthenticatedUser,
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
) -> Employee:
    target = get_visible_employee(session, user, employee_id)
    updates = payload.model_dump(exclude_unset=True)
    is_self = target.id == user.employee_id
    managing = can_manage_employees(user)

    if not managing:
        if not is_self:
            raise APIError(403, "forbidden", "You cannot modify another employee")
        disallowed = set(updates) - _SELF_ALLOWED_FIELDS
        if disallowed:
            raise APIError(403, "forbidden", "You cannot change that profile field")
    elif "role" in updates and not can_assign_roles(user):
        raise APIError(403, "forbidden", "You cannot assign this role")

    department_id = updates.get("department_id", target.department_id)
    team_id = updates.get("team_id", target.team_id)
    if "department_id" in updates and updates["department_id"] is not None:
        _validate_department(session, user, updates["department_id"])
    if "team_id" in updates and updates["team_id"] is not None:
        _validate_team(session, user, updates["team_id"], department_id)
    if "manager_id" in updates and updates["manager_id"] is not None:
        if updates["manager_id"] == target.id:
            raise APIError(400, "invalid_manager", "An employee cannot report to themselves")
        _validate_manager(session, user, updates["manager_id"])
    if "email" in updates and updates["email"] != target.email:
        existing = employee_repository.get_employee_by_email(session, user.organization_id, updates["email"])
        if existing is not None and existing.id != target.id:
            raise APIError(409, "duplicate_email", "Email already exists in this organization")

    role_name = updates.pop("role", None)
    for field, value in updates.items():
        setattr(target, field, value.strip() if isinstance(value, str) and field != "email" else value)
    if role_name:
        _assign_role(session, target, role_name)
    if target.account is not None and "email" in updates:
        target.account.email = target.email
    if target.account is not None and "is_active" in updates:
        target.account.is_active = bool(target.is_active)
    try:
        session.flush()
    except IntegrityError as exc:
        raise APIError(409, "duplicate_employee", "Employee code or email already exists") from exc
    return employee_repository.get_employee_by_id(session, target.id) or target


def deactivate_employee(session: Session, user: AuthenticatedUser, employee_id: uuid.UUID) -> Employee:
    if not can_manage_employees(user):
        raise APIError(403, "forbidden", "You do not have access to this resource")
    target = get_visible_employee(session, user, employee_id)
    target.is_active = False
    target.employment_status = EmploymentStatus.INACTIVE
    if target.account is not None:
        target.account.is_active = False
    session.flush()
    return employee_repository.get_employee_by_id(session, target.id) or target
