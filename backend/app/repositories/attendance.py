"""Attendance persistence helpers."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.attendance import Attendance, AttendanceEvent, AttendanceSession
from app.models.audit_log import AuditLog


def get_attendance(session: Session, employee_id: uuid.UUID, attendance_date: date) -> Attendance | None:
    return session.scalar(
        select(Attendance)
        .options(selectinload(Attendance.sessions))
        .where(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == attendance_date,
        )
    )


def list_attendance_range(
    session: Session,
    employee_id: uuid.UUID,
    start: date,
    end: date,
) -> list[Attendance]:
    return list(
        session.scalars(
            select(Attendance)
            .options(selectinload(Attendance.sessions))
            .where(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date >= start,
                Attendance.attendance_date <= end,
            )
            .order_by(Attendance.attendance_date)
        ).unique()
    )


def list_attendance_for_employees_on_date(
    session: Session,
    employee_ids: list[uuid.UUID],
    attendance_date: date,
) -> list[Attendance]:
    if not employee_ids:
        return []
    return list(
        session.scalars(
            select(Attendance)
            .options(selectinload(Attendance.sessions), selectinload(Attendance.employee))
            .where(
                Attendance.employee_id.in_(employee_ids),
                Attendance.attendance_date == attendance_date,
            )
            .order_by(Attendance.employee_id)
        ).unique()
    )


def get_or_create_attendance(session: Session, employee_id: uuid.UUID, attendance_date: date) -> Attendance:
    existing = get_attendance(session, employee_id, attendance_date)
    if existing is not None:
        return existing
    row = Attendance(employee_id=employee_id, attendance_date=attendance_date)
    session.add(row)
    session.flush()
    return row


def replace_sessions(session: Session, attendance: Attendance, rows: list[AttendanceSession]) -> None:
    session.execute(delete(AttendanceSession).where(AttendanceSession.attendance_id == attendance.id))
    session.flush()
    for row in rows:
        session.add(row)
    session.flush()


def list_events_for_employee(session: Session, employee_id: uuid.UUID) -> list[AttendanceEvent]:
    return list(
        session.scalars(
            select(AttendanceEvent)
            .where(AttendanceEvent.employee_id == employee_id)
            .order_by(AttendanceEvent.event_time, AttendanceEvent.id)
        )
    )


def assign_events_to_attendance(
    session: Session,
    employee_id: uuid.UUID,
    attendance_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> None:
    events = list(
        session.scalars(
            select(AttendanceEvent).where(
                AttendanceEvent.employee_id == employee_id,
                AttendanceEvent.event_time >= start,
                AttendanceEvent.event_time < end,
            )
        )
    )
    for event in events:
        event.attendance_id = attendance_id


def replace_anomaly_audit_logs(
    session: Session,
    *,
    organization_id: uuid.UUID,
    employee_id: uuid.UUID,
    attendance_id: uuid.UUID,
    payload: dict,
) -> None:
    session.execute(
        delete(AuditLog).where(
            AuditLog.entity_type == "attendance",
            AuditLog.entity_id == str(attendance_id),
            AuditLog.action == "attendance.recalculated",
        )
    )
    session.add(
        AuditLog(
            organization_id=organization_id,
            user_id=employee_id,
            action="attendance.recalculated",
            entity_type="attendance",
            entity_id=str(attendance_id),
            event_metadata=payload,
        )
    )
