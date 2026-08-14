"""Runtime: instance lock, status CLI, graceful shutdown, device identity."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from app.agent import DesktopAgent, print_status, run_agent
from app.config import load_settings
from app.device import load_or_create_device_identity
from app.models import EventType
from app.runtime.instance import InstanceLock, InstanceLockError
from app.runtime.status import collect_health, render_health, write_status_file
from app.storage.models import SyncStatus
from app.storage.repository import EventRepository
from main import main


def test_instance_lock_rejects_second_holder(tmp_path: Path) -> None:
    path = tmp_path / "agent.lock"
    first = InstanceLock(path)
    first.acquire()
    second = InstanceLock(path)
    with pytest.raises(InstanceLockError):
        second.acquire()
    first.release()
    second.acquire()
    second.release()


def test_second_agent_process_exits(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LOG_DIR", str(data_dir / "logs"))
    monkeypatch.setenv("LOCAL_DATABASE_PATH", str(data_dir / "events.db"))
    settings = load_settings(
        DATA_DIR=data_dir,
        LOG_DIR=data_dir / "logs",
        LOCAL_DATABASE_PATH=data_dir / "events.db",
        AGENT_MODE="test",
        TEST_EVENT_DELAY_SECONDS=0,
    )
    lock = InstanceLock(settings.instance_lock_path)
    lock.acquire()
    try:
        assert run_agent(settings, once=True) == 2
    finally:
        lock.release()


def test_status_command_reports_sqlite(data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LOG_DIR", str(data_dir / "logs"))
    monkeypatch.setenv("LOCAL_DATABASE_PATH", str(data_dir / "events.db"))
    monkeypatch.setenv("TEST_EVENT_DELAY_SECONDS", "0")
    monkeypatch.setenv("API_BASE_URL", "")
    assert main(["--test", "--once"]) == 0
    capsys.readouterr()
    code = main(["--status"])
    assert code == 0
    output = capsys.readouterr().out
    assert "Agent status:" in output
    assert "Pending events:" in output
    assert "SQLite available: True" in output
    assert "Backend:" in output
    assert "Device ID:" in output


def test_health_render_omits_secrets(settings, device) -> None:
    health = collect_health(settings, agent_status="STOPPED", backend="OFFLINE", device=device)
    text = render_health(health)
    assert "password" not in text.lower()
    assert "secret" not in text.lower()
    assert "jwt" not in text.lower()
    assert health.device_id == device.device_identifier


def test_device_identifier_survives_restart(settings) -> None:
    first = load_or_create_device_identity(settings)
    second = load_or_create_device_identity(settings)
    assert first.device_identifier == second.device_identifier
    assert (settings.DATA_DIR / "device_identity.json").is_file()


def test_agent_restart_keeps_sqlite_events(settings) -> None:
    agent = DesktopAgent(settings)
    agent.run_test_scenario(["WINDOWS_LOGIN", "SYSTEM_LOCK"])
    event_ids = [event.event_id for event in agent.service.events]
    assert event_ids
    agent.stop()
    restarted = DesktopAgent(settings)
    stored = restarted.repository.list_events()
    assert {item.event.event_id for item in stored} == set(event_ids)
    assert all(item.sync_status is SyncStatus.PENDING for item in stored)


def test_graceful_stop_releases_wait(settings) -> None:
    agent = DesktopAgent(settings)
    finished = threading.Event()

    def waiter() -> None:
        agent.wait()
        finished.set()

    thread = threading.Thread(target=waiter)
    thread.start()
    agent.request_stop()
    thread.join(timeout=2)
    assert finished.is_set()
    agent.stop()


def test_shutdown_ignores_new_idle_events(event_service) -> None:
    event_service.record(EventType.WINDOWS_LOGIN, source="test")
    event_service.begin_shutdown()
    assert event_service.record(EventType.SYSTEM_LOCK, source="test") is None
    assert event_service.record(EventType.SYSTEM_SHUTDOWN, source="test") is not None


def test_live_mode_exits_on_non_windows(settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.is_windows", lambda: False)
    settings.AGENT_MODE = "live"
    assert run_agent(settings, once=True) == 1


def test_status_file_omits_secrets(settings, tmp_path: Path) -> None:
    health = collect_health(settings, agent_status="RUNNING", backend="OFFLINE")
    path = tmp_path / "status.json"
    write_status_file(path, health)
    payload = json.loads(path.read_text(encoding="utf-8"))
    forbidden = {"password", "secret", "jwt", "token", "device_secret"}
    assert forbidden.isdisjoint(payload.keys())
    blob = json.dumps({k: v for k, v in payload.items() if k not in {"database_path", "log_dir"}})
    lower = blob.lower()
    assert "password" not in lower
    assert "jwt" not in lower
    assert "device_secret" not in lower


def test_latest_event_helpers(settings, device) -> None:
    from app.models import AgentEvent

    repo = EventRepository(settings.local_database_path)
    event = AgentEvent.create(
        EventType.SYSTEM_LOCK,
        device_identifier=device.device_identifier,
        device_name=device.device_name,
        operating_system=device.operating_system,
        username=device.username,
    )
    repo.save_event(event)
    latest = repo.get_latest_event()
    assert latest is not None
    assert latest.event.event_id == event.event_id
    assert repo.get_latest_synced_at() is None
    repo.mark_event_synced(event.event_id)
    assert repo.get_latest_synced_at() is not None
