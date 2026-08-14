"""Stable local device identity.

The identifier is a random UUID stored on disk so it survives application
restarts. It is not derived from a MAC address, password, or other sensitive
personal data. On Windows, the hostname and session username are recorded as
non-secret machine labels only.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import AgentSettings


@dataclass(frozen=True)
class DeviceIdentity:
    device_identifier: str
    device_name: str
    operating_system: str
    username: str


def _session_username() -> str:
    for candidate in (os.environ.get("USERNAME"), os.environ.get("USER"), os.environ.get("LOGNAME")):
        if candidate:
            return candidate
    try:
        return os.getlogin()
    except OSError:
        return "unknown"


def _read_stored_identifier(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    identifier = payload.get("device_identifier")
    if isinstance(identifier, str) and identifier.strip():
        return identifier.strip()
    return None


def _write_stored_identifier(path: Path, identifier: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "device_identifier": identifier,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_or_create_device_identity(settings: AgentSettings) -> DeviceIdentity:
    """Return a stable device identity, creating and persisting one if needed."""
    path = settings.device_identity_path
    identifier = _read_stored_identifier(path)
    if identifier is None:
        identifier = str(uuid.uuid4())
        _write_stored_identifier(path, identifier)
    os_name = "Windows" if platform.system().lower().startswith("win") else platform.system()
    return DeviceIdentity(
        device_identifier=identifier,
        device_name=socket.gethostname() or "unknown-device",
        operating_system=os_name,
        username=_session_username(),
    )
