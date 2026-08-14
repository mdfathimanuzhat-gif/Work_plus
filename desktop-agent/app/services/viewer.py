"""Console event viewer for local development."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.device import DeviceIdentity
from app.models import AgentEvent
from app.storage.models import StoredEvent, SyncStatus


def format_clock(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%H:%M:%S")


def render_banner(
    device: DeviceIdentity,
    *,
    status: str,
    mode: str,
    database_path: Path | None = None,
    total_events: int | None = None,
    pending_events: int | None = None,
) -> str:
    lines = [
        "WorkPulse Desktop Agent",
        f"Status: {status}",
        "",
        f"Device: {device.device_name}",
        f"Mode: {mode}",
        f"OS: {device.operating_system}",
        f"User: {device.username}",
        f"Device ID: {device.device_identifier}",
    ]
    if database_path is not None:
        lines.extend(["", "Local Database:", str(database_path)])
    return "\n".join(lines)


def render_event_line(event: AgentEvent, sync_status: SyncStatus | str = SyncStatus.PENDING) -> str:
    status = sync_status.value if isinstance(sync_status, SyncStatus) else sync_status
    return f"[{format_clock(event.event_timestamp)}] {event.event_type.value:<16} {status}"


def render_stored_event_line(stored: StoredEvent) -> str:
    return render_event_line(stored.event, stored.sync_status)


def render_event_summary(*, total_events: int, pending_events: int) -> str:
    return f"Total events: {total_events}\nPending sync: {pending_events}"


def render_log_line(timestamp: str, event_type: str) -> str:
    try:
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        clock = format_clock(moment)
    except ValueError:
        clock = timestamp
    return f"[{clock}] {event_type}"
