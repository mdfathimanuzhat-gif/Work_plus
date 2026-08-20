"""First-run interactive login prompt."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.config import load_settings
from app.sync.api_client import AgentApiClient, AgentApiError
from app.sync.auth import load_device_secret
from app.sync.enroll_prompt import (
    enroll_with_credentials,
    maybe_interactive_enroll,
    should_prompt_for_login,
)
from main import main


def _live_settings(data_dir: Path, **overrides: object):
    values: dict[str, object] = {
        "DATA_DIR": data_dir,
        "LOG_DIR": data_dir / "logs",
        "LOCAL_DATABASE_PATH": data_dir / "events.db",
        "AGENT_MODE": "live",
        "AGENT_EMAIL": "",
        "AGENT_PASSWORD": "",
        "DEVICE_SECRET": "",
        "API_BASE_URL": "https://workpulse.test",
        "SYNC_ENABLED": True,
    }
    values.update(overrides)
    return load_settings(**values)


def test_prompts_when_no_credentials_and_no_device_secret(data_dir: Path, capsys) -> None:
    settings = _live_settings(data_dir)
    assert should_prompt_for_login(settings) is True

    prompts: list[str] = []
    enrolled: list[tuple[str, str]] = []

    def fake_input(message: str) -> str:
        prompts.append(message)
        return "israh.zunain@workpulse.local"

    def fake_getpass(message: str) -> str:
        prompts.append(message)
        return "secret-password"

    def fake_enroll(_settings, email: str, password: str) -> None:
        enrolled.append((email, password))
        (_settings.DATA_DIR / "device_secret").write_text("persisted-secret\n", encoding="utf-8")

    maybe_interactive_enroll(
        settings,
        input_fn=fake_input,
        getpass_fn=fake_getpass,
        enroll_fn=fake_enroll,
    )
    output = capsys.readouterr().out
    assert "Welcome to WorkPulse. Let's connect this computer to your account." in output
    assert prompts == ["Work email: ", "Password: "]
    assert enrolled == [("israh.zunain@workpulse.local", "secret-password")]
    assert "Connected as israh.zunain@workpulse.local. Tracking has started." in output
    assert load_device_secret(settings) == "persisted-secret"


def test_skips_prompt_when_env_credentials_present(data_dir: Path) -> None:
    settings = _live_settings(
        data_dir,
        AGENT_EMAIL="israh.zunain@workpulse.local",
        AGENT_PASSWORD="TestPassw0rd!",
    )
    assert should_prompt_for_login(settings) is False

    def boom(_message: str) -> str:
        raise AssertionError("interactive prompt should be skipped when .env credentials exist")

    maybe_interactive_enroll(settings, input_fn=boom, getpass_fn=boom, enroll_fn=lambda *_a: None)


def test_skips_prompt_when_device_secret_exists(data_dir: Path) -> None:
    settings = _live_settings(data_dir)
    settings.device_secret_path.write_text("existing-secret\n", encoding="utf-8")
    assert should_prompt_for_login(settings) is False

    def boom(_message: str) -> str:
        raise AssertionError("interactive prompt should be skipped once the device is enrolled")

    maybe_interactive_enroll(settings, input_fn=boom, getpass_fn=boom, enroll_fn=lambda *_a: None)


def test_does_not_prompt_again_after_successful_enroll(data_dir: Path) -> None:
    settings = _live_settings(data_dir)

    def enroll(_settings, _email: str, _password: str) -> None:
        _settings.device_secret_path.write_text("device-secret\n", encoding="utf-8")

    maybe_interactive_enroll(
        settings,
        input_fn=lambda _m: "user@workpulse.local",
        getpass_fn=lambda _m: "pw",
        enroll_fn=enroll,
    )
    assert settings.device_secret_path.is_file()

    def boom(_message: str) -> str:
        raise AssertionError("enrolled agents must not prompt on later runs")

    maybe_interactive_enroll(settings, input_fn=boom, getpass_fn=boom, enroll_fn=lambda *_a: None)


def test_cli_test_and_status_skip_prompt(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LOG_DIR", str(data_dir / "logs"))
    monkeypatch.setenv("LOCAL_DATABASE_PATH", str(data_dir / "events.db"))
    monkeypatch.setenv("TEST_EVENT_DELAY_SECONDS", "0")
    monkeypatch.setenv("AGENT_EMAIL", "")
    monkeypatch.setenv("AGENT_PASSWORD", "")
    monkeypatch.setenv("DEVICE_SECRET", "")
    monkeypatch.setenv("AGENT_MODE", "live")

    def boom(_message: str) -> str:
        raise AssertionError("CLI --test/--status must not prompt")

    monkeypatch.setattr("builtins.input", boom)
    monkeypatch.setattr("getpass.getpass", boom)
    assert main(["--test", "--once"]) == 0
    assert main(["--status"]) == 0


def test_main_prompts_on_live_start_without_credentials(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LOG_DIR", str(data_dir / "logs"))
    monkeypatch.setenv("LOCAL_DATABASE_PATH", str(data_dir / "events.db"))
    monkeypatch.setenv("AGENT_EMAIL", "")
    monkeypatch.setenv("AGENT_PASSWORD", "")
    monkeypatch.setenv("DEVICE_SECRET", "")
    monkeypatch.setenv("AGENT_MODE", "live")
    monkeypatch.setenv("API_BASE_URL", "https://workpulse.test")

    monkeypatch.setattr("builtins.input", lambda _m: "israh.zunain@workpulse.local")
    monkeypatch.setattr("getpass.getpass", lambda _m: "pw")

    def fake_enroll(settings, email: str, password: str) -> None:
        settings.device_secret_path.parent.mkdir(parents=True, exist_ok=True)
        settings.device_secret_path.write_text("secret\n", encoding="utf-8")
        settings.AGENT_EMAIL = email

    monkeypatch.setattr("app.sync.enroll_prompt.enroll_with_credentials", fake_enroll)
    monkeypatch.setattr("main.run_agent", lambda *_a, **_k: 0)

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "Welcome to WorkPulse. Let's connect this computer to your account." in output
    assert "Connected as israh.zunain@workpulse.local. Tracking has started." in output


def test_failed_login_exits_nonzero_without_traceback(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("LOG_DIR", str(data_dir / "logs"))
    monkeypatch.setenv("LOCAL_DATABASE_PATH", str(data_dir / "events.db"))
    monkeypatch.setenv("AGENT_EMAIL", "")
    monkeypatch.setenv("AGENT_PASSWORD", "")
    monkeypatch.setenv("DEVICE_SECRET", "")
    monkeypatch.setenv("AGENT_MODE", "live")
    monkeypatch.setenv("API_BASE_URL", "https://workpulse.test")

    monkeypatch.setattr("builtins.input", lambda _m: "bad@workpulse.local")
    monkeypatch.setattr("getpass.getpass", lambda _m: "nope")

    def fail(_settings, _email: str, _password: str) -> None:
        raise AgentApiError(401, "unauthorized", "Invalid credentials")

    monkeypatch.setattr("app.sync.enroll_prompt.enroll_with_credentials", fail)
    monkeypatch.setattr("main.run_agent", lambda *_a, **_k: 0)

    assert main([]) == 1
    captured = capsys.readouterr()
    assert "Could not sign in. Check your email and password." in captured.err
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out


def test_enroll_with_credentials_uses_existing_auth_flow(data_dir: Path) -> None:
    settings = _live_settings(data_dir)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "emp-token", "refresh_token": "r", "expires_in": 60})
        if request.url.path.endswith("/devices/enroll"):
            return httpx.Response(
                200,
                json={
                    "device_id": str(uuid4()),
                    "device_identifier": "dev-1",
                    "device_secret": "enrolled-secret",
                },
            )
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json={"access_token": "device-token", "expires_in": 60})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://workpulse.test")
    api = AgentApiClient(settings, client=http_client)

    maybe_interactive_enroll(
        settings,
        input_fn=lambda _m: "israh.zunain@workpulse.local",
        getpass_fn=lambda _m: "TestPassw0rd!",
        enroll_fn=lambda s, e, p: enroll_with_credentials(s, e, p, client=api),
    )
    assert load_device_secret(settings) == "enrolled-secret"
    assert should_prompt_for_login(settings) is False
