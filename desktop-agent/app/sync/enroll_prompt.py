"""First-run interactive login for machines that are not enrolled yet."""

from __future__ import annotations

import getpass
import logging
from collections.abc import Callable

from app.config import AgentSettings
from app.device import load_or_create_device_identity
from app.sync.api_client import AgentApiClient, AgentApiError
from app.sync.auth import ensure_device_token, load_device_secret

logger = logging.getLogger("workpulse.agent.sync.enroll")

WELCOME_MESSAGE = "Welcome to WorkPulse. Let's connect this computer to your account."
SUCCESS_MESSAGE = "Connected as {email}. Tracking has started."


class InteractiveEnrollError(Exception):
    """User-facing enrollment failure; callers should print the message and exit."""


def has_env_credentials(settings: AgentSettings) -> bool:
    return bool(settings.AGENT_EMAIL and settings.AGENT_PASSWORD)


def should_prompt_for_login(settings: AgentSettings) -> bool:
    """Prompt only on first live run when nothing can enroll this device yet."""
    if settings.is_test_mode:
        return False
    if load_device_secret(settings):
        return False
    if has_env_credentials(settings):
        return False
    return True


def format_enroll_error(exc: BaseException) -> str:
    if isinstance(exc, AgentApiError):
        if exc.status_code in {401, 403}:
            return "Could not sign in. Check your email and password."
        if exc.status_code == 0 or exc.code in {"timeout", "network_error"}:
            return "Could not reach the WorkPulse server. Check your network connection and API_BASE_URL."
        return f"Could not connect this computer: {exc.message}"
    if isinstance(exc, ValueError):
        return str(exc)
    return "Could not connect this computer. Please try again."


def enroll_with_credentials(
    settings: AgentSettings,
    email: str,
    password: str,
    *,
    client: AgentApiClient | None = None,
) -> None:
    """Login and enroll using the same path as AGENT_EMAIL/AGENT_PASSWORD from .env."""
    settings.AGENT_EMAIL = email
    settings.AGENT_PASSWORD = password
    owns_client = client is None
    api = client or AgentApiClient(settings)
    try:
        device = load_or_create_device_identity(settings)
        ensure_device_token(api, settings, device)
    finally:
        if owns_client:
            api.close()
        settings.AGENT_PASSWORD = None


def maybe_interactive_enroll(
    settings: AgentSettings,
    *,
    input_fn: Callable[[str], str] | None = None,
    getpass_fn: Callable[[str], str] | None = None,
    enroll_fn: Callable[[AgentSettings, str, str], None] | None = None,
) -> AgentSettings:
    if not should_prompt_for_login(settings):
        return settings

    read_line = input_fn or input
    read_password = getpass_fn or getpass.getpass
    enroll = enroll_fn or enroll_with_credentials

    print(WELCOME_MESSAGE, flush=True)
    try:
        email = read_line("Work email: ").strip()
        password = read_password("Password: ")
    except EOFError as exc:
        raise InteractiveEnrollError(
            "Interactive login is required on first run. "
            "Enter your work email and password, or set AGENT_EMAIL and AGENT_PASSWORD."
        ) from exc

    if not email or not password:
        raise InteractiveEnrollError("Email and password are required.")

    try:
        enroll(settings, email, password)
    except InteractiveEnrollError:
        raise
    except (AgentApiError, ValueError, OSError) as exc:
        logger.debug("Interactive enrollment failed", exc_info=True)
        raise InteractiveEnrollError(format_enroll_error(exc)) from None

    print(SUCCESS_MESSAGE.format(email=email), flush=True)
    return settings
