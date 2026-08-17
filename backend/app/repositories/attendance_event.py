"""Attendance event persistence for agent ingestion."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.attendance import AttendanceEvent


def get_client_event_ids(session: Session, event_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not event_ids:
        return set()
    rows = session.scalars(select(AttendanceEvent.client_event_id).where(AttendanceEvent.client_event_id.in_(event_ids)))
    return set(rows)


def add_attendance_event(session: Session, event: AttendanceEvent) -> AttendanceEvent:
    session.add(event)
    return event


def list_events_for_employee_in_range(
    session: Session,
    employee_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> list[AttendanceEvent]:
    statement = (
        select(AttendanceEvent)
        .options(selectinload(AttendanceEvent.device))
        .where(
            AttendanceEvent.employee_id == employee_id,
            AttendanceEvent.event_time >= start,
            AttendanceEvent.event_time < end,
        )
        .order_by(AttendanceEvent.event_time.asc(), AttendanceEvent.id.asc())
    )
    return list(session.scalars(statement).unique())
