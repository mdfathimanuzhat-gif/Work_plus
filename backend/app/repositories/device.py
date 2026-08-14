"""Device persistence helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.device import Device
from app.models.employee import Employee
from app.models.rbac import EmployeeRole


def get_device_by_id(session: Session, device_id: uuid.UUID) -> Device | None:
    return session.scalar(
        select(Device)
        .options(
            selectinload(Device.employee).selectinload(Employee.organization),
            selectinload(Device.employee).selectinload(Employee.employee_roles).selectinload(EmployeeRole.role),
        )
        .where(Device.id == device_id)
    )


def get_device_by_identifier(session: Session, device_identifier: str) -> Device | None:
    return session.scalar(
        select(Device)
        .options(selectinload(Device.employee))
        .where(Device.device_identifier == device_identifier)
    )


def get_device_by_secret_hash(session: Session, secret_hash: str) -> Device | None:
    return session.scalar(
        select(Device)
        .options(selectinload(Device.employee))
        .where(Device.secret_hash == secret_hash)
    )


def touch_device(device: Device) -> None:
    device.last_seen_at = datetime.now(timezone.utc)
