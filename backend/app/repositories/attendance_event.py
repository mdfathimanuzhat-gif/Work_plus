"""Attendance event persistence for agent ingestion."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceEvent


def get_client_event_ids(session: Session, event_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not event_ids:
        return set()
    rows = session.scalars(select(AttendanceEvent.client_event_id).where(AttendanceEvent.client_event_id.in_(event_ids)))
    return set(rows)


def add_attendance_event(session: Session, event: AttendanceEvent) -> AttendanceEvent:
    session.add(event)
    return event
