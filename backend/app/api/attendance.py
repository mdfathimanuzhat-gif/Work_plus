"""Read-only attendance APIs. Calculated values cannot be modified by clients."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.database.session import get_db
from app.schemas.attendance import AttendanceDayResponse, LiveAttendanceResponse, TeamAttendanceResponse
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/me", response_model=list[AttendanceDayResponse])
def get_my_attendance(
    user: CurrentUser,
    session: DbSession,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> list[AttendanceDayResponse]:
    records = attendance_service.list_my_attendance(session, user, start, end)
    session.commit()
    return records


@router.get("/me/live", response_model=LiveAttendanceResponse)
def get_my_live_attendance(user: CurrentUser, session: DbSession) -> LiveAttendanceResponse:
    return attendance_service.live_status(session, user, user.employee_id)


@router.get("/me/{attendance_date}", response_model=AttendanceDayResponse)
def get_my_attendance_on_date(
    attendance_date: date,
    user: CurrentUser,
    session: DbSession,
) -> AttendanceDayResponse:
    record = attendance_service.get_day_for_user(session, user, user.employee_id, attendance_date)
    session.commit()
    return record


@router.get("/team/{attendance_date}", response_model=TeamAttendanceResponse)
def get_team_attendance(
    attendance_date: date,
    user: CurrentUser,
    session: DbSession,
) -> TeamAttendanceResponse:
    payload = attendance_service.team_attendance_on_date(session, user, attendance_date)
    session.commit()
    return payload


@router.get("/{employee_id}/{attendance_date}", response_model=AttendanceDayResponse)
def get_employee_attendance(
    employee_id: uuid.UUID,
    attendance_date: date,
    user: CurrentUser,
    session: DbSession,
) -> AttendanceDayResponse:
    record = attendance_service.get_day_for_user(session, user, employee_id, attendance_date)
    session.commit()
    return record
