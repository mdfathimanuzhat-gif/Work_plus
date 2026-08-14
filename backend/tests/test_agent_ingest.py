"""Desktop-agent enrollment and event ingestion tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.attendance import AttendanceEvent
from app.models.device import Device
from app.models.employee import Employee
from app.models.enums import AttendanceEventType, EmploymentStatus
from app.models.organization import Organization
from app.models.rbac import EmployeeRole, Role
from app.services.auth_service import create_account

PASSWORD = "TestPassw0rd!"


@pytest.fixture
def client(migrated_database: None) -> TestClient:
    return TestClient(app)


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.json()
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def agent_world(migrated_database: None) -> dict[str, str]:
    session = SessionLocal()
    try:
        org = session.scalar(select(Organization).where(Organization.code == "AGT-SYNC"))
        if org is None:
            org = Organization(name="Agent Sync Org", code="AGT-SYNC", timezone="UTC")
            session.add(org)
            session.flush()
            role = session.scalar(select(Role).where(Role.name == "EMPLOYEE"))
            if role is None:
                role = Role(name="EMPLOYEE", description="Individual contributor")
                session.add(role)
                session.flush()
            assert role is not None
            emp = Employee(
                organization_id=org.id,
                employee_code="AGT001",
                first_name="Agent",
                last_name="User",
                email="agent.user@workpulse.local",
                employment_status=EmploymentStatus.ACTIVE,
                is_active=True,
            )
            other = Employee(
                organization_id=org.id,
                employee_code="AGT002",
                first_name="Other",
                last_name="User",
                email="agent.other@workpulse.local",
                employment_status=EmploymentStatus.ACTIVE,
                is_active=True,
            )
            session.add_all([emp, other])
            session.flush()
            session.add_all(
                [
                    EmployeeRole(employee_id=emp.id, role_id=role.id),
                    EmployeeRole(employee_id=other.id, role_id=role.id),
                ]
            )
            create_account(session, employee_id=emp.id, email=emp.email, password=PASSWORD)
            create_account(session, employee_id=other.id, email=other.email, password=PASSWORD)
            session.commit()
        return {"email": "agent.user@workpulse.local", "other_email": "agent.other@workpulse.local"}
    finally:
        session.close()


def _enroll(client: TestClient, token: str, identifier: str) -> dict:
    response = client.post(
        "/api/agent/devices/enroll",
        headers={"Authorization": f"Bearer {token}"},
        json={"device_identifier": identifier, "device_name": "DESKTOP-TEST", "operating_system": "Windows"},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _device_token(client: TestClient, identifier: str, secret: str) -> str:
    response = client.post(
        "/api/agent/auth/token",
        json={"device_identifier": identifier, "device_secret": secret},
    )
    assert response.status_code == 200, response.json()
    return response.json()["access_token"]


def _event(event_id, event_type: str, identifier: str, timestamp: datetime | None = None) -> dict:
    return {
        "event_id": str(event_id),
        "event_type": event_type,
        "event_timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        "device_identifier": identifier,
        "device_name": "DESKTOP-TEST",
        "username": "test-user",
        "metadata": {"source": "test"},
    }


def test_successful_and_batch_upload(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    identifier = f"dev-{uuid4()}"
    enrolled = _enroll(client, user_token, identifier)
    device_token = _device_token(client, identifier, enrolled["device_secret"])
    first = uuid4()
    second = uuid4()
    past = datetime.now(timezone.utc) - timedelta(hours=4)
    response = client.post(
        "/api/agent/events/batch",
        headers={"Authorization": f"Bearer {device_token}"},
        json={
            "device_id": identifier,
            "events": [
                _event(first, "WINDOWS_LOGIN", identifier, past),
                _event(second, "SYSTEM_LOCK", identifier),
            ],
        },
    )
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["accepted"] == 2
    assert body["duplicates"] == 0
    session = SessionLocal()
    try:
        stored = session.scalar(select(AttendanceEvent).where(AttendanceEvent.client_event_id == first))
        assert stored is not None
        assert stored.event_type is AttendanceEventType.LOGIN
        stored_time = stored.event_time
        if stored_time.tzinfo is None:
            stored_time = stored_time.replace(tzinfo=timezone.utc)
        assert abs((stored_time - past).total_seconds()) < 1
    finally:
        session.close()


def test_duplicate_event_is_idempotent(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    identifier = f"dev-{uuid4()}"
    enrolled = _enroll(client, user_token, identifier)
    device_token = _device_token(client, identifier, enrolled["device_secret"])
    event_id = uuid4()
    payload = {"device_id": identifier, "events": [_event(event_id, "SYSTEM_UNLOCK", identifier)]}
    headers = {"Authorization": f"Bearer {device_token}"}
    first = client.post("/api/agent/events/batch", headers=headers, json=payload)
    second = client.post("/api/agent/events/batch", headers=headers, json=payload)
    assert first.json()["accepted"] == 1
    assert second.json()["duplicates"] == 1
    assert second.json()["results"][0]["reason"] == "already_processed"
    session = SessionLocal()
    try:
        count = len(list(session.scalars(select(AttendanceEvent).where(AttendanceEvent.client_event_id == event_id))))
        assert count == 1
    finally:
        session.close()


def test_invalid_event_id_and_type(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    identifier = f"dev-{uuid4()}"
    enrolled = _enroll(client, user_token, identifier)
    device_token = _device_token(client, identifier, enrolled["device_secret"])
    headers = {"Authorization": f"Bearer {device_token}"}
    bad_id = client.post(
        "/api/agent/events/batch",
        headers=headers,
        json={"device_id": identifier, "events": [{**_event(uuid4(), "SYSTEM_LOCK", identifier), "event_id": "not-a-uuid"}]},
    )
    assert bad_id.status_code == 422
    bad_type = client.post(
        "/api/agent/events/batch",
        headers=headers,
        json={"device_id": identifier, "events": [_event(uuid4(), "SCREENSHOT", identifier)]},
    )
    assert bad_type.status_code == 422


def test_authentication_failure_and_unknown_device(client: TestClient) -> None:
    missing = client.post("/api/agent/events/batch", json={"device_id": "x", "events": [_event(uuid4(), "SYSTEM_LOCK", "x")]})
    assert missing.status_code == 401
    wrong = client.post(
        "/api/agent/auth/token",
        json={"device_identifier": "missing-device", "device_secret": "nope"},
    )
    assert wrong.status_code == 401


def test_inactive_device_rejected(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    identifier = f"dev-{uuid4()}"
    enrolled = _enroll(client, user_token, identifier)
    session = SessionLocal()
    try:
        device = session.scalar(select(Device).where(Device.device_identifier == identifier))
        assert device is not None
        device.is_active = False
        session.commit()
    finally:
        session.close()
    token_response = client.post(
        "/api/agent/auth/token",
        json={"device_identifier": identifier, "device_secret": enrolled["device_secret"]},
    )
    assert token_response.status_code == 403


def test_device_cannot_submit_another_employees_events(client: TestClient, agent_world: dict[str, str]) -> None:
    token_a = _login(client, agent_world["email"])
    token_b = _login(client, agent_world["other_email"])
    id_a = f"dev-{uuid4()}"
    id_b = f"dev-{uuid4()}"
    enroll_a = _enroll(client, token_a, id_a)
    enroll_b = _enroll(client, token_b, id_b)
    device_a = _device_token(client, id_a, enroll_a["device_secret"])
    hijack = client.post(
        "/api/agent/events/batch",
        headers={"Authorization": f"Bearer {device_a}"},
        json={"device_id": id_b, "events": [_event(uuid4(), "WINDOWS_LOGIN", id_b)]},
    )
    assert hijack.status_code == 403
    mismatch = client.post(
        "/api/agent/events/batch",
        headers={"Authorization": f"Bearer {device_a}"},
        json={"device_id": id_a, "events": [_event(uuid4(), "WINDOWS_LOGIN", id_b)]},
    )
    assert mismatch.status_code == 200
    assert mismatch.json()["failed"] == 1
    assert mismatch.json()["results"][0]["reason"] == "device_mismatch"


def test_employee_token_cannot_ingest_events(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    response = client.post(
        "/api/agent/events/batch",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"device_id": "x", "events": [_event(uuid4(), "SYSTEM_LOCK", "x")]},
    )
    assert response.status_code == 401


def test_rejects_client_supplied_employee_id(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    identifier = f"dev-{uuid4()}"
    enrolled = _enroll(client, user_token, identifier)
    device_token = _device_token(client, identifier, enrolled["device_secret"])
    event = _event(uuid4(), "SYSTEM_LOCK", identifier)
    event["employee_id"] = str(uuid4())
    response = client.post(
        "/api/agent/events/batch",
        headers={"Authorization": f"Bearer {device_token}"},
        json={"device_id": identifier, "events": [event]},
    )
    assert response.status_code == 422


def test_inactive_device_cannot_ingest_with_existing_token(client: TestClient, agent_world: dict[str, str]) -> None:
    user_token = _login(client, agent_world["email"])
    identifier = f"dev-{uuid4()}"
    enrolled = _enroll(client, user_token, identifier)
    device_token = _device_token(client, identifier, enrolled["device_secret"])
    session = SessionLocal()
    try:
        device = session.scalar(select(Device).where(Device.device_identifier == identifier))
        assert device is not None
        device.is_active = False
        session.commit()
    finally:
        session.close()
    response = client.post(
        "/api/agent/events/batch",
        headers={"Authorization": f"Bearer {device_token}"},
        json={"device_id": identifier, "events": [_event(uuid4(), "SYSTEM_LOCK", identifier)]},
    )
    assert response.status_code in {401, 403}
