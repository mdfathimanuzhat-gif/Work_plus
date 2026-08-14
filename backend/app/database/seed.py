"""Development-only seed data.

Creates one organization, department, team, and employee placeholders
(HR, team lead, employee, admin) with roles and permissions.

Login accounts are created only when DEV_SEED_PASSWORD is set. That value is
read from the environment and is never committed.
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

DEV_ORGANIZATION_CODE = "WP-DEV"

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


def seed_development_data(session: Session) -> Organization:
    """Insert idempotent local-development reference data."""
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

    organization = session.scalar(
        select(Organization).where(Organization.code == DEV_ORGANIZATION_CODE)
    )
    if organization is not None:
        logger.info("Development organization %s already exists; ensuring people and accounts", DEV_ORGANIZATION_CODE)
        _ensure_admin_employee(session, organization, roles)
        _seed_development_accounts(session, organization)
        return organization

    organization = Organization(
        name="WorkPulse Development",
        code=DEV_ORGANIZATION_CODE,
        email="dev@workpulse.local",
        phone=None,
        address="Local development only",
        timezone="UTC",
        is_active=True,
    )
    session.add(organization)
    session.flush()

    department = Department(
        organization_id=organization.id,
        name="Engineering",
        code="ENG",
        description="Development department",
        is_active=True,
    )
    session.add(department)
    session.flush()

    team = Team(
        organization_id=organization.id,
        department_id=department.id,
        name="Platform",
        description="Platform team",
        is_active=True,
    )
    session.add(team)
    session.flush()

    hr_employee = Employee(
        organization_id=organization.id,
        employee_code="HR-001",
        first_name="Hari",
        last_name="Rao",
        email="hr.dev@workpulse.local",
        department_id=department.id,
        joining_date=date(2024, 1, 8),
        employment_status=EmploymentStatus.ACTIVE,
        is_active=True,
    )
    team_lead = Employee(
        organization_id=organization.id,
        employee_code="TL-001",
        first_name="Leah",
        last_name="Turner",
        email="lead.dev@workpulse.local",
        department_id=department.id,
        team_id=team.id,
        joining_date=date(2024, 2, 12),
        employment_status=EmploymentStatus.ACTIVE,
        is_active=True,
    )
    session.add_all([hr_employee, team_lead])
    session.flush()

    team.team_lead_id = team_lead.id

    employee = Employee(
        organization_id=organization.id,
        employee_code="EMP-001",
        first_name="Eden",
        last_name="Patel",
        email="employee.dev@workpulse.local",
        department_id=department.id,
        team_id=team.id,
        manager_id=team_lead.id,
        joining_date=date(2024, 3, 4),
        employment_status=EmploymentStatus.ACTIVE,
        is_active=True,
    )
    session.add(employee)
    session.flush()

    session.add_all(
        [
            EmployeeRole(employee_id=hr_employee.id, role_id=roles["HR"].id),
            EmployeeRole(employee_id=team_lead.id, role_id=roles["TEAM_LEAD"].id),
            EmployeeRole(employee_id=employee.id, role_id=roles["EMPLOYEE"].id),
        ]
    )
    session.flush()

    admin_employee = Employee(
        organization_id=organization.id,
        employee_code="ADM-001",
        first_name="Asha",
        last_name="Admin",
        email="admin.dev@workpulse.local",
        department_id=department.id,
        joining_date=date(2024, 1, 2),
        employment_status=EmploymentStatus.ACTIVE,
        is_active=True,
    )
    session.add(admin_employee)
    session.flush()
    session.add(EmployeeRole(employee_id=admin_employee.id, role_id=roles["ADMIN"].id))
    session.flush()
    logger.info("Seeded development organization %s", DEV_ORGANIZATION_CODE)
    _seed_development_accounts(session, organization)
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


def _ensure_admin_employee(session: Session, organization: Organization, roles: dict[str, Role]) -> None:
    existing = session.scalar(
        select(Employee).where(
            Employee.organization_id == organization.id,
            Employee.employee_code == "ADM-001",
        )
    )
    if existing is not None:
        return
    department = session.scalar(
        select(Department).where(Department.organization_id == organization.id).limit(1)
    )
    admin_employee = Employee(
        organization_id=organization.id,
        employee_code="ADM-001",
        first_name="Asha",
        last_name="Admin",
        email="admin.dev@workpulse.local",
        department_id=department.id if department else None,
        joining_date=date(2024, 1, 2),
        employment_status=EmploymentStatus.ACTIVE,
        is_active=True,
    )
    session.add(admin_employee)
    session.flush()
    session.add(EmployeeRole(employee_id=admin_employee.id, role_id=roles["ADMIN"].id))
    session.flush()
