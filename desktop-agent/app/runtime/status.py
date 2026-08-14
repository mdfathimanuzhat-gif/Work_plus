"""Local health snapshot. Never includes passwords, secrets, or tokens."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import AgentSettings
from app.device import DeviceIdentity, load_or_create_device_identity
from app.storage.database import DatabaseError, initialize_database
from app.storage.models import SyncStatus
from app.storage.repository import EventRepository
from app.sync.api_client import AgentApiClient

logger = logging.getLogger("workpulse.agent.runtime")


@dataclass
class AgentHealth:
    agent_status: str
    device_id: str
    device_name: str
    employee: str
    backend: str
    sqlite_available: bool
    device_authenticated: bool
    pending_events: int
    last_event: str
    last_successful_sync: str
    database_path: str
    log_dir: str


def _utc_text(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collect_health(
    settings: AgentSettings,
    *,
    agent_status: str = "STOPPED",
    backend: str | None = None,
    device: DeviceIdentity | None = None,
    last_successful_sync: datetime | None = None,
    device_authenticated: bool | None = None,
) -> AgentHealth:
    identity = device or load_or_create_device_identity(settings)
    sqlite_ok = True
    pending = 0
    last_event = ""
    last_sync = _utc_text(last_successful_sync)
    try:
        initialize_database(settings.local_database_path)
        repo = EventRepository(settings.local_database_path)
        pending = repo.get_event_count(SyncStatus.PENDING)
        latest = repo.get_latest_event()
        if latest is not None:
            last_event = f"{_utc_text(latest.event.event_timestamp)} {latest.event.event_type.value}"
        if last_successful_sync is None:
            last_sync = _utc_text(repo.get_latest_synced_at())
    except (DatabaseError, OSError):
        sqlite_ok = False
        logger.exception("SQLite health check failed")

    reachable = backend
    if reachable is None:
        reachable = "DISABLED"
        if settings.api_base_url:
            try:
                client = AgentApiClient(settings)
                reachable = "CONNECTED" if client.ping() else "OFFLINE"
                client.close()
            except Exception:
                reachable = "OFFLINE"

    authenticated = device_authenticated
    if authenticated is None:
        authenticated = settings.device_secret_path.is_file() or bool(settings.DEVICE_SECRET)

    employee = settings.AGENT_EMAIL or ""
    log_dir = str(settings.LOG_DIR) if settings.LOG_DIR is not None else ""
    return AgentHealth(
        agent_status=agent_status,
        device_id=identity.device_identifier,
        device_name=identity.device_name,
        employee=employee,
        backend=reachable,
        sqlite_available=sqlite_ok,
        device_authenticated=bool(authenticated),
        pending_events=pending,
        last_event=last_event,
        last_successful_sync=last_sync,
        database_path=str(settings.local_database_path),
        log_dir=log_dir,
    )


def render_health(health: AgentHealth) -> str:
    return "\n".join(
        [
            "WorkPulse Desktop Agent",
            f"Agent status: {health.agent_status}",
            f"Device ID: {health.device_id}",
            f"Device: {health.device_name}",
            f"Employee: {health.employee or '(not set)'}",
            f"Backend: {health.backend}",
            f"SQLite available: {health.sqlite_available}",
            f"Device authenticated: {health.device_authenticated}",
            f"Pending events: {health.pending_events}",
            f"Last event: {health.last_event or '(none)'}",
            f"Last successful sync: {health.last_successful_sync or '(none)'}",
            f"SQLite: {health.database_path}",
            f"Logs: {health.log_dir}",
        ]
    )


def write_status_file(path: Path, health: AgentHealth) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent_status": health.agent_status,
        "device_id": health.device_id,
        "device_name": health.device_name,
        "employee": health.employee,
        "backend": health.backend,
        "sqlite_available": health.sqlite_available,
        "device_authenticated": health.device_authenticated,
        "pending_events": health.pending_events,
        "last_event": health.last_event,
        "last_successful_sync": health.last_successful_sync,
        "database_path": health.database_path,
        "log_dir": health.log_dir,
        "written_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
