"""Timesheet entry and approval routes."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.database.session import get_db
from app.schemas.timesheet import ApprovalDecision, TimesheetCreate, TimesheetDetailOut, TimesheetOut
from app.services import timesheet_service

router = APIRouter(prefix="/timesheet", tags=["timesheet"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/entries", response_model=TimesheetOut, status_code=201)
def create_entry(
    body: TimesheetCreate,
    user: CurrentUser,
    session: DbSession,
) -> TimesheetOut:
    row = timesheet_service.create_own_entry(session, user, body)
    session.commit()
    return timesheet_service.serialize_timesheet(row)


@router.get("/entries", response_model=list[TimesheetOut])
def list_own_entries(
    user: CurrentUser,
    session: DbSession,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[TimesheetOut]:
    rows = timesheet_service.list_own_entries(session, user, date_from, date_to)
    return [timesheet_service.serialize_timesheet(row) for row in rows]


@router.get("/team", response_model=list[TimesheetOut])
def list_team_entries(
    user: CurrentUser,
    session: DbSession,
) -> list[TimesheetOut]:
    rows = timesheet_service.list_team_queue(session, user)
    return [timesheet_service.serialize_timesheet(row) for row in rows]


@router.post("/entries/{timesheet_id}/submit", response_model=TimesheetOut)
def submit_entry(
    timesheet_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> TimesheetOut:
    row = timesheet_service.submit_own_entry(session, user, timesheet_id)
    session.commit()
    return timesheet_service.serialize_timesheet(row)


@router.post("/entries/{timesheet_id}/review", response_model=TimesheetDetailOut)
def review_entry(
    timesheet_id: uuid.UUID,
    body: ApprovalDecision,
    user: CurrentUser,
    session: DbSession,
) -> TimesheetDetailOut:
    row = timesheet_service.review_entry(session, user, timesheet_id, body)
    session.commit()
    return timesheet_service.serialize_timesheet_detail(row)


@router.get("/entries/{timesheet_id}", response_model=TimesheetDetailOut)
def get_entry(
    timesheet_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> TimesheetDetailOut:
    row = timesheet_service.get_visible_entry(session, user, timesheet_id)
    return timesheet_service.serialize_timesheet_detail(row)
