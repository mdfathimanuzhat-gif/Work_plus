"""Attendance API authorization and persistence tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database.seed import seed_development_data
from app.database.session import SessionLocal
from app.main import app
from app.models.attendance import Attendance, AttendanceEvent
from app.models.employee import Employee
from app.models.enums import AttendanceEventType

PASSWORD = "TestPassw0rd!"


def _day(offset_days: int, hour: int = 0, minute: int = 0) -> datetime:
    base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=offset_days)
    return base.replace(hour=hour, minute=minute)


@pytest.fixture
def client(migrated_database: None) -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def people(migrated_database: None) -> dict[str, Any]:
    session = SessionLocal()
    try:
        organization = seed_development_data(session)
        session.commit()
        employees = {
            employee.email: employee
            for employee in session.scalars(
                select(Employee).where(Employee.organization_id == organization.id)
            )
        }
        return {
            "israh_id": employees["israh.zunain@workpulse.local"].id,
            "sameer_id": employees["sameer@workpulse.local"].id,
            "nayab_id": employees["nayab.rasul@workpulse.local"].id,
            "sidrah_id": employees["sidrah.hunain@workpulse.local"].id,
        }
    finally:
        session.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.json()
    return response.json()["access_token"]


def _add_events(employee_id, pairs: list[tuple[datetime, AttendanceEventType]]) -> None:
    session = SessionLocal()
    try:
        times = [moment for moment, _ in pairs]
        start = min(times).replace(hour=0, minute=0, second=0, microsecond=0)
        end = max(times)
        session.execute(
            delete(AttendanceEvent).where(
                AttendanceEvent.employee_id == employee_id,
                AttendanceEvent.event_time >= start,
                AttendanceEvent.event_time <= end,
            )
        )
        for moment, event_type in pairs:
            session.add(
                AttendanceEvent(
                    employee_id=employee_id,
                    client_event_id=uuid4(),
                    event_type=event_type,
                    event_time=moment,
                )
            )
        session.commit()
    finally:
        session.close()


def test_employee_can_only_read_own_attendance(client: TestClient, people: dict[str, Any]) -> None:
    day = _day(20, 0)
    _add_events(
        people["israh_id"],
        [
            (day.replace(hour=9), AttendanceEventType.LOGIN),
            (day.replace(hour=18), AttendanceEventType.LOGOUT),
        ],
    )
    _add_events(
        people["sameer_id"],
        [
            (day.replace(hour=10), AttendanceEventType.LOGIN),
            (day.replace(hour=17), AttendanceEventType.LOGOUT),
        ],
    )
    israh = _token(client, "israh.zunain@workpulse.local")
    own = client.get(f"/api/attendance/me/{day.date().isoformat()}", headers=_auth(israh))
    assert own.status_code == 200, own.json()
    assert own.json()["total_session_seconds"] == 9 * 3600
    assert own.json()["total_active_seconds"] == 9 * 3600
    assert own.json()["status"] == "PRESENT"
    other = client.get(f"/api/attendance/{people['sameer_id']}/{day.date().isoformat()}", headers=_auth(israh))
    assert other.status_code == 403
    live = client.get("/api/attendance/me/live", headers=_auth(israh))
    assert live.status_code == 200
    assert live.json()["state"] == "OFFLINE"


def test_team_lead_sees_team_not_hr(client: TestClient, people: dict[str, Any]) -> None:
    day = _day(21, 0)
    _add_events(
        people["israh_id"],
        [
            (day.replace(hour=9), AttendanceEventType.LOGIN),
            (day.replace(hour=18), AttendanceEventType.LOGOUT),
        ],
    )
    nayab = _token(client, "nayab.rasul@workpulse.local")
    allowed = client.get(f"/api/attendance/{people['israh_id']}/{day.date().isoformat()}", headers=_auth(nayab))
    assert allowed.status_code == 200
    denied = client.get(f"/api/attendance/{people['sidrah_id']}/{day.date().isoformat()}", headers=_auth(nayab))
    assert denied.status_code == 403
    team = client.get(f"/api/attendance/team/{day.date().isoformat()}", headers=_auth(nayab))
    assert team.status_code == 200
    ids = {row["employee_id"] for row in team.json()["records"]}
    assert str(people["israh_id"]) in ids
    assert str(people["sidrah_id"]) not in ids


def test_hr_can_view_organization_attendance(client: TestClient, people: dict[str, Any]) -> None:
    day = _day(22, 0)
    _add_events(
        people["sameer_id"],
        [
            (day.replace(hour=9), AttendanceEventType.LOGIN),
            (day.replace(hour=13), AttendanceEventType.LOCK),
            (day.replace(hour=13, minute=30), AttendanceEventType.UNLOCK),
            (day.replace(hour=18), AttendanceEventType.LOGOUT),
        ],
    )
    hr = _token(client, "sidrah.hunain@workpulse.local")
    response = client.get(f"/api/attendance/{people['sameer_id']}/{day.date().isoformat()}", headers=_auth(hr))
    assert response.status_code == 200
    body = response.json()
    assert body["total_locked_seconds"] == 30 * 60
    assert body["total_session_seconds"] == 9 * 3600
    employee_denied_team = _token(client, "israh.zunain@workpulse.local")
    assert client.get(f"/api/attendance/team/{day.date().isoformat()}", headers=_auth(employee_denied_team)).status_code == 403


def test_recalculation_does_not_accumulate(client: TestClient, people: dict[str, Any]) -> None:
    day = _day(23, 0)
    _add_events(
        people["israh_id"],
        [
            (day.replace(hour=9), AttendanceEventType.LOGIN),
            (day.replace(hour=18), AttendanceEventType.LOGOUT),
        ],
    )
    token = _token(client, "israh.zunain@workpulse.local")
    first = client.get(f"/api/attendance/me/{day.date().isoformat()}", headers=_auth(token))
    second = client.get(f"/api/attendance/me/{day.date().isoformat()}", headers=_auth(token))
    assert first.json()["total_active_seconds"] == second.json()["total_active_seconds"] == 9 * 3600
    session = SessionLocal()
    try:
        rows = list(
            session.scalars(
                select(Attendance).where(
                    Attendance.employee_id == people["israh_id"],
                    Attendance.attendance_date == day.date(),
                )
            )
        )
        assert len(rows) == 1
        assert len(rows[0].sessions) == 1
    finally:
        session.close()


def test_attendance_endpoints_are_read_only(client: TestClient, people: dict[str, Any]) -> None:
    token = _token(client, "israh.zunain@workpulse.local")
    assert client.post("/api/attendance/me", headers=_auth(token), json={}).status_code in {404, 405, 422}
    assert client.patch("/api/attendance/me/2031-06-01", headers=_auth(token), json={"status": "PRESENT"}).status_code in {
        404,
        405,
        422,
    }


def test_live_status_is_offline_when_last_event_is_stale(client: TestClient, people: dict[str, Any]) -> None:
    last_seen = datetime.now(timezone.utc) - timedelta(minutes=11)
    _add_events(
        people["israh_id"],
        [(last_seen, AttendanceEventType.LOGIN)],
    )
    token = _token(client, "israh.zunain@workpulse.local")
    live = client.get("/api/attendance/me/live", headers=_auth(token))
    assert live.status_code == 200, live.json()
    body = live.json()
    assert body["state"] == "OFFLINE"
    as_of = datetime.fromisoformat(body["as_of"].replace("Z", "+00:00"))
    assert abs((as_of - last_seen).total_seconds()) < 2


def test_live_status_keeps_recent_state(client: TestClient, people: dict[str, Any]) -> None:
    recent_login = datetime.now(timezone.utc) - timedelta(seconds=30)
    _add_events(
        people["sameer_id"],
        [(recent_login, AttendanceEventType.LOGIN)],
    )
    token = _token(client, "sameer@workpulse.local")
    live = client.get("/api/attendance/me/live", headers=_auth(token))
    assert live.status_code == 200, live.json()
    assert live.json()["state"] == "ACTIVE"

    recent_lock = datetime.now(timezone.utc) - timedelta(minutes=2)
    _add_events(
        people["sameer_id"],
        [
            (recent_lock - timedelta(minutes=1), AttendanceEventType.LOGIN),
            (recent_lock, AttendanceEventType.LOCK),
        ],
    )
    locked = client.get("/api/attendance/me/live", headers=_auth(token))
    assert locked.status_code == 200, locked.json()
    assert locked.json()["state"] == "LOCKED"

