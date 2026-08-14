"""Event recording, de-duplication, ordering, and unexpected sequences."""

from __future__ import annotations

from app.models import EventType
from app.services.event_service import EventService


def _types(service: EventService) -> list[str]:
    return [event.event_type.value for event in service.events]


def test_login_event(event_service: EventService) -> None:
    event = event_service.record(EventType.WINDOWS_LOGIN)
    assert event is not None
    assert event.event_type is EventType.WINDOWS_LOGIN
    assert event.device_name == "DESKTOP-TEST"
    assert event.username == "test-user"
    assert "password" not in event.to_dict()


def test_logout_event(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    event = event_service.record(EventType.WINDOWS_LOGOUT)
    assert event is not None
    assert event.event_type is EventType.WINDOWS_LOGOUT


def test_lock_and_unlock_events(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    lock = event_service.record(EventType.SYSTEM_LOCK)
    unlock = event_service.record(EventType.SYSTEM_UNLOCK)
    assert lock is not None and unlock is not None
    assert _types(event_service) == ["WINDOWS_LOGIN", "SYSTEM_LOCK", "SYSTEM_UNLOCK"]


def test_shutdown_and_restart_events(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    event_service.record(EventType.WINDOWS_LOGOUT)
    shutdown = event_service.record(EventType.SYSTEM_SHUTDOWN)
    restart = event_service.record(EventType.SYSTEM_RESTART)
    assert shutdown is not None and restart is not None
    assert shutdown.event_type is EventType.SYSTEM_SHUTDOWN
    assert restart.event_type is EventType.SYSTEM_RESTART


def test_sleep_and_wake_events(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    assert event_service.record(EventType.SYSTEM_SLEEP) is not None
    assert event_service.record(EventType.SYSTEM_WAKE) is not None


def test_idle_start_and_end_events(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    assert event_service.record(EventType.IDLE_START) is not None
    assert event_service.record(EventType.IDLE_END) is not None


def test_duplicate_lock_is_suppressed(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    first = event_service.record(EventType.SYSTEM_LOCK)
    second = event_service.record(EventType.SYSTEM_LOCK)
    third = event_service.record(EventType.SYSTEM_LOCK)
    assert first is not None
    assert second is None and third is None
    assert _types(event_service).count("SYSTEM_LOCK") == 1


def test_duplicate_idle_start_is_suppressed(event_service: EventService) -> None:
    event_service.record(EventType.IDLE_START)
    assert event_service.record(EventType.IDLE_START) is None
    assert _types(event_service) == ["IDLE_START"]


def test_chronological_ordering_and_unique_ids(event_service: EventService) -> None:
    sequence = [
        EventType.WINDOWS_LOGIN,
        EventType.SYSTEM_LOCK,
        EventType.SYSTEM_UNLOCK,
        EventType.IDLE_START,
        EventType.IDLE_END,
        EventType.WINDOWS_LOGOUT,
    ]
    for event_type in sequence:
        event_service.record(event_type)
    events = event_service.events
    timestamps = [item.event_timestamp for item in events]
    assert timestamps == sorted(timestamps)
    ids = [item.event_id for item in events]
    assert len(ids) == len(set(ids))
    assert all(item.event_type for item in events)


def test_unlock_without_lock_is_recorded_with_anomaly(event_service: EventService) -> None:
    event = event_service.record(EventType.SYSTEM_UNLOCK)
    assert event is not None
    assert event.metadata.get("anomaly") == "unlock_without_lock"


def test_shutdown_without_logout_is_recorded_with_anomaly(event_service: EventService) -> None:
    event_service.record(EventType.WINDOWS_LOGIN)
    event = event_service.record(EventType.SYSTEM_SHUTDOWN)
    assert event is not None
    assert event.metadata.get("anomaly") == "shutdown_without_logout"


def test_listener_failure_does_not_crash(event_service: EventService) -> None:
    def boom(_event: object) -> None:
        raise RuntimeError("listener exploded")

    event_service.add_listener(boom)
    event = event_service.record(EventType.WINDOWS_LOGIN)
    assert event is not None
    assert event.event_id
