"""Persist derived attendance from raw events. Clients cannot write these values."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.attendance import Attendance, AttendanceSession
from app.models.employee import Employee
from app.models.enums import AttendanceSessionStatus
from app.repositories import attendance as attendance_repository
from app.repositories import employee as employee_repository
from app.schemas.attendance import (
    AttendanceAnomalyResponse,
    AttendanceDayResponse,
    AttendanceSessionResponse,
    LiveAttendanceResponse,
    TeamAttendanceResponse,
)
from app.services.attendance_engine import (
    DailyAttendance,
    EngineEvent,
    empty_day,
    ensure_utc,
    load_zoneinfo,
    local_date,
    local_day_bounds,
    replay_events,
)
from app.services.authorization import AuthenticatedUser, ensure_can_view_attendance, has_permission, has_role

logger = logging.getLogger("workpulse.attendance")


def _timezone_name(employee: Employee) -> str:
    return employee.organization.timezone if employee.organization and employee.organization.timezone else "UTC"


def _engine_events(session: Session, employee_id: uuid.UUID) -> list[EngineEvent]:
    rows = attendance_repository.list_events_for_employee(session, employee_id)
    return [
        EngineEvent(
            event_id=row.id,
            event_type=row.event_type,
            event_time=ensure_utc(row.event_time),
            device_id=row.device_id,
        )
        for row in rows
    ]


def _serialize_anomalies(day: DailyAttendance) -> list[dict]:
    return [
        {
            "code": item.code,
            "message": item.message,
            "event_time": ensure_utc(item.event_time).isoformat(),
            "event_type": item.event_type,
        }
        for item in day.anomalies
    ]


def serialize_attendance(row: Attendance) -> AttendanceDayResponse:
    raw = row.anomalies if isinstance(row.anomalies, list) else []
    anomalies = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        event_time = item.get("event_time")
        parsed = datetime.fromisoformat(str(event_time).replace("Z", "+00:00")) if event_time else datetime.now(timezone.utc)
        anomalies.append(
            AttendanceAnomalyResponse(
                code=str(item.get("code", "unknown")),
                message=str(item.get("message", "")),
                event_time=ensure_utc(parsed),
                event_type=str(item.get("event_type", "")),
            )
        )
    return AttendanceDayResponse(
        id=row.id,
        employee_id=row.employee_id,
        attendance_date=row.attendance_date,
        first_login_time=row.check_in_time,
        last_logout_time=row.check_out_time,
        total_session_seconds=row.total_session_seconds,
        total_locked_seconds=row.total_locked_seconds,
        total_idle_seconds=row.total_idle_seconds,
        total_sleep_seconds=row.total_sleep_seconds,
        total_active_seconds=row.total_work_seconds,
        session_count=row.session_count,
        status=row.status,
        is_complete=row.is_complete,
        calculated_at=row.calculated_at,
        anomalies=anomalies,
        sessions=[AttendanceSessionResponse.model_validate(item) for item in row.sessions],
    )


def persist_daily_attendance(
    session: Session,
    employee: Employee,
    day: DailyAttendance,
    *,
    calculated_at: datetime,
) -> Attendance:
    tz = load_zoneinfo(_timezone_name(employee))
    row = attendance_repository.get_or_create_attendance(session, employee.id, day.attendance_date)
    row.check_in_time = day.first_login_time
    row.check_out_time = day.last_logout_time
    row.total_work_seconds = max(0, day.total_active_seconds)
    row.total_idle_seconds = max(0, day.total_idle_seconds)
    row.total_locked_seconds = max(0, day.total_locked_seconds)
    row.total_sleep_seconds = max(0, day.total_sleep_seconds)
    row.total_session_seconds = max(0, day.total_session_seconds)
    row.session_count = day.session_count
    row.status = day.status
    row.is_complete = day.is_complete
    row.calculated_at = calculated_at
    row.anomalies = _serialize_anomalies(day)
    session.flush()

    session_rows = [
        AttendanceSession(
            attendance_id=row.id,
            employee_id=employee.id,
            device_id=item.device_id,
            session_start=item.session_start,
            session_end=item.session_end,
            session_duration_seconds=item.session_duration_seconds,
            locked_seconds=item.locked_seconds,
            idle_seconds=item.idle_seconds,
            sleep_seconds=item.sleep_seconds,
            active_seconds=item.active_seconds,
            status=AttendanceSessionStatus(item.status.value),
            ended_reason=item.ended_reason,
        )
        for item in day.sessions
    ]
    attendance_repository.replace_sessions(session, row, session_rows)
    start, end = local_day_bounds(day.attendance_date, tz)
    attendance_repository.assign_events_to_attendance(session, employee.id, row.id, start, end)
    attendance_repository.replace_anomaly_audit_logs(
        session,
        organization_id=employee.organization_id,
        employee_id=employee.id,
        attendance_id=row.id,
        payload={
            "attendance_date": day.attendance_date.isoformat(),
            "anomaly_count": len(day.anomalies),
            "anomalies": row.anomalies,
        },
    )
    logger.info(
        "Recalculated attendance employee=%s date=%s status=%s sessions=%s active=%s",
        employee.id,
        day.attendance_date,
        day.status.value,
        day.session_count,
        day.total_active_seconds,
    )
    return attendance_repository.get_attendance(session, employee.id, day.attendance_date) or row


def recalculate_employee(
    session: Session,
    employee: Employee,
    *,
    as_of: datetime | None = None,
    dates: set[date] | None = None,
) -> dict[date, Attendance]:
    """Replace derived attendance for the given dates from raw events."""
    now = ensure_utc(as_of or datetime.now(timezone.utc))
    result = replay_events(_engine_events(session, employee.id), timezone_name=_timezone_name(employee), as_of=now)
    target_dates = dates if dates is not None else set(result.days)
    stored: dict[date, Attendance] = {}
    for day in sorted(target_dates):
        computed = result.days.get(day) or empty_day(day)
        stored[day] = persist_daily_attendance(session, employee, computed, calculated_at=now)
    return stored


def recalculate_for_event_times(
    session: Session,
    employee: Employee,
    event_times: list[datetime],
    *,
    as_of: datetime | None = None,
) -> None:
    if not event_times:
        return
    tz = load_zoneinfo(_timezone_name(employee))
    dates: set[date] = set()
    for moment in event_times:
        day = local_date(moment, tz)
        dates.add(day)
        dates.add(day - timedelta(days=1))
        dates.add(day + timedelta(days=1))
    recalculate_employee(session, employee, as_of=as_of, dates=dates)


def get_day_for_user(
    session: Session,
    user: AuthenticatedUser,
    employee_id: uuid.UUID,
    attendance_date: date,
) -> AttendanceDayResponse:
    employee = employee_repository.get_employee_by_id(session, employee_id)
    ensure_can_view_attendance(user, employee)
    assert employee is not None
    stored = recalculate_employee(session, employee, dates={attendance_date})
    return serialize_attendance(stored[attendance_date])


def list_my_attendance(
    session: Session,
    user: AuthenticatedUser,
    start: date | None,
    end: date | None,
) -> list[AttendanceDayResponse]:
    employee = employee_repository.get_employee_by_id(session, user.employee_id)
    assert employee is not None
    tz = load_zoneinfo(_timezone_name(employee))
    today = local_date(datetime.now(timezone.utc), tz)
    range_end = end or today
    range_start = start or (range_end - timedelta(days=6))
    if range_end < range_start:
        raise APIError(422, "invalid_range", "end date must be on or after start date")
    if (range_end - range_start).days > 62:
        raise APIError(422, "invalid_range", "Date range cannot exceed 62 days")
    dates = {range_start + timedelta(days=offset) for offset in range((range_end - range_start).days + 1)}
    stored = recalculate_employee(session, employee, dates=dates)
    return [serialize_attendance(stored[day]) for day in sorted(stored)]


def live_status(session: Session, user: AuthenticatedUser, employee_id: uuid.UUID) -> LiveAttendanceResponse:
    employee = employee_repository.get_employee_by_id(session, employee_id)
    ensure_can_view_attendance(user, employee)
    assert employee is not None
    now = datetime.now(timezone.utc)
    tz_name = _timezone_name(employee)
    tz = load_zoneinfo(tz_name)
    result = replay_events(_engine_events(session, employee.id), timezone_name=tz_name, as_of=now)
    return LiveAttendanceResponse(
        employee_id=employee.id,
        state=result.live_state,
        as_of=now,
        attendance_date=local_date(now, tz),
        timezone=tz_name,
    )


def team_attendance_on_date(
    session: Session,
    user: AuthenticatedUser,
    attendance_date: date,
) -> TeamAttendanceResponse:
    if not (
        has_role(user, "ADMIN")
        or has_permission(user, "attendance.view_team", "attendance.view_organization")
    ):
        raise APIError(403, "forbidden", "You do not have access to team attendance")

    if has_role(user, "ADMIN") or has_permission(user, "attendance.view_organization"):
        employees = employee_repository.list_employees_in_organization(session, user.organization_id)
    else:
        team_ids = set(user.led_team_ids)
        if user.employee.team_id is not None:
            team_ids.add(user.employee.team_id)
        employees = []
        seen: set[uuid.UUID] = set()
        for team_id in team_ids:
            for member in employee_repository.list_employees_on_team(session, team_id):
                if member.id not in seen:
                    seen.add(member.id)
                    employees.append(member)
    records = []
    for employee in employees:
        if not can_view_member(user, employee):
            continue
        stored = recalculate_employee(session, employee, dates={attendance_date})
        records.append(serialize_attendance(stored[attendance_date]))
    return TeamAttendanceResponse(attendance_date=attendance_date, records=records)


def can_view_member(user: AuthenticatedUser, employee: Employee) -> bool:
    try:
        ensure_can_view_attendance(user, employee)
        return True
    except APIError:
        return False
