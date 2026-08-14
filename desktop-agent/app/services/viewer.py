"""Console event viewer for local development."""

from __future__ import annotations

from datetime import datetime, timezone

from app.device import DeviceIdentity
from app.models import AgentEvent


def format_clock(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%H:%M:%S")


def render_banner(device: DeviceIdentity, *, status: str, mode: str) -> str:
    return (
        "WorkPulse Desktop Agent\n"
        f"Device: {device.device_name}\n"
        f"Status: {status}\n"
        f"Mode: {mode}\n"
        f"OS: {device.operating_system}\n"
        f"User: {device.username}\n"
        f"Device ID: {device.device_identifier}"
    )


def render_event_line(event: AgentEvent) -> str:
    return f"[{format_clock(event.event_timestamp)}] {event.event_type.value}"


def render_log_line(timestamp: str, event_type: str) -> str:
    try:
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        clock = format_clock(moment)
    except ValueError:
        clock = timestamp
    return f"[{clock}] {event_type}"
