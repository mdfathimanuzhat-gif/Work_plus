"""Device identity, configuration, idle detector, and Win32 mappings."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import load_settings
from app.detectors.idle_detector import IdleDetector
from app.detectors.power_detector import (
    ENDSESSION_LOGOFF,
    ENDSESSION_RESTART,
    PBT_APMRESUMESUSPEND,
    PBT_APMSUSPEND,
    WM_ENDSESSION,
    WM_POWERBROADCAST,
    map_end_session,
    map_power_broadcast,
)
from app.detectors.session_detector import (
    WTS_SESSION_LOCK,
    WTS_SESSION_LOGOFF,
    WTS_SESSION_LOGON,
    WTS_SESSION_UNLOCK,
    map_session_notification,
)
from app.detectors.win32_loop import Win32EventLoop
from app.device import load_or_create_device_identity
from app.models import EventType, parse_event_type


class FakeClock:
    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def idle_seconds(self) -> float:
        return self.seconds


def test_stable_device_identifier(data_dir: Path) -> None:
    settings = load_settings(DATA_DIR=data_dir, LOG_DIR=data_dir / "logs")
    first = load_or_create_device_identity(settings)
    second = load_or_create_device_identity(settings)
    assert first.device_identifier == second.device_identifier
    assert (data_dir / "device_identity.json").is_file()
    assert first.device_identifier
    assert ":" not in first.device_identifier or first.device_identifier.count("-") == 4


def test_configuration_loading(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IDLE_THRESHOLD_SECONDS", "120")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("AGENT_MODE", "test")
    settings = load_settings(DATA_DIR=data_dir, LOG_DIR=data_dir / "logs")
    assert settings.IDLE_THRESHOLD_SECONDS == 120
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.is_test_mode is True


def test_invalid_idle_threshold_rejected(data_dir: Path) -> None:
    with pytest.raises(Exception):
        load_settings(DATA_DIR=data_dir, IDLE_THRESHOLD_SECONDS=0)


def test_session_notification_mapping() -> None:
    assert map_session_notification(WTS_SESSION_LOGON) is EventType.WINDOWS_LOGIN
    assert map_session_notification(WTS_SESSION_LOGOFF) is EventType.WINDOWS_LOGOUT
    assert map_session_notification(WTS_SESSION_LOCK) is EventType.SYSTEM_LOCK
    assert map_session_notification(WTS_SESSION_UNLOCK) is EventType.SYSTEM_UNLOCK
    assert map_session_notification(99) is None


def test_power_and_end_session_mapping() -> None:
    assert map_power_broadcast(PBT_APMSUSPEND) is EventType.SYSTEM_SLEEP
    assert map_power_broadcast(PBT_APMRESUMESUSPEND) is EventType.SYSTEM_WAKE
    assert map_end_session(1, ENDSESSION_LOGOFF) is EventType.WINDOWS_LOGOUT
    assert map_end_session(1, 0) is EventType.SYSTEM_SHUTDOWN
    assert map_end_session(1, 0, restart_requested=None) is EventType.SYSTEM_SHUTDOWN
    # Heuristics must not override a documented shutdown message.
    assert map_end_session(1, 0, restart_requested=True) is EventType.SYSTEM_SHUTDOWN
    assert map_end_session(1, ENDSESSION_RESTART) is EventType.SYSTEM_RESTART
    assert map_end_session(0, 0) is None


def test_idle_detector_start_and_end() -> None:
    recorded: list[EventType] = []
    clock = FakeClock(0)
    detector = IdleDetector(
        threshold_seconds=300,
        poll_interval_seconds=0.01,
        record=lambda event_type, metadata=None, source="idle": recorded.append(event_type),
        clock=clock,
    )
    detector.poll_once()
    assert recorded == []
    clock.seconds = 301
    detector.poll_once()
    detector.poll_once()
    assert recorded == [EventType.IDLE_START]
    clock.seconds = 1
    detector.poll_once()
    assert recorded == [EventType.IDLE_START, EventType.IDLE_END]


def test_idle_detector_skips_while_locked() -> None:
    recorded: list[EventType] = []
    clock = FakeClock(500)
    detector = IdleDetector(
        threshold_seconds=300,
        poll_interval_seconds=0.01,
        record=lambda event_type, metadata=None, source="idle": recorded.append(event_type),
        clock=clock,
        is_locked=lambda: True,
    )
    detector.poll_once()
    assert recorded == []


def test_win32_loop_dispatches_mapped_messages() -> None:
    recorded: list[tuple[EventType, str]] = []

    def record(event_type: EventType, metadata=None, source="detector") -> None:
        recorded.append((event_type, source))

    loop = Win32EventLoop(record)
    loop.handle_message(0x02B1, WTS_SESSION_LOCK, 0)
    loop.handle_message(WM_POWERBROADCAST, PBT_APMSUSPEND, 0)
    loop.handle_message(WM_ENDSESSION, 1, 0)
    assert recorded[0] == (EventType.SYSTEM_LOCK, "session")
    assert recorded[1] == (EventType.SYSTEM_SLEEP, "power")
    assert recorded[2][0] is EventType.SYSTEM_SHUTDOWN


def test_parse_test_mode_alias() -> None:
    assert parse_event_type("SYSTEM_LOGOUT") is EventType.WINDOWS_LOGOUT
    assert parse_event_type("windows_login") is EventType.WINDOWS_LOGIN


@pytest.mark.skipif(os.name != "nt", reason="Windows-only integration test")
def test_windows_last_input_api_available() -> None:
    from app.detectors.idle_detector import WindowsIdleClock

    seconds = WindowsIdleClock().idle_seconds()
    assert seconds >= 0
