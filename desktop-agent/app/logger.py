"""Structured rotating logs for the desktop agent.

Event lines are written in a stable, parseable form:

    2026-08-14T09:00:01Z WINDOWS_LOGIN

Diagnostic messages use the same rotating files plus stderr. Passwords and
other secrets must never be passed into these helpers.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import AgentSettings
from app.models import AgentEvent, format_utc

EVENT_LOGGER_NAME = "workpulse.agent.events"
DIAGNOSTIC_LOGGER_NAME = "workpulse.agent"


class EventLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = getattr(record, "event_timestamp", None)
        event_type = getattr(record, "event_type", None)
        if timestamp and event_type:
            return f"{timestamp} {event_type}"
        return super().format(record)


def configure_logging(settings: AgentSettings) -> logging.Logger:
    """Configure rotating file + console loggers. Safe to call more than once."""
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    diagnostic = logging.getLogger(DIAGNOSTIC_LOGGER_NAME)
    events = logging.getLogger(EVENT_LOGGER_NAME)
    if diagnostic.handlers and events.handlers:
        diagnostic.setLevel(settings.LOG_LEVEL)
        events.setLevel(settings.LOG_LEVEL)
        return diagnostic

    diagnostic.setLevel(settings.LOG_LEVEL)
    events.setLevel(settings.LOG_LEVEL)
    diagnostic.propagate = False
    events.propagate = False

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    diagnostic.addHandler(console)

    diagnostic_file = RotatingFileHandler(
        settings.LOG_DIR / "agent.log",
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    diagnostic_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    diagnostic.addHandler(diagnostic_file)

    event_file = RotatingFileHandler(
        settings.events_log_path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    event_file.setFormatter(EventLogFormatter())
    events.addHandler(event_file)
    return diagnostic


def log_event_line(event: AgentEvent) -> None:
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.info(
        "%s %s",
        format_utc(event.event_timestamp),
        event.event_type.value,
        extra={
            "event_timestamp": format_utc(event.event_timestamp),
            "event_type": event.event_type.value,
            "event_id": event.event_id,
        },
    )


def parse_event_log(path: Path) -> list[tuple[str, str]]:
    """Read `TIMESTAMP EVENT_TYPE` lines from the rotating event log."""
    if not path.exists():
        return []
    rows: list[tuple[str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or " " not in line:
            continue
        timestamp, event_type = line.split(" ", 1)
        rows.append((timestamp, event_type.strip()))
    return rows
