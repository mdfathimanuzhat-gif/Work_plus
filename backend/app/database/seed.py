"""Development-only seed data for Finance Company - Development.

Creates exactly four demo people. Login accounts are created when
DEV_SEED_PASSWORD is set. That value is never committed.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.models.organization import Organization
from app.models.rbac import EmployeeRole, Permission, Role
from app.models.team import Team
from app.repositories.user_account import get_account_by_email
from app.services.auth_service import create_account

logger = logging.getLogger(__name__)

DEV_ORGANIZATION_CODE = "FIN-DEV"
DEV_ORGANIZATION_NAME = "Finance Company - Development"

ROLE_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("ADMIN", "Organization administrator"),
    ("HR", "Human resources; organization-wide people and access management"),
    ("TEAM_LEAD", "Lead of an assigned team"),
    ("EMPLOYEE", "Individual contributor; own records only"),
)

PERMISSION_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("employee.view_own", "View own employee profile"),
    ("employee.view_team", "View employees on the assigned team"),
    ("employee.manage_organization", "Manage employees across the organization"),
    ("attendance.view_own", "View own attendance"),
    ("attendance.view_team", "View assigned team attendance"),
    ("attendance.view_organization", "View organization-wide attendance"),
    ("timesheet.manage_own", "Create and edit own timesheets"),
    ("timesheet.review_team", "Approve or reject assigned team timesheets"),
    ("timesheet.view_organization", "View organization-wide timesheets"),
    ("department.manage", "Manage departments"),
    ("team.manage", "Manage teams"),
    ("access.manage", "Manage roles and employee access"),
    ("report.view_organization", "View organization reports"),
    ("notification.view_own", "View own notifications"),
    ("audit.view_organization", "View organization audit logs"),
)

ROLE_PERMISSION_MAP: dict[str, tuple[str, ...]] = {
    "EMPLOYEE": (
        "employee.view_own",
        "attendance.view_own",
        "timesheet.manage_own",
        "notification.view_own",
    ),
    "TEAM_LEAD": (
        "employee.view_own",
        "employee.view_team",
        "attendance.view_own",
        "attendance.view_team",
        "timesheet.manage_own",
        "timesheet.review_team",
        "notification.view_own",
    ),
    "HR": (
        "employee.view_own",
        "employee.view_team",
        "employee.manage_organization",
        "attendance.view_own",
        "attendance.view_team",
        "attendance.view_organization",
        "timesheet.manage_own",
        "timesheet.review_team",
        "timesheet.view_organization",
        "department.manage",
        "team.manage",
        "access.manage",
        "report.view_organization",
        "notification.view_own",
        "audit.view_organization",
    ),
    "ADMIN": tuple(name for name, _description in PERMISSION_DEFINITIONS),
}


def _get_or_create_role(session: Session, name: str, description: str) -> Role:
    role = session.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name, description=description)
        session.add(role)
        session.flush()
    return role


def _get_or_create_permission(session: Session, name: str, description: str) -> Permission:
    permission = session.scalar(select(Permission).where(Permission.name == name))
    if permission is None:
        permission = Permission(name=name, description=description)
        session.add(permission)
        session.flush()
    return permission


def _get_or_create_department(
    session: Session,
    organization: Organization,
    *,
    name: str,
    code: str,
    description: str,
) -> Department:
    department = session.scalar(
        select(Department).where(
            Department.organization_id == organization.id,
            Department.code == code,
        )
    )
    if department is None:
        department = Department(
            organization_id=organization.id,
            name=name,
            code=code,
            description=description,
            is_active=True,
        )
        session.add(department)
        session.flush()
        return department
    department.name = name
    department.description = description
    department.is_active = True
    session.flush()
    return department


def _get_or_create_team(
    session: Session,
    organization: Organization,
    *,
    name: str,
    description: str,
    department: Department,
) -> Team:
    team = session.scalar(
        select(Team).where(Team.organization_id == organization.id, Team.name == name)
    )
    if team is None:
        team = Team(
            organization_id=organization.id,
            department_id=department.id,
            name=name,
            description=description,
            is_active=True,
        )
        session.add(team)
        session.flush()
        return team
    team.department_id = department.id
    team.description = description
    team.is_active = True
    session.flush()
    return team


def _get_or_create_employee(
    session: Session,
    organization: Organization,
    *,
    employee_code: str,
    first_name: str,
    last_name: str,
    email: str,
    department: Department | None,
    team: Team | None,
    manager: Employee | None,
    role: Role,
) -> Employee:
    employee = session.scalar(
        select(Employee).where(
            Employee.organization_id == organization.id,
            Employee.employee_code == employee_code,
        )
    )
    if employee is None:
        employee = Employee(
            organization_id=organization.id,
            employee_code=employee_code,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=None,
            department_id=department.id if department else None,
            team_id=team.id if team else None,
            manager_id=manager.id if manager else None,
            joining_date=date(2024, 6, 1),
            employment_status=EmploymentStatus.ACTIVE,
            is_active=True,
        )
        session.add(employee)
        session.flush()
    else:
        employee.first_name = first_name
        employee.last_name = last_name
        employee.email = email
        employee.department_id = department.id if department else None
        employee.team_id = team.id if team else None
        employee.manager_id = manager.id if manager else None
        employee.is_active = True
        employee.employment_status = EmploymentStatus.ACTIVE
        session.flush()
    has_role = session.scalar(
        select(EmployeeRole).where(
            EmployeeRole.employee_id == employee.id,
            EmployeeRole.role_id == role.id,
        )
    )
    if has_role is None:
        session.add(EmployeeRole(employee_id=employee.id, role_id=role.id))
        session.flush()
    return employee


def seed_development_data(session: Session) -> Organization:
    """Insert idempotent finance-company demo data."""
    roles = {
        name: _get_or_create_role(session, name, description)
        for name, description in ROLE_DEFINITIONS
    }
    permissions = {
        name: _get_or_create_permission(session, name, description)
        for name, description in PERMISSION_DEFINITIONS
    }
    for role_name, permission_names in ROLE_PERMISSION_MAP.items():
        role = roles[role_name]
        current = {permission.name for permission in role.permissions}
        for permission_name in permission_names:
            if permission_name not in current:
                role.permissions.append(permissions[permission_name])

    organization = session.scalar(select(Organization).where(Organization.code == DEV_ORGANIZATION_CODE))
    if organization is None:
        organization = Organization(
            name=DEV_ORGANIZATION_NAME,
            code=DEV_ORGANIZATION_CODE,
            email="dev@finance.local",
            address="Development data only",
            timezone="UTC",
            is_active=True,
        )
        session.add(organization)
        session.flush()
    else:
        organization.name = DEV_ORGANIZATION_NAME

    department = _get_or_create_department(
        session,
        organization,
        name="Finance Operations",
        code="FINOPS",
        description="Finance operations department",
    )
    team = _get_or_create_team(
        session,
        organization,
        name="Finance Operations Team",
        description="Finance operations team",
        department=department,
    )

    hr = _get_or_create_employee(
        session,
        organization,
        employee_code="HR001",
        first_name="Sidrah",
        last_name="Hunain",
        email="sidrah.hunain@workpulse.local",
        department=department,
        team=None,
        manager=None,
        role=roles["HR"],
    )
    team_lead = _get_or_create_employee(
        session,
        organization,
        employee_code="EMP003",
        first_name="Nayab",
        last_name="Rasul",
        email="nayab.rasul@workpulse.local",
        department=department,
        team=team,
        manager=None,
        role=roles["TEAM_LEAD"],
    )
    team.team_lead_id = team_lead.id
    session.flush()

    _get_or_create_employee(
        session,
        organization,
        employee_code="EMP001",
        first_name="Israh",
        last_name="Zunain",
        email="israh.zunain@workpulse.local",
        department=department,
        team=team,
        manager=team_lead,
        role=roles["EMPLOYEE"],
    )
    _get_or_create_employee(
        session,
        organization,
        employee_code="EMP002",
        first_name="Sameer",
        last_name="",
        email="sameer@workpulse.local",
        department=department,
        team=team,
        manager=team_lead,
        role=roles["EMPLOYEE"],
    )

    _seed_development_accounts(session, organization)
    logger.info(
        "Ensured demo organization %s with HR %s and team lead %s",
        DEV_ORGANIZATION_CODE,
        hr.employee_code,
        team_lead.employee_code,
    )
    return organization


def _seed_development_accounts(session: Session, organization: Organization) -> None:
    password = get_settings().DEV_SEED_PASSWORD
    if not password:
        logger.info("DEV_SEED_PASSWORD is not set; skipping login accounts")
        return
    employees = list(session.scalars(select(Employee).where(Employee.organization_id == organization.id)))
    for employee in employees:
        if get_account_by_email(session, employee.email) is not None:
            continue
        create_account(
            session,
            employee_id=employee.id,
            email=employee.email,
            password=password,
        )
    logger.info("Ensured development login accounts for organization %s", organization.code)
