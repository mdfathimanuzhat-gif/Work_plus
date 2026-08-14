"""Load and persist the device secret outside of source control."""

from __future__ import annotations

import logging
import os

from app.config import AgentSettings
from app.device import DeviceIdentity
from app.sync.api_client import AgentApiClient, AgentApiError

logger = logging.getLogger("workpulse.agent.sync.auth")


def load_device_secret(settings: AgentSettings) -> str | None:
    if settings.DEVICE_SECRET:
        return settings.DEVICE_SECRET
    path = settings.device_secret_path
    if not path.is_file():
        return None
    try:
        secret = path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.exception("Failed to read device secret file")
        return None
    return secret or None


def store_device_secret(settings: AgentSettings, secret: str) -> None:
    path = settings.device_secret_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(secret + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.warning("Could not restrict permissions on %s", path)


def ensure_device_token(
    client: AgentApiClient,
    settings: AgentSettings,
    device: DeviceIdentity,
) -> str:
    """Enroll if needed, then exchange the device secret for a device JWT."""
    secret = load_device_secret(settings)
    if secret is None:
        if not settings.AGENT_EMAIL or not settings.AGENT_PASSWORD:
            raise AgentApiError(401, "not_enrolled", "Device is not enrolled and AGENT_EMAIL/AGENT_PASSWORD are not set")
        logger.info("Enrolling device %s", device.device_identifier)
        employee_token = client.login_employee(settings.AGENT_EMAIL, settings.AGENT_PASSWORD)
        secret = client.enroll(
            employee_access_token=employee_token,
            device_identifier=device.device_identifier,
            device_name=device.device_name,
            operating_system=device.operating_system,
        )
        store_device_secret(settings, secret)
    return client.issue_device_token(device.device_identifier, secret)
