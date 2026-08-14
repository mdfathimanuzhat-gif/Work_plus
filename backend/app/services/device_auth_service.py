"""Device enrollment and device-token issuance."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import create_device_token, hash_token
from app.models.device import Device
from app.repositories import device as device_repository
from app.schemas.agent import DeviceEnrollRequest, DeviceEnrollResponse, DeviceTokenResponse
from app.services.authorization import AuthenticatedUser


@dataclass(frozen=True)
class AuthenticatedDevice:
    device: Device

    @property
    def device_id(self) -> uuid.UUID:
        return self.device.id

    @property
    def employee_id(self) -> uuid.UUID:
        return self.device.employee_id

    @property
    def organization_id(self) -> uuid.UUID:
        return self.device.employee.organization_id

    @property
    def device_identifier(self) -> str:
        return self.device.device_identifier


def enroll_device(session: Session, user: AuthenticatedUser, payload: DeviceEnrollRequest) -> DeviceEnrollResponse:
    identifier = payload.device_identifier.strip()
    existing = device_repository.get_device_by_identifier(session, identifier)
    if existing is not None and existing.employee_id != user.employee_id:
        raise APIError(409, "device_in_use", "This device is already registered to another employee")
    secret = secrets.token_urlsafe(32)
    secret_hash = hash_token(secret)
    if existing is None:
        device = Device(
            employee_id=user.employee_id,
            device_name=payload.device_name.strip(),
            device_identifier=identifier,
            operating_system=payload.operating_system,
            is_active=True,
            secret_hash=secret_hash,
        )
        session.add(device)
        session.flush()
    else:
        if not existing.is_active:
            raise APIError(403, "device_inactive", "This device is inactive")
        existing.device_name = payload.device_name.strip()
        existing.operating_system = payload.operating_system
        existing.secret_hash = secret_hash
        device = existing
        session.flush()
    return DeviceEnrollResponse(
        device_id=device.id,
        device_identifier=device.device_identifier,
        device_secret=secret,
    )


def issue_device_token(session: Session, device_identifier: str, device_secret: str) -> DeviceTokenResponse:
    device = device_repository.get_device_by_identifier(session, device_identifier.strip())
    if device is None or not device.secret_hash:
        raise APIError(401, "invalid_device_credentials", "Invalid device credentials")
    if hash_token(device_secret) != device.secret_hash:
        raise APIError(401, "invalid_device_credentials", "Invalid device credentials")
    if not device.is_active or not device.employee.is_active:
        raise APIError(403, "device_inactive", "This device is inactive")
    settings = get_settings()
    token, _, _ = create_device_token(
        device_id=device.id,
        employee_id=device.employee_id,
        organization_id=device.employee.organization_id,
        device_identifier=device.device_identifier,
        expires_delta=timedelta(minutes=settings.DEVICE_TOKEN_EXPIRE_MINUTES),
    )
    device_repository.touch_device(device)
    return DeviceTokenResponse(
        access_token=token,
        expires_in=settings.DEVICE_TOKEN_EXPIRE_MINUTES * 60,
    )


def load_authenticated_device(session: Session, payload: dict) -> AuthenticatedDevice:
    try:
        device_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise APIError(401, "invalid_token", "Invalid token") from exc
    device = device_repository.get_device_by_id(session, device_id)
    if device is None or not device.is_active or not device.employee.is_active:
        raise APIError(401, "invalid_token", "Invalid token")
    token_identifier = payload.get("device_identifier")
    if token_identifier and token_identifier != device.device_identifier:
        raise APIError(401, "invalid_token", "Invalid token")
    token_org = payload.get("organization_id")
    if token_org and str(device.employee.organization_id) != str(token_org):
        raise APIError(401, "invalid_token", "Invalid token")
    device_repository.touch_device(device)
    return AuthenticatedDevice(device=device)
