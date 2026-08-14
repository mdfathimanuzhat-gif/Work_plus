"""Shared fixtures for desktop-agent unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import load_settings
from app.device import DeviceIdentity
from app.logger import configure_logging
from app.services.event_service import EventService


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    path = tmp_path / "storage"
    path.mkdir()
    (path / "logs").mkdir()
    return path


@pytest.fixture
def settings(data_dir: Path):
    return load_settings(
        DATA_DIR=data_dir,
        LOG_DIR=data_dir / "logs",
        IDLE_THRESHOLD_SECONDS=300,
        AGENT_MODE="test",
        LOG_LEVEL="INFO",
        TEST_EVENT_DELAY_SECONDS=0,
    )


@pytest.fixture
def device() -> DeviceIdentity:
    return DeviceIdentity(
        device_identifier="device-test-id",
        device_name="DESKTOP-TEST",
        operating_system="Windows",
        username="test-user",
    )


@pytest.fixture
def event_service(settings, device) -> EventService:
    configure_logging(settings)
    return EventService(device)
