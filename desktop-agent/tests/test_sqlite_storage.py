"""SQLite local event queue tests. Uses temporary database files only."""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from app.config import load_settings
from app.models import AgentEvent, EventType, utc_now
from app.storage.database import initialize_database
from app.storage.models import SyncStatus
from app.storage.repository import DuplicateEventError, EventRepository


def _event(device, event_type: EventType = EventType.WINDOWS_LOGIN, event_id: str | None = None) -> AgentEvent:
    return AgentEvent.create(
        event_type,
        device_identifier=device.device_identifier,
        device_name=device.device_name,
        operating_system=device.operating_system,
        username=device.username,
        event_id=event_id,
        metadata={"source": "test"},
    )


@pytest.fixture
def repository(data_dir: Path) -> EventRepository:
    return EventRepository(data_dir / "events.db")


def test_database_and_table_creation(data_dir: Path) -> None:
    path = initialize_database(data_dir / "events.db")
    assert path.is_file()
    connection = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "attendance_events" in tables
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(attendance_events)")
        }
        expected = {
            "id",
            "event_id",
            "event_type",
            "event_timestamp",
            "device_identifier",
            "device_name",
            "username",
            "metadata",
            "sync_status",
            "sync_attempts",
            "last_sync_attempt",
            "synced_at",
            "created_at",
        }
        assert expected <= columns
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal"
    finally:
        connection.close()


def test_save_and_retrieve_event(repository: EventRepository, device) -> None:
    created = repository.save_event(_event(device, EventType.SYSTEM_LOCK))
    assert created.sync_status is SyncStatus.PENDING
    assert created.sync_attempts == 0
    loaded = repository.get_event_by_id(created.event.event_id)
    assert loaded is not None
    assert loaded.event.event_type is EventType.SYSTEM_LOCK
    assert loaded.event.username == "test-user"


def test_retrieve_pending_events(repository: EventRepository, device) -> None:
    first = repository.save_event(_event(device, EventType.WINDOWS_LOGIN))
    second = repository.save_event(_event(device, EventType.SYSTEM_LOCK))
    repository.mark_event_synced(second.event.event_id)
    pending = repository.get_pending_events()
    assert [item.event.event_id for item in pending] == [first.event.event_id]


def test_unique_event_id_and_duplicate_rejection(repository: EventRepository, device) -> None:
    event = _event(device, EventType.SYSTEM_UNLOCK, event_id="same-id")
    repository.save_event(event)
    with pytest.raises(DuplicateEventError):
        repository.save_event(event)
    assert repository.get_event_count() == 1


def test_mark_syncing_synced_failed_and_attempt_counter(repository: EventRepository, device) -> None:
    stored = repository.save_event(_event(device, EventType.IDLE_START))
    event_id = stored.event.event_id
    syncing = repository.mark_event_syncing(event_id)
    assert syncing is not None
    assert syncing.sync_status is SyncStatus.SYNCING
    assert syncing.sync_attempts == 1
    assert syncing.last_sync_attempt is not None
    repository.mark_event_syncing(event_id)
    again = repository.get_event_by_id(event_id)
    assert again is not None and again.sync_attempts == 2
    failed = repository.mark_event_failed(event_id)
    assert failed is not None and failed.sync_status is SyncStatus.FAILED
    synced = repository.mark_event_synced(event_id)
    assert synced is not None
    assert synced.sync_status is SyncStatus.SYNCED
    assert synced.synced_at is not None


def test_database_restart_persistence(data_dir: Path, device) -> None:
    path = data_dir / "events.db"
    first = EventRepository(path)
    saved = first.save_event(_event(device, EventType.WINDOWS_LOGOUT))
    second = EventRepository(path)
    loaded = second.get_event_by_id(saved.event.event_id)
    assert loaded is not None
    assert loaded.sync_status is SyncStatus.PENDING
    assert loaded.event.event_type is EventType.WINDOWS_LOGOUT


def test_multiple_event_insertion(repository: EventRepository, device) -> None:
    types = [EventType.WINDOWS_LOGIN, EventType.SYSTEM_LOCK, EventType.SYSTEM_UNLOCK]
    for event_type in types:
        repository.save_event(_event(device, event_type))
    assert repository.get_event_count() == 3
    assert repository.get_event_count(SyncStatus.PENDING) == 3


def test_sqlite_transaction_rollback(repository: EventRepository, device) -> None:
    first = _event(device, EventType.SYSTEM_SLEEP, event_id="keep-me")
    duplicate = _event(device, EventType.SYSTEM_WAKE, event_id="keep-me")
    with pytest.raises(DuplicateEventError):
        repository.save_events_atomic([first, duplicate])
    assert repository.get_event_count() == 0


def test_offline_event_persistence(repository: EventRepository, device) -> None:
    stored = repository.save_event(_event(device, EventType.SYSTEM_SHUTDOWN))
    assert stored.sync_status is SyncStatus.PENDING
    assert repository.get_pending_events()[0].event.event_id == stored.event.event_id


def test_event_retention_query_and_cleanup(repository: EventRepository, device) -> None:
    stored = repository.save_event(_event(device, EventType.SYSTEM_RESTART))
    repository.mark_event_synced(stored.event.event_id)
    assert repository.events_eligible_for_cleanup(retention_days=30) == []
    connection = sqlite3.connect(repository.database_path)
    old = (utc_now() - timedelta(days=40)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        connection.execute(
            "UPDATE attendance_events SET synced_at = ? WHERE event_id = ?",
            (old, stored.event.event_id),
        )
        connection.commit()
    finally:
        connection.close()
    eligible = repository.events_eligible_for_cleanup(retention_days=30)
    assert len(eligible) == 1
    pending = repository.save_event(_event(device, EventType.IDLE_END))
    deleted = repository.cleanup_synced_events(retention_days=30)
    assert deleted == 1
    assert repository.get_event_by_id(stored.event.event_id) is None
    assert repository.get_event_by_id(pending.event.event_id) is not None


def test_event_service_persists_and_restores(settings, device) -> None:
    from app.models import EventType
    from app.services.event_service import EventService
    from app.storage.repository import EventRepository

    repository = EventRepository(settings.local_database_path)
    service = EventService(device, repository=repository)
    event = service.record(EventType.WINDOWS_LOGIN)
    assert event is not None
    assert repository.get_pending_events()[0].event.event_id == event.event_id
    restored = EventService(device, repository=EventRepository(settings.local_database_path))
    assert restored.state.logged_in is True
    assert restored.events[0].event_id == event.event_id


def test_database_path_configuration(data_dir: Path) -> None:
    custom = data_dir / "custom" / "workpulse.sqlite"
    settings = load_settings(DATA_DIR=data_dir, LOCAL_DATABASE_PATH=custom, LOG_DIR=data_dir / "logs")
    assert settings.local_database_path == custom
    EventRepository(settings.local_database_path)
    assert custom.is_file()
