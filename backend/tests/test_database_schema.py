"""PostgreSQL connectivity, migrations, and relationship checks."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import inspect, select, text

from app.database.session import SessionLocal, engine
from app.models.attendance import Attendance, AttendanceEvent
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import AttendanceEventType, AttendanceStatus, EmploymentStatus
from app.models.organization import Organization
from app.models.rbac import EmployeeRole, Permission, Role
from app.models.team import Team
from app.models.timesheet import Timesheet

EXPECTED_TABLES = {
    "organizations",
    "departments",
    "teams",
    "employees",
    "roles",
    "permissions",
    "role_permissions",
    "employee_roles",
    "devices",
    "attendance",
    "attendance_events",
    "timesheets",
    "timesheet_approvals",
    "locations",
    "notifications",
    "audit_logs",
    "user_accounts",
    "refresh_tokens",
    "revoked_access_tokens",
    "alembic_version",
}


def test_postgresql_connection_works(migrated_database: None) -> None:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_migrated_tables_exist(migrated_database: None) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {sorted(missing)}"


def test_relationships_can_be_loaded(migrated_database: None) -> None:
    session = SessionLocal()
    try:
        organization = Organization(
            name="Rel Test Org",
            code=f"REL-{uuid4().hex[:8].upper()}",
            timezone="UTC",
        )
        session.add(organization)
        session.flush()

        department = Department(
            organization_id=organization.id,
            name="Quality",
            code="QA",
        )
        session.add(department)
        session.flush()

        team = Team(
            organization_id=organization.id,
            department_id=department.id,
            name="QA Team",
        )
        session.add(team)
        session.flush()

        lead = Employee(
            organization_id=organization.id,
            employee_code="TL-REL",
            first_name="Taylor",
            last_name="Lead",
            email="lead.rel@workpulse.local",
            department_id=department.id,
            team_id=team.id,
            employment_status=EmploymentStatus.ACTIVE,
        )
        session.add(lead)
        session.flush()
        team.team_lead_id = lead.id

        member = Employee(
            organization_id=organization.id,
            employee_code="EMP-REL",
            first_name="Morgan",
            last_name="Member",
            email="member.rel@workpulse.local",
            department_id=department.id,
            team_id=team.id,
            manager_id=lead.id,
            joining_date=date(2024, 6, 1),
            employment_status=EmploymentStatus.ACTIVE,
        )
        session.add(member)
        session.flush()

        suffix = uuid4().hex[:8]
        role = Role(name=f"REL_TEST_ROLE_{suffix}", description="Test-only role")
        permission = Permission(name=f"rel.test.permission.{suffix}", description="Test-only permission")
        role.permissions.append(permission)
        session.add(role)
        session.flush()
        session.add(EmployeeRole(employee_id=lead.id, role_id=role.id))

        attendance = Attendance(
            employee_id=member.id,
            attendance_date=date(2024, 6, 2),
            status=AttendanceStatus.INCOMPLETE,
        )
        session.add(attendance)
        session.flush()
        session.add(
            AttendanceEvent(
                employee_id=member.id,
                attendance_id=attendance.id,
                event_type=AttendanceEventType.LOGIN,
                event_time=datetime(2024, 6, 2, 9, 0, tzinfo=timezone.utc),
            )
        )
        session.add(
            Timesheet(
                employee_id=member.id,
                date=date(2024, 6, 2),
                project="WorkPulse",
                task="Schema test",
                hours=Decimal("4.00"),
            )
        )
        session.commit()

        session.expire_all()
        loaded_org = session.scalar(
            select(Organization).where(Organization.id == organization.id)
        )
        assert loaded_org is not None
        assert loaded_org.departments[0].name == "Quality"
        loaded_team = loaded_org.teams[0]
        assert loaded_team.team_lead is not None
        assert loaded_team.team_lead.employee_code == "TL-REL"
        loaded_member = session.scalar(
            select(Employee).where(
                Employee.organization_id == organization.id,
                Employee.employee_code == "EMP-REL",
            )
        )
        assert loaded_member is not None
        assert loaded_member.manager is not None
        assert loaded_member.manager.employee_code == "TL-REL"
        assert loaded_member.team is not None
        assert loaded_member.team.name == "QA Team"
        assert loaded_member.attendance_records[0].events[0].event_type == AttendanceEventType.LOGIN
        assert loaded_member.timesheets[0].project == "WorkPulse"
        assert loaded_team.team_lead.employee_roles[0].role.permissions[0].name == f"rel.test.permission.{suffix}"
    finally:
        session.close()


def test_seed_development_data_creates_rbac_placeholders(migrated_database: None) -> None:
    from app.database.seed import DEV_ORGANIZATION_CODE, seed_development_data

    session = SessionLocal()
    try:
        organization = seed_development_data(session)
        session.commit()
        session.expire_all()

        loaded = session.scalar(
            select(Organization).where(Organization.code == DEV_ORGANIZATION_CODE)
        )
        assert loaded is not None
        assert loaded.id == organization.id
        assert loaded.name == "Finance Company - Development"
        department_names = {department.name for department in loaded.departments}
        assert "Finance Operations" in department_names
        finance_team = next(team for team in loaded.teams if team.name == "Finance Operations Team")
        lead = finance_team.team_lead
        assert lead is not None
        assert lead.employee_code == "EMP003"
        codes = {employee.employee_code for employee in loaded.employees}
        assert {"HR001", "EMP001", "EMP002", "EMP003"}.issubset(codes)
        member = next(employee for employee in loaded.employees if employee.employee_code == "EMP001")
        assert member.manager_id == lead.id
        role_names = {
            assignment.role.name
            for employee in loaded.employees
            for assignment in employee.employee_roles
        }
        assert {"HR", "TEAM_LEAD", "EMPLOYEE"}.issubset(role_names)
        hr_role = session.scalar(select(Role).where(Role.name == "HR"))
        assert hr_role is not None
        assert "employee.manage_organization" in {perm.name for perm in hr_role.permissions}

        seed_development_data(session)
        session.commit()
        assert session.scalar(select(Organization).where(Organization.code == DEV_ORGANIZATION_CODE)) is not None
    finally:
        session.close()
