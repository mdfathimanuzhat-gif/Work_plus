"""Timesheet create, submit, review, and visibility tests."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database.seed import seed_development_data
from app.database.session import SessionLocal
from app.main import app
from app.models.employee import Employee
from sqlalchemy import select

PASSWORD = "TestPassw0rd!"


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


def _entry_payload(**overrides: Any) -> dict[str, Any]:
    body = {
        "date": date.today().isoformat(),
        "project": f"Finance-{uuid4().hex[:8]}",
        "task": "Month close",
        "description": "Reconcile ledger",
        "hours": "7.50",
    }
    body.update(overrides)
    return body


def test_employee_creates_and_submits_entry_team_lead_approves(client: TestClient, people: dict[str, Any]) -> None:
    israh = _token(client, "israh.zunain@workpulse.local")
    nayab = _token(client, "nayab.rasul@workpulse.local")

    created = client.post("/api/timesheet/entries", headers=_auth(israh), json=_entry_payload())
    assert created.status_code == 201, created.json()
    entry_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"
    assert created.json()["employee_id"] == str(people["israh_id"])
    assert created.json()["submitted_at"] is None

    mine = client.get("/api/timesheet/entries", headers=_auth(israh))
    assert mine.status_code == 200
    assert any(row["id"] == entry_id for row in mine.json())

    submitted = client.post(f"/api/timesheet/entries/{entry_id}/submit", headers=_auth(israh))
    assert submitted.status_code == 200, submitted.json()
    assert submitted.json()["status"] == "SUBMITTED"
    assert submitted.json()["submitted_at"] is not None

    again = client.post(f"/api/timesheet/entries/{entry_id}/submit", headers=_auth(israh))
    assert again.status_code == 409

    queue = client.get("/api/timesheet/team", headers=_auth(nayab))
    assert queue.status_code == 200, queue.json()
    assert any(row["id"] == entry_id for row in queue.json())

    reviewed = client.post(
        f"/api/timesheet/entries/{entry_id}/review",
        headers=_auth(nayab),
        json={"status": "approved", "comments": "Looks good"},
    )
    assert reviewed.status_code == 200, reviewed.json()
    assert reviewed.json()["status"] == "APPROVED"
    assert reviewed.json()["approvals"]
    assert reviewed.json()["approvals"][0]["reviewer_id"] == str(people["nayab_id"])
    assert reviewed.json()["approvals"][0]["status"] == "APPROVED"

    detail = client.get(f"/api/timesheet/entries/{entry_id}", headers=_auth(nayab))
    assert detail.status_code == 200
    assert detail.json()["status"] == "APPROVED"


def test_hr_can_view_org_wide_submitted_entries(client: TestClient, people: dict[str, Any]) -> None:
    sameer = _token(client, "sameer@workpulse.local")
    sidrah = _token(client, "sidrah.hunain@workpulse.local")

    created = client.post("/api/timesheet/entries", headers=_auth(sameer), json=_entry_payload())
    assert created.status_code == 201, created.json()
    entry_id = created.json()["id"]
    submitted = client.post(f"/api/timesheet/entries/{entry_id}/submit", headers=_auth(sameer))
    assert submitted.status_code == 200, submitted.json()

    queue = client.get("/api/timesheet/team", headers=_auth(sidrah))
    assert queue.status_code == 200, queue.json()
    assert any(row["id"] == entry_id for row in queue.json())

    detail = client.get(f"/api/timesheet/entries/{entry_id}", headers=_auth(sidrah))
    assert detail.status_code == 200
    assert detail.json()["employee_id"] == str(people["sameer_id"])


def test_employee_cannot_approve_own_entry(client: TestClient) -> None:
    israh = _token(client, "israh.zunain@workpulse.local")
    created = client.post("/api/timesheet/entries", headers=_auth(israh), json=_entry_payload())
    assert created.status_code == 201, created.json()
    entry_id = created.json()["id"]
    submitted = client.post(f"/api/timesheet/entries/{entry_id}/submit", headers=_auth(israh))
    assert submitted.status_code == 200, submitted.json()

    review = client.post(
        f"/api/timesheet/entries/{entry_id}/review",
        headers=_auth(israh),
        json={"status": "APPROVED"},
    )
    assert review.status_code == 403


def test_employee_cannot_see_another_employees_entries(client: TestClient) -> None:
    israh = _token(client, "israh.zunain@workpulse.local")
    sameer = _token(client, "sameer@workpulse.local")

    created = client.post("/api/timesheet/entries", headers=_auth(sameer), json=_entry_payload())
    assert created.status_code == 201, created.json()
    entry_id = created.json()["id"]

    mine = client.get("/api/timesheet/entries", headers=_auth(israh))
    assert mine.status_code == 200
    assert all(row["id"] != entry_id for row in mine.json())

    other = client.get(f"/api/timesheet/entries/{entry_id}", headers=_auth(israh))
    assert other.status_code == 403

    team = client.get("/api/timesheet/team", headers=_auth(israh))
    assert team.status_code == 403
