"""Test-mode simulator and CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.agent import DesktopAgent, run_agent
from app.models import EventType
from app.services.simulator import DEFAULT_SCENARIO, simulate_events
from main import main


def test_simulator_emits_expected_types(event_service) -> None:
    simulate_events(event_service.record, delay_seconds=0)
    types = [event.event_type for event in event_service.events]
    assert EventType.WINDOWS_LOGIN in types
    assert EventType.SYSTEM_LOCK in types
    assert EventType.SYSTEM_UNLOCK in types
    assert EventType.IDLE_START in types
    assert EventType.IDLE_END in types
    assert EventType.WINDOWS_LOGOUT in types
    assert EventType.SYSTEM_SHUTDOWN in types
    assert EventType.SYSTEM_RESTART in types
    assert all(event.metadata.get("source") == "test_mode" for event in event_service.events)


def test_cli_test_once_prints_simulated_events(data_dir: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LOG_DIR", str(data_dir / "logs"))
    monkeypatch.setenv("TEST_EVENT_DELAY_SECONDS", "0")
    code = main(["--test", "--once"])
    assert code == 0
    output = capsys.readouterr().out
    assert "WorkPulse Desktop Agent" in output
    assert "WINDOWS_LOGIN" in output
    assert "SYSTEM_LOCK" in output
    assert "SYSTEM_UNLOCK" in output
    assert "IDLE_START" in output
    assert "WINDOWS_LOGOUT" in output


def test_agent_test_scenario_uses_service(settings) -> None:
    agent = DesktopAgent(settings)
    agent.run_test_scenario(DEFAULT_SCENARIO)
    assert [event.event_type.value for event in agent.service.events][0] == "WINDOWS_LOGIN"
    assert agent.service.events[-1].event_type is EventType.SYSTEM_RESTART


@pytest.mark.skipif(sys.platform == "win32", reason="Live mode is supported on Windows")
def test_live_mode_requires_windows(data_dir: Path) -> None:
    from app.config import load_settings

    settings = load_settings(
        AGENT_MODE="live",
        DATA_DIR=data_dir,
        LOG_DIR=data_dir / "logs",
    )
    assert run_agent(settings) == 1
