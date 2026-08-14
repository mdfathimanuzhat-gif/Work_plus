"""Agent sync client, retry, and offline-to-online behavior."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from app.config import load_settings
from app.device import DeviceIdentity
from app.models import AgentEvent, EventType
from app.storage.models import SyncStatus
from app.storage.repository import EventRepository
from app.sync.api_client import AgentApiClient, AgentApiError
from app.sync.retry import backoff_seconds
from app.sync.sync_service import SyncService


def test_exponential_backoff() -> None:
    assert backoff_seconds(1) == 5
    assert backoff_seconds(2) == 15
    assert backoff_seconds(3) == 30
    assert backoff_seconds(4) == 60
    assert backoff_seconds(8, max_delay=60) == 60
    assert backoff_seconds(2, max_delay=10) == 10


class FakeAPI:
    def __init__(self) -> None:
        self.offline = False
        self.status = 200
        self.payload = {"accepted": 1, "duplicates": 0, "failed": 0, "results": []}
        self.calls: list[str] = []
        self.seen_ids: set[str] = set()

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(f"{request.method} {request.url.path}")
        if self.offline:
            raise httpx.ConnectError("offline", request=request)
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"access_token": "emp-token", "refresh_token": "r", "expires_in": 60})
        if request.url.path.endswith("/devices/enroll"):
            return httpx.Response(200, json={"device_id": str(uuid4()), "device_identifier": "dev-1", "device_secret": "secret"})
        if request.url.path.endswith("/auth/token"):
            if self.status in {401, 403}:
                return httpx.Response(self.status, json={"error": {"code": "unauthorized", "message": "no"}})
            return httpx.Response(200, json={"access_token": "device-token", "expires_in": 60})
        if request.url.path.endswith("/events/batch"):
            if self.status in {500, 503, 429, 401, 403, 409, 422, 400}:
                return httpx.Response(self.status, json={"error": {"code": "server", "message": "fail"}})
            body = request.read()
            import json

            data = json.loads(body)
            results = []
            accepted = duplicates = failed = 0
            for item in data["events"]:
                event_id = item["event_id"]
                if event_id in self.seen_ids:
                    duplicates += 1
                    results.append({"event_id": event_id, "status": "duplicate", "reason": "already_processed"})
                else:
                    self.seen_ids.add(event_id)
                    accepted += 1
                    results.append({"event_id": event_id, "status": "accepted"})
            return httpx.Response(200, json={"accepted": accepted, "duplicates": duplicates, "failed": failed, "results": results})
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "no"}})


@pytest.fixture
def sync_env(settings, device):
    fake = FakeAPI()
    transport = httpx.MockTransport(fake.handler)
    http_client = httpx.Client(transport=transport, base_url="https://workpulse.test")
    sync_settings = load_settings(
        DATA_DIR=settings.DATA_DIR,
        LOG_DIR=settings.LOG_DIR,
        LOCAL_DATABASE_PATH=settings.local_database_path,
        API_BASE_URL="https://workpulse.test",
        ALLOW_INSECURE_HTTP=False,
        SYNC_ENABLED=True,
        SYNC_BATCH_SIZE=2,
        AGENT_EMAIL="agent.user@workpulse.local",
        AGENT_PASSWORD="TestPassw0rd!",
        DEVICE_SECRET="secret",
        AGENT_MODE="test",
    )
    client = AgentApiClient(sync_settings, client=http_client)
    repo = EventRepository(sync_settings.local_database_path)
    service = SyncService(sync_settings, device, repo, client=client, sleeper=lambda _s: None)
    return fake, repo, service, device


def _store(repo: EventRepository, device: DeviceIdentity, event_type: EventType) -> AgentEvent:
    event = AgentEvent.create(
        event_type,
        device_identifier=device.device_identifier,
        device_name=device.device_name,
        operating_system=device.operating_system,
        username=device.username,
        event_timestamp=datetime.now(timezone.utc),
    )
    repo.save_event(event)
    return event


def test_successful_upload_marks_synced(sync_env) -> None:
    fake, repo, service, device = sync_env
    event = _store(repo, device, EventType.WINDOWS_LOGIN)
    summary = service.sync_once()
    assert summary["accepted"] == 1
    stored = repo.get_event_by_id(event.event_id)
    assert stored is not None
    assert stored.sync_status is SyncStatus.SYNCED


def test_network_failure_keeps_pending(sync_env) -> None:
    fake, repo, service, device = sync_env
    event = _store(repo, device, EventType.SYSTEM_LOCK)
    fake.offline = True
    summary = service.sync_once()
    assert summary["pending"] >= 1
    stored = repo.get_event_by_id(event.event_id)
    assert stored is not None
    assert stored.sync_status is SyncStatus.PENDING


def test_server_500_and_503_retry_pending(sync_env) -> None:
    fake, repo, service, device = sync_env
    _store(repo, device, EventType.SYSTEM_UNLOCK)
    fake.status = 500
    with pytest.raises(AgentApiError):
        service.sync_once()
    assert repo.get_event_count(SyncStatus.PENDING) == 1
    fake.status = 503
    with pytest.raises(AgentApiError):
        service.sync_once()
    assert repo.get_event_count(SyncStatus.PENDING) == 1


def test_http_429_retries(sync_env) -> None:
    fake, repo, service, device = sync_env
    _store(repo, device, EventType.IDLE_START)
    fake.status = 429
    with pytest.raises(AgentApiError) as exc:
        service.sync_once()
    assert exc.value.status_code == 429
    assert repo.get_event_count(SyncStatus.PENDING) == 1


def test_timeout_keeps_pending(sync_env) -> None:
    fake, repo, service, device = sync_env
    _store(repo, device, EventType.IDLE_END)

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json={"access_token": "device-token", "expires_in": 60})
        raise httpx.TimeoutException("timeout", request=request)

    service._client._client = httpx.Client(transport=httpx.MockTransport(timeout_handler), base_url="https://workpulse.test")
    with pytest.raises(AgentApiError) as exc:
        service.sync_once()
    assert exc.value.code == "timeout"
    assert repo.get_event_count(SyncStatus.PENDING) == 1


def test_multiple_batches(sync_env) -> None:
    fake, repo, service, device = sync_env
    for event_type in (EventType.WINDOWS_LOGIN, EventType.SYSTEM_LOCK, EventType.SYSTEM_UNLOCK):
        _store(repo, device, event_type)
    summary = service.sync_once()
    assert summary["accepted"] == 3
    assert repo.get_event_count(SyncStatus.PENDING) == 0
    assert repo.get_event_count(SyncStatus.SYNCED) == 3


def test_offline_then_online(sync_env) -> None:
    fake, repo, service, device = sync_env
    _store(repo, device, EventType.WINDOWS_LOGIN)
    fake.offline = True
    service.sync_once()
    assert repo.get_event_count(SyncStatus.PENDING) == 1
    fake.offline = False
    summary = service.sync_once()
    assert summary["accepted"] == 1
    assert repo.get_event_count(SyncStatus.SYNCED) == 1


def test_duplicate_upload_marks_synced(sync_env) -> None:
    fake, repo, service, device = sync_env
    event = _store(repo, device, EventType.SYSTEM_SLEEP)
    fake.seen_ids.add(event.event_id)
    summary = service.sync_once()
    assert summary["duplicates"] == 1
    assert repo.get_event_by_id(event.event_id).sync_status is SyncStatus.SYNCED


def test_auth_failure_does_not_mark_failed(sync_env) -> None:
    fake, repo, service, device = sync_env
    _store(repo, device, EventType.SYSTEM_WAKE)
    fake.status = 401
    summary = service.sync_once()
    assert repo.get_event_count(SyncStatus.PENDING) == 1
    assert repo.get_event_count(SyncStatus.FAILED) == 0
    assert summary["pending"] == 1


def test_http_422_marks_failed(sync_env) -> None:
    fake, repo, service, device = sync_env
    event = _store(repo, device, EventType.SYSTEM_LOCK)
    fake.status = 422
    summary = service.sync_once()
    stored = repo.get_event_by_id(event.event_id)
    assert stored is not None
    assert stored.sync_status is SyncStatus.FAILED
    assert summary["failed"] == 1


def test_http_409_marks_synced(sync_env) -> None:
    fake, repo, service, device = sync_env
    event = _store(repo, device, EventType.SYSTEM_SHUTDOWN)
    fake.status = 409
    summary = service.sync_once()
    stored = repo.get_event_by_id(event.event_id)
    assert stored is not None
    assert stored.sync_status is SyncStatus.SYNCED
    assert summary["duplicates"] == 1


def test_retry_loop_uses_exponential_backoff(sync_env) -> None:
    fake, repo, service, device = sync_env
    _store(repo, device, EventType.SYSTEM_RESTART)
    fake.status = 500
    sleeps: list[float] = []

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        service._stop.set()

    service._sleep = sleeper
    service._run()
    assert sleeps == [5]


def test_insecure_http_rejected_without_flag(settings) -> None:
    from app.config import load_settings

    blocked = load_settings(
        DATA_DIR=settings.DATA_DIR,
        LOG_DIR=settings.LOG_DIR,
        LOCAL_DATABASE_PATH=settings.local_database_path,
        API_BASE_URL="http://127.0.0.1:8000",
        ALLOW_INSECURE_HTTP=False,
    )
    with pytest.raises(ValueError, match="HTTP is only allowed"):
        AgentApiClient(blocked)
