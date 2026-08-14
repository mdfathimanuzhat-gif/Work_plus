"""Desktop-agent enrollment, device tokens, and event ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_device_payload
from app.core.errors import APIError
from app.database.session import get_db
from app.repositories import token as token_repository
from app.schemas.agent import (
    AgentEventBatchRequest,
    AgentEventBatchResponse,
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DeviceTokenRequest,
    DeviceTokenResponse,
)
from app.services import device_auth_service, event_ingest_service
from app.services.device_auth_service import AuthenticatedDevice

router = APIRouter(prefix="/agent", tags=["agent"])
DbSession = Annotated[Session, Depends(get_db)]


def require_authenticated_device(
    session: DbSession,
    payload: Annotated[dict, Depends(get_device_payload)],
) -> AuthenticatedDevice:
    jti = str(payload.get("jti", ""))
    if not jti or token_repository.is_access_jti_revoked(session, jti):
        raise APIError(401, "invalid_token", "Invalid token")
    expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise APIError(401, "token_expired", "Token has expired")
    return device_auth_service.load_authenticated_device(session, payload)


CurrentDevice = Annotated[AuthenticatedDevice, Depends(require_authenticated_device)]


@router.post("/devices/enroll", response_model=DeviceEnrollResponse)
def enroll_device(
    body: DeviceEnrollRequest,
    user: CurrentUser,
    session: DbSession,
) -> DeviceEnrollResponse:
    result = device_auth_service.enroll_device(session, user, body)
    session.commit()
    return result


@router.post("/auth/token", response_model=DeviceTokenResponse)
def device_token(body: DeviceTokenRequest, session: DbSession) -> DeviceTokenResponse:
    tokens = device_auth_service.issue_device_token(session, body.device_identifier, body.device_secret)
    session.commit()
    return tokens


@router.post("/events/batch", response_model=AgentEventBatchResponse)
def ingest_events(
    body: AgentEventBatchRequest,
    device: CurrentDevice,
    session: DbSession,
) -> AgentEventBatchResponse:
    result = event_ingest_service.ingest_event_batch(session, device, body)
    session.commit()
    return result
