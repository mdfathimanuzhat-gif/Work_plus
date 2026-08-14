"""Shared fixtures for desktop-agent unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Tests are often launched from the repo root:
#   .venv\Scripts\python.exe -m pytest .\desktop-agent\tests
# Put this package first so `import app` is desktop-agent, not backend/app
# and not a stale copy in site-packages.
_AGENT_ROOT = Path(__file__).resolve().parents[1]
_agent_root = str(_AGENT_ROOT)
if sys.path[:1] != [_agent_root]:
    sys.path.insert(0, _agent_root)

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
        LOCAL_DATABASE_PATH=data_dir / "events.db",
        IDLE_THRESHOLD_SECONDS=300,
        AGENT_MODE="test",
        LOG_LEVEL="INFO",
        TEST_EVENT_DELAY_SECONDS=0,
        LOCAL_EVENT_RETENTION_DAYS=30,
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
    from app.storage.repository import EventRepository

    return EventService(device, repository=EventRepository(settings.local_database_path))
