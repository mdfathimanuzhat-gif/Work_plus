"""Employee, department, and team management tests using demo seed users."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.seed import seed_development_data
from app.database.session import SessionLocal
from app.main import app
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.models.organization import Organization
from app.models.rbac import EmployeeRole, Role
from app.models.team import Team
from app.repositories.user_account import get_account_by_email
from app.services.auth_service import create_account

PASSWORD = "TestPassw0rd!"


@pytest.fixture
def client(migrated_database: None) -> TestClient:
    return TestClient(app)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _token(client: TestClient, email: str) -> str:
    response = _login(client, email)
    assert response.status_code == 200, response.json()
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def demo(migrated_database: None) -> dict[str, Any]:
    session = SessionLocal()
    try:
        organization = seed_development_data(session)
        other_org = Organization(name="Other Org", code=f"OTH-{uuid4().hex[:6].upper()}", timezone="UTC")
        session.add(other_org)
        session.flush()
        other_dept = Department(
            organization_id=other_org.id,
            name="Other Dept",
            code="OTH",
            is_active=True,
        )
        session.add(other_dept)
        session.flush()
        outsider = Employee(
            organization_id=other_org.id,
            employee_code="OUT-1",
            first_name="Outside",
            last_name="Person",
            email=f"out.{uuid4().hex[:8]}@other.local",
            department_id=other_dept.id,
            employment_status=EmploymentStatus.ACTIVE,
            is_active=True,
        )
        session.add(outsider)
        session.flush()

        extra_dept = Department(
            organization_id=organization.id,
            name="Treasury",
            code=f"TRY-{uuid4().hex[:4].upper()}",
            is_active=True,
        )
        session.add(extra_dept)
        session.flush()
        extra_team = Team(
            organization_id=organization.id,
            department_id=extra_dept.id,
            name=f"Treasury Team {uuid4().hex[:4]}",
            is_active=True,
        )
        session.add(extra_team)
        session.flush()
        role_employee = session.scalar(select(Role).where(Role.name == "EMPLOYEE"))
        role_admin = session.scalar(select(Role).where(Role.name == "ADMIN"))
        assert role_employee is not None
        assert role_admin is not None
        outsider_team_member = session.scalar(
            select(Employee).where(
                Employee.organization_id == organization.id,
                Employee.employee_code == "EMP999",
            )
        )
        admin = session.scalar(
            select(Employee).where(
                Employee.organization_id == organization.id,
                Employee.employee_code == "ADM001",
            )
        )
        if outsider_team_member is None:
            outsider_team_member = Employee(
                organization_id=organization.id,
                employee_code="EMP999",
                first_name="Other",
                last_name="TeamMember",
                email="other.team@workpulse.local",
                department_id=extra_dept.id,
                team_id=extra_team.id,
                employment_status=EmploymentStatus.ACTIVE,
                is_active=True,
            )
            session.add(outsider_team_member)
        if admin is None:
            admin = Employee(
                organization_id=organization.id,
                employee_code="ADM001",
                first_name="Asha",
                last_name="Admin",
                email="asha.admin@workpulse.local",
                department_id=extra_dept.id,
                employment_status=EmploymentStatus.ACTIVE,
                is_active=True,
            )
            session.add(admin)
        session.flush()
        existing_role_pairs = {
            (row.employee_id, row.role_id)
            for row in session.scalars(
                select(EmployeeRole).where(
                    EmployeeRole.employee_id.in_([outsider_team_member.id, admin.id])
                )
            )
        }
        role_rows = []
        if (outsider_team_member.id, role_employee.id) not in existing_role_pairs:
            role_rows.append(EmployeeRole(employee_id=outsider_team_member.id, role_id=role_employee.id))
        if (admin.id, role_admin.id) not in existing_role_pairs:
            role_rows.append(EmployeeRole(employee_id=admin.id, role_id=role_admin.id))
        if role_rows:
            session.add_all(role_rows)
        if get_account_by_email(session, outsider_team_member.email) is None:
            create_account(
                session,
                employee_id=outsider_team_member.id,
                email=outsider_team_member.email,
                password=PASSWORD,
            )
        if get_account_by_email(session, admin.email) is None:
            create_account(session, employee_id=admin.id, email=admin.email, password=PASSWORD)
        extra_team.team_lead_id = outsider_team_member.id

        demo_employees = {
            employee.employee_code: employee
            for employee in session.scalars(
                select(Employee).where(Employee.organization_id == organization.id)
            )
        }
        world = {
            "org_id": organization.id,
            "israh_id": demo_employees["EMP001"].id,
            "sameer_id": demo_employees["EMP002"].id,
            "nayab_id": demo_employees["EMP003"].id,
            "sidrah_id": demo_employees["HR001"].id,
            "other_member_id": outsider_team_member.id,
            "admin_id": admin.id,
            "outsider_id": outsider.id,
            "outsider_dept_id": other_dept.id,
            "extra_dept_id": extra_dept.id,
            "extra_team_id": extra_team.id,
            "finops_dept_id": demo_employees["EMP001"].department_id,
            "finops_team_id": demo_employees["EMP001"].team_id,
        }
        session.commit()
        return world
    finally:
        session.close()


def test_israh_can_access_only_own_profile(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "israh.zunain@workpulse.local")
    own = client.get(f"/api/employees/{demo['israh_id']}", headers=_auth(token))
    me = client.get("/api/employees/me", headers=_auth(token))
    listing = client.get("/api/employees", headers=_auth(token))
    assert own.status_code == 200
    assert own.json()["employee_code"] == "EMP001"
    assert me.status_code == 200
    assert me.json()["id"] == str(demo["israh_id"])
    assert [row["id"] for row in listing.json()] == [str(demo["israh_id"])]


def test_sameer_can_access_only_own_profile(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sameer@workpulse.local")
    own = client.get(f"/api/employees/{demo['sameer_id']}", headers=_auth(token))
    assert own.status_code == 200
    assert own.json()["first_name"] == "Sameer"


def test_israh_cannot_access_sameer(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "israh.zunain@workpulse.local")
    response = client.get(f"/api/employees/{demo['sameer_id']}", headers=_auth(token))
    assert response.status_code == 403


def test_sameer_cannot_access_israh(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sameer@workpulse.local")
    response = client.get(f"/api/employees/{demo['israh_id']}", headers=_auth(token))
    assert response.status_code == 403


def test_nayab_can_access_assigned_team(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "nayab.rasul@workpulse.local")
    israh = client.get(f"/api/employees/{demo['israh_id']}", headers=_auth(token))
    sameer = client.get(f"/api/employees/{demo['sameer_id']}", headers=_auth(token))
    members = client.get(f"/api/teams/{demo['finops_team_id']}/members", headers=_auth(token))
    assert israh.status_code == 200
    assert sameer.status_code == 200
    codes = {row["employee_code"] for row in members.json()}
    assert {"EMP001", "EMP002", "EMP003"}.issubset(codes)


def test_nayab_cannot_access_employees_outside_team(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "nayab.rasul@workpulse.local")
    other_team = client.get(f"/api/employees/{demo['other_member_id']}", headers=_auth(token))
    hr = client.get(f"/api/employees/{demo['sidrah_id']}", headers=_auth(token))
    outsider = client.get(f"/api/employees/{demo['outsider_id']}", headers=_auth(token))
    assert other_team.status_code == 403
    assert hr.status_code == 403
    assert outsider.status_code == 404


def test_sidrah_can_access_all_organization_employees(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    listing = client.get("/api/employees", headers=_auth(token))
    codes = {row["employee_code"] for row in listing.json()}
    assert {"EMP001", "EMP002", "EMP003", "HR001", "EMP999", "ADM001"}.issubset(codes)
    outsider = client.get(f"/api/employees/{demo['outsider_id']}", headers=_auth(token))
    assert outsider.status_code == 404


def test_employees_cannot_create_employees(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "israh.zunain@workpulse.local")
    response = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP100",
            "first_name": "New",
            "last_name": "Person",
            "email": "new.person@workpulse.local",
        },
    )
    assert response.status_code == 403


def test_employees_cannot_change_own_role_department_or_team(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sameer@workpulse.local")
    employee_id = demo["sameer_id"]
    role = client.patch(
        f"/api/employees/{employee_id}",
        headers=_auth(token),
        json={"role": "HR"},
    )
    department = client.patch(
        f"/api/employees/{employee_id}",
        headers=_auth(token),
        json={"department_id": str(demo["extra_dept_id"])},
    )
    team = client.patch(
        f"/api/employees/{employee_id}",
        headers=_auth(token),
        json={"team_id": str(demo["extra_team_id"])},
    )
    status = client.patch(
        f"/api/employees/{employee_id}",
        headers=_auth(token),
        json={"employment_status": "TERMINATED"},
    )
    assert role.status_code == 403
    assert department.status_code == 403
    assert team.status_code == 403
    assert status.status_code == 403


def test_team_lead_cannot_create_or_deactivate_employees(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "nayab.rasul@workpulse.local")
    created = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP101",
            "first_name": "Blocked",
            "last_name": "Create",
            "email": "blocked.create@workpulse.local",
        },
    )
    deactivated = client.post(
        f"/api/employees/{demo['israh_id']}/deactivate",
        headers=_auth(token),
    )
    assert created.status_code == 403
    assert deactivated.status_code == 403


def test_hr_can_create_update_and_deactivate_employee(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    created = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP200",
            "first_name": "Amina",
            "last_name": "Khan",
            "email": "amina.khan@workpulse.local",
            "department_id": str(demo["finops_dept_id"]),
            "team_id": str(demo["finops_team_id"]),
            "manager_id": str(demo["nayab_id"]),
            "joining_date": str(date(2024, 7, 1)),
            "role": "EMPLOYEE",
            "password": PASSWORD,
        },
    )
    assert created.status_code == 201, created.json()
    employee_id = created.json()["id"]
    updated = client.patch(
        f"/api/employees/{employee_id}",
        headers=_auth(token),
        json={"phone": "555-0100", "employment_status": "ON_LEAVE"},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "555-0100"
    listing = client.get("/api/employees", headers=_auth(token), params={"search": "Amina"})
    assert any(row["id"] == employee_id for row in listing.json())
    deactivated = client.post(f"/api/employees/{employee_id}/deactivate", headers=_auth(token))
    assert deactivated.status_code == 200
    details = client.get(f"/api/employees/{employee_id}", headers=_auth(token))
    assert details.json()["is_active"] is False


def test_admin_can_manage_employees(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "asha.admin@workpulse.local")
    created = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP201",
            "first_name": "Admin",
            "last_name": "Hire",
            "email": "admin.hire@workpulse.local",
        },
    )
    assert created.status_code == 201


def test_duplicate_employee_code_and_email(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    duplicate_code = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP001",
            "first_name": "Dup",
            "last_name": "Code",
            "email": "dup.code@workpulse.local",
        },
    )
    duplicate_email = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP202",
            "first_name": "Dup",
            "last_name": "Email",
            "email": "israh.zunain@workpulse.local",
        },
    )
    assert duplicate_code.status_code == 409
    assert duplicate_email.status_code == 409


def test_invalid_department_team_and_team_lead(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    missing = str(uuid4())
    invalid_dept = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP203",
            "first_name": "Bad",
            "last_name": "Dept",
            "email": "bad.dept@workpulse.local",
            "department_id": missing,
        },
    )
    invalid_team = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP204",
            "first_name": "Bad",
            "last_name": "Team",
            "email": "bad.team@workpulse.local",
            "team_id": missing,
        },
    )
    invalid_lead = client.patch(
        f"/api/teams/{demo['finops_team_id']}",
        headers=_auth(token),
        json={"team_lead_id": missing},
    )
    cross_org_lead = client.patch(
        f"/api/teams/{demo['finops_team_id']}",
        headers=_auth(token),
        json={"team_lead_id": str(demo["outsider_id"])},
    )
    assert invalid_dept.status_code == 400
    assert invalid_team.status_code == 400
    assert invalid_lead.status_code == 400
    assert cross_org_lead.status_code == 400


def test_hr_department_and_team_management(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    department = client.post(
        "/api/departments",
        headers=_auth(token),
        json={"name": "Audit", "code": "AUD", "description": "Audit"},
    )
    assert department.status_code == 201
    team = client.post(
        "/api/teams",
        headers=_auth(token),
        json={
            "name": "Audit Team",
            "department_id": department.json()["id"],
            "team_lead_id": str(demo["nayab_id"]),
        },
    )
    assert team.status_code == 201
    updated = client.patch(
        f"/api/teams/{team.json()['id']}",
        headers=_auth(token),
        json={"team_lead_id": str(demo["nayab_id"])},
    )
    assert updated.status_code == 200
    employee = _token(client, "israh.zunain@workpulse.local")
    forbidden = client.post(
        "/api/departments",
        headers=_auth(employee),
        json={"name": "Nope", "code": "NOPE"},
    )
    assert forbidden.status_code == 403


def test_employee_can_view_assigned_team_not_other_team(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "israh.zunain@workpulse.local")
    own_team = client.get(f"/api/teams/{demo['finops_team_id']}", headers=_auth(token))
    other_team = client.get(f"/api/teams/{demo['extra_team_id']}", headers=_auth(token))
    assert own_team.status_code == 200
    assert other_team.status_code == 403


def test_cannot_assign_inactive_team_or_employee_as_team_lead(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    team = client.post(
        "/api/teams",
        headers=_auth(token),
        json={"name": "Inactive Assignment Team", "department_id": str(demo["finops_dept_id"])},
    )
    assert team.status_code == 201
    team_id = team.json()["id"]
    paused = client.patch(f"/api/teams/{team_id}", headers=_auth(token), json={"is_active": False})
    assert paused.status_code == 200
    assigned = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP205",
            "first_name": "Inactive",
            "last_name": "Team",
            "email": "inactive.team@workpulse.local",
            "team_id": team_id,
        },
    )
    assert assigned.status_code == 400
    employee_as_lead = client.patch(
        f"/api/teams/{demo['finops_team_id']}",
        headers=_auth(token),
        json={"team_lead_id": str(demo["israh_id"])},
    )
    assert employee_as_lead.status_code == 400
    employee_as_manager = client.patch(
        f"/api/employees/{demo['sameer_id']}",
        headers=_auth(token),
        json={"manager_id": str(demo["israh_id"])},
    )
    assert employee_as_manager.status_code == 400


def test_cannot_assign_other_organization_department(client: TestClient, demo: dict[str, Any]) -> None:
    token = _token(client, "sidrah.hunain@workpulse.local")
    response = client.post(
        "/api/employees",
        headers=_auth(token),
        json={
            "employee_code": "EMP206",
            "first_name": "Cross",
            "last_name": "Org",
            "email": "cross.org@workpulse.local",
            "department_id": str(demo["outsider_dept_id"]),
        },
    )
    assert response.status_code == 400
