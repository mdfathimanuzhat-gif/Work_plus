"""Ingest desktop-agent attendance events into PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.attendance import AttendanceEvent
from app.repositories import attendance_event as event_repository
from app.schemas.agent import (
    AGENT_TO_SERVER_EVENT,
    AgentEventBatchRequest,
    AgentEventBatchResponse,
    AgentEventResult,
)
from app.services.device_auth_service import AuthenticatedDevice

logger = logging.getLogger("workpulse.agent.ingest")


def ingest_event_batch(
    session: Session,
    device: AuthenticatedDevice,
    payload: AgentEventBatchRequest,
) -> AgentEventBatchResponse:
    settings = get_settings()
    if payload.device_id.strip() != device.device_identifier:
        raise APIError(403, "device_mismatch", "Events must be submitted by the authenticated device")
    if len(payload.events) > settings.AGENT_EVENT_MAX_BATCH:
        raise APIError(422, "batch_too_large", f"Batch cannot exceed {settings.AGENT_EVENT_MAX_BATCH} events")

    results: list[AgentEventResult] = []
    now = datetime.now(timezone.utc)
    min_time = now - timedelta(days=settings.AGENT_EVENT_MAX_AGE_DAYS)
    max_time = now + timedelta(seconds=settings.AGENT_EVENT_MAX_FUTURE_SECONDS)
    existing = event_repository.get_client_event_ids(session, [item.event_id for item in payload.events])

    for item in payload.events:
        if item.device_identifier != device.device_identifier:
            results.append(AgentEventResult(event_id=item.event_id, status="failed", reason="device_mismatch"))
            continue
        if item.event_timestamp < min_time or item.event_timestamp > max_time:
            results.append(AgentEventResult(event_id=item.event_id, status="failed", reason="timestamp_out_of_range"))
            continue
        if item.event_id in existing:
            results.append(AgentEventResult(event_id=item.event_id, status="duplicate", reason="already_processed"))
            continue
        try:
            with session.begin_nested():
                session.add(
                    AttendanceEvent(
                        employee_id=device.employee_id,
                        device_id=device.device_id,
                        client_event_id=item.event_id,
                        event_type=AGENT_TO_SERVER_EVENT[item.event_type],
                        event_time=item.event_timestamp,
                        event_metadata={
                            **item.metadata,
                            "device_name": item.device_name,
                            "username": item.username,
                            "agent_event_type": item.event_type,
                        },
                    )
                )
                session.flush()
            existing.add(item.event_id)
            results.append(AgentEventResult(event_id=item.event_id, status="accepted"))
        except IntegrityError:
            results.append(AgentEventResult(event_id=item.event_id, status="duplicate", reason="already_processed"))

    accepted = sum(1 for row in results if row.status == "accepted")
    duplicates = sum(1 for row in results if row.status == "duplicate")
    failed = sum(1 for row in results if row.status == "failed")
    logger.info(
        "Agent ingest device=%s employee=%s accepted=%s duplicates=%s failed=%s count=%s",
        device.device_identifier,
        device.employee_id,
        accepted,
        duplicates,
        failed,
        len(payload.events),
    )
    return AgentEventBatchResponse(
        accepted=accepted,
        duplicates=duplicates,
        failed=failed,
        results=results,
    )
