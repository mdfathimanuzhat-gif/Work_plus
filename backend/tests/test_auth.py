"""Authentication, JWT, and data-isolation tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.seed import (
    PERMISSION_DEFINITIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSION_MAP,
)
from app.database.session import SessionLocal
from app.main import app
from app.models.department import Department
from app.models.employee import Employee
from app.models.enums import EmploymentStatus
from app.models.organization import Organization
from app.models.rbac import EmployeeRole, Permission, Role
from app.models.team import Team
from app.services.auth_service import create_account

PASSWORD = "TestPassw0rd!"


@pytest.fixture
def client(migrated_database: None) -> TestClient:
    return TestClient(app)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _ensure_role(session: Session, name: str) -> Role:
    role = session.scalar(select(Role).where(Role.name == name))
    if role is None:
        description = dict(ROLE_DEFINITIONS).get(name, name)
        role = Role(name=name, description=description)
        session.add(role)
        session.flush()
    permissions_by_name = {
        permission.name: permission for permission in session.scalars(select(Permission)).all()
    }
    for permission_name, description in PERMISSION_DEFINITIONS:
        if permission_name not in permissions_by_name:
            permission = Permission(name=permission_name, description=description)
            session.add(permission)
            session.flush()
            permissions_by_name[permission_name] = permission
    wanted = set(ROLE_PERMISSION_MAP.get(name, ()))
    current = {permission.name for permission in role.permissions}
    for permission_name in wanted - current:
        role.permissions.append(permissions_by_name[permission_name])
    session.flush()
    return role


def _employee(
    session: Session,
    organization: Organization,
    *,
    code: str,
    email: str,
    first_name: str,
    last_name: str,
    role_name: str,
    department: Department | None = None,
    team: Team | None = None,
    manager: Employee | None = None,
    is_active: bool = True,
    account_active: bool = True,
    password: str = PASSWORD,
) -> Employee:
    employee = Employee(
        organization_id=organization.id,
        employee_code=code,
        first_name=first_name,
        last_name=last_name,
        email=email,
        department_id=department.id if department else None,
        team_id=team.id if team else None,
        manager_id=manager.id if manager else None,
        joining_date=date(2024, 6, 1),
        employment_status=EmploymentStatus.ACTIVE,
        is_active=is_active,
    )
    session.add(employee)
    session.flush()
    role = _ensure_role(session, role_name)
    session.add(EmployeeRole(employee_id=employee.id, role_id=role.id))
    create_account(
        session,
        employee_id=employee.id,
        email=email,
        password=password,
        is_active=account_active,
    )
    session.flush()
    return employee


@pytest.fixture(scope="session")
def isolation_world(migrated_database: None) -> dict[str, Any]:
    session = SessionLocal()
    try:
        existing = session.scalar(select(Organization).where(Organization.code == "AUTH-ISO"))
        if existing is not None:
            employees = {
                employee.email: employee
                for employee in session.scalars(
                    select(Employee).where(Employee.organization_id == existing.id)
                )
            }
            return {
                "hr_id": employees["hr.iso@workpulse.local"].id,
                "admin_id": employees["admin.iso@workpulse.local"].id,
                "lead_a_id": employees["lead.a@workpulse.local"].id,
                "lead_b_id": employees["lead.b@workpulse.local"].id,
                "member_a_id": employees["emp.a@workpulse.local"].id,
                "member_b_id": employees["emp.b@workpulse.local"].id,
                "inactive_id": employees["inactive@workpulse.local"].id,
                "org_id": existing.id,
            }

        organization = Organization(name="Auth Test Org", code="AUTH-ISO", timezone="UTC")
        session.add(organization)
        session.flush()
        department = Department(organization_id=organization.id, name="Engineering", code="ENG")
        session.add(department)
        session.flush()
        team_a = Team(organization_id=organization.id, department_id=department.id, name="Team A")
        team_b = Team(organization_id=organization.id, department_id=department.id, name="Team B")
        session.add_all([team_a, team_b])
        session.flush()

        hr = _employee(
            session,
            organization,
            code="HR-A",
            email="hr.iso@workpulse.local",
            first_name="Hari",
            last_name="Iso",
            role_name="HR",
            department=department,
        )
        admin = _employee(
            session,
            organization,
            code="ADM-A",
            email="admin.iso@workpulse.local",
            first_name="Asha",
            last_name="Iso",
            role_name="ADMIN",
            department=department,
        )
        lead_a = _employee(
            session,
            organization,
            code="TL-A",
            email="lead.a@workpulse.local",
            first_name="Leah",
            last_name="Alpha",
            role_name="TEAM_LEAD",
            department=department,
            team=team_a,
        )
        lead_b = _employee(
            session,
            organization,
            code="TL-B",
            email="lead.b@workpulse.local",
            first_name="Lee",
            last_name="Beta",
            role_name="TEAM_LEAD",
            department=department,
            team=team_b,
        )
        team_a.team_lead_id = lead_a.id
        team_b.team_lead_id = lead_b.id
        member_a = _employee(
            session,
            organization,
            code="EMP-A",
            email="emp.a@workpulse.local",
            first_name="Eden",
            last_name="Alpha",
            role_name="EMPLOYEE",
            department=department,
            team=team_a,
            manager=lead_a,
        )
        member_b = _employee(
            session,
            organization,
            code="EMP-B",
            email="emp.b@workpulse.local",
            first_name="Evan",
            last_name="Beta",
            role_name="EMPLOYEE",
            department=department,
            team=team_b,
            manager=lead_b,
        )
        inactive = _employee(
            session,
            organization,
            code="EMP-INACTIVE",
            email="inactive@workpulse.local",
            first_name="Ina",
            last_name="Active",
            role_name="EMPLOYEE",
            department=department,
            team=team_a,
            account_active=False,
        )
        world = {
            "hr_id": hr.id,
            "admin_id": admin.id,
            "lead_a_id": lead_a.id,
            "lead_b_id": lead_b.id,
            "member_a_id": member_a.id,
            "member_b_id": member_b.id,
            "inactive_id": inactive.id,
            "org_id": organization.id,
        }
        session.commit()
        return world
    finally:
        session.close()


def test_login_success(client: TestClient, isolation_world: dict[str, Any]) -> None:
    response = _login(client, "emp.a@workpulse.local")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert "password_hash" not in body
    payload = jwt.decode(
        body["access_token"],
        get_settings().SECRET_KEY,
        algorithms=[get_settings().JWT_ALGORITHM],
    )
    assert payload["typ"] == "access"
    assert payload["employee_id"] == str(isolation_world["member_a_id"])
    assert payload["role"] == "EMPLOYEE"
    assert "email" not in payload
    assert "password" not in payload


def test_login_invalid_password(client: TestClient, isolation_world: dict[str, Any]) -> None:
    response = _login(client, "emp.a@workpulse.local", "WrongPassw0rd!")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    unknown = _login(client, "missing@workpulse.local", "WrongPassw0rd!")
    assert unknown.status_code == 401
    assert unknown.json()["error"]["message"] == response.json()["error"]["message"]


def test_login_inactive_account(client: TestClient, isolation_world: dict[str, Any]) -> None:
    response = _login(client, "inactive@workpulse.local")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_me_missing_token(client: TestClient, isolation_world: dict[str, Any]) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_invalid_token(client: TestClient, isolation_world: dict[str, Any]) -> None:
    response = client.get("/api/auth/me", headers=_auth_header("not-a-valid-token"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_me_expired_token(client: TestClient, isolation_world: dict[str, Any]) -> None:
    member_id = isolation_world["member_a_id"]
    org_id = isolation_world["org_id"]
    session = SessionLocal()
    try:
        from app.models.user_account import UserAccount

        account = session.scalar(select(UserAccount).where(UserAccount.employee_id == member_id))
        assert account is not None
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(account.id),
                "employee_id": str(member_id),
                "organization_id": str(org_id),
                "role": "EMPLOYEE",
                "roles": ["EMPLOYEE"],
                "typ": "access",
                "jti": "expired-jti",
                "iat": int((now - timedelta(hours=2)).timestamp()),
                "exp": int((now - timedelta(hours=1)).timestamp()),
            },
            get_settings().SECRET_KEY,
            algorithm=get_settings().JWT_ALGORITHM,
        )
    finally:
        session.close()
    response = client.get("/api/auth/me", headers=_auth_header(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


def test_refresh_token_rotation(client: TestClient, isolation_world: dict[str, Any]) -> None:
    login = _login(client, "emp.a@workpulse.local")
    refresh = client.post("/api/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert refresh.status_code == 200
    new_tokens = refresh.json()
    assert new_tokens["access_token"] != login.json()["access_token"]
    reused = client.post("/api/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert reused.status_code == 401
    me = client.get("/api/auth/me", headers=_auth_header(new_tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "emp.a@workpulse.local"


def test_logout_revokes_tokens(client: TestClient, isolation_world: dict[str, Any]) -> None:
    login = _login(client, "emp.a@workpulse.local")
    access = login.json()["access_token"]
    refresh = login.json()["refresh_token"]
    response = client.post(
        "/api/auth/logout",
        headers=_auth_header(access),
        json={"refresh_token": refresh},
    )
    assert response.status_code == 200
    me = client.get("/api/auth/me", headers=_auth_header(access))
    assert me.status_code == 401
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 401


def test_get_me(client: TestClient, isolation_world: dict[str, Any]) -> None:
    access = _login(client, "emp.a@workpulse.local").json()["access_token"]
    response = client.get("/api/auth/me", headers=_auth_header(access))
    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == str(isolation_world["member_a_id"])
    assert body["roles"] == ["EMPLOYEE"]
    assert "password_hash" not in body
    assert "employee.view_own" in body["permissions"]


def test_employee_can_access_own_data(client: TestClient, isolation_world: dict[str, Any]) -> None:
    member_id = isolation_world["member_a_id"]
    access = _login(client, "emp.a@workpulse.local").json()["access_token"]
    response = client.get(f"/api/employees/{member_id}", headers=_auth_header(access))
    assert response.status_code == 200
    assert response.json()["id"] == str(member_id)
    listing = client.get("/api/employees", headers=_auth_header(access))
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [str(member_id)]


def test_employee_cannot_access_another_employee(client: TestClient, isolation_world: dict[str, Any]) -> None:
    other_id = isolation_world["member_b_id"]
    teammate_lead_id = isolation_world["lead_a_id"]
    access = _login(client, "emp.a@workpulse.local").json()["access_token"]
    other_team = client.get(f"/api/employees/{other_id}", headers=_auth_header(access))
    assert other_team.status_code == 403
    same_team_lead = client.get(f"/api/employees/{teammate_lead_id}", headers=_auth_header(access))
    assert same_team_lead.status_code == 403


def test_team_lead_can_access_own_team(client: TestClient, isolation_world: dict[str, Any]) -> None:
    member_id = isolation_world["member_a_id"]
    lead_id = isolation_world["lead_a_id"]
    access = _login(client, "lead.a@workpulse.local").json()["access_token"]
    own = client.get(f"/api/employees/{lead_id}", headers=_auth_header(access))
    member_response = client.get(f"/api/employees/{member_id}", headers=_auth_header(access))
    assert own.status_code == 200
    assert member_response.status_code == 200
    listing = client.get("/api/employees", headers=_auth_header(access))
    codes = {row["employee_code"] for row in listing.json()}
    assert {"TL-A", "EMP-A", "EMP-INACTIVE"}.issubset(codes)
    assert "EMP-B" not in codes


def test_team_lead_cannot_access_another_team(client: TestClient, isolation_world: dict[str, Any]) -> None:
    other_member_id = isolation_world["member_b_id"]
    other_lead_id = isolation_world["lead_b_id"]
    access = _login(client, "lead.a@workpulse.local").json()["access_token"]
    assert client.get(f"/api/employees/{other_member_id}", headers=_auth_header(access)).status_code == 403
    assert client.get(f"/api/employees/{other_lead_id}", headers=_auth_header(access)).status_code == 403


def test_hr_can_access_organization_employees(client: TestClient, isolation_world: dict[str, Any]) -> None:
    access = _login(client, "hr.iso@workpulse.local").json()["access_token"]
    other_id = isolation_world["member_b_id"]
    response = client.get(f"/api/employees/{other_id}", headers=_auth_header(access))
    assert response.status_code == 200
    listing = client.get("/api/employees", headers=_auth_header(access))
    codes = {row["employee_code"] for row in listing.json()}
    assert {"HR-A", "ADM-A", "TL-A", "TL-B", "EMP-A", "EMP-B", "EMP-INACTIVE"}.issubset(codes)


def test_admin_can_access_organization_employees(client: TestClient, isolation_world: dict[str, Any]) -> None:
    access = _login(client, "admin.iso@workpulse.local").json()["access_token"]
    other_id = isolation_world["member_a_id"]
    response = client.get(f"/api/employees/{other_id}", headers=_auth_header(access))
    assert response.status_code == 200
    listing = client.get("/api/employees", headers=_auth_header(access))
    assert len(listing.json()) >= 7
