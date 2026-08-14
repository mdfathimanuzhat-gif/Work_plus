"""SQLite schema for the local attendance-event queue."""

from __future__ import annotations

SCHEMA_VERSION = 1

CREATE_ATTENDANCE_EVENTS = """
CREATE TABLE IF NOT EXISTS attendance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    device_identifier TEXT NOT NULL,
    device_name TEXT NOT NULL,
    username TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    sync_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (sync_status IN ('PENDING', 'SYNCING', 'SYNCED', 'FAILED')),
    sync_attempts INTEGER NOT NULL DEFAULT 0,
    last_sync_attempt TEXT,
    synced_at TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_attendance_events_sync_status ON attendance_events (sync_status)",
    "CREATE INDEX IF NOT EXISTS ix_attendance_events_event_timestamp ON attendance_events (event_timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_attendance_events_created_at ON attendance_events (created_at)",
)

CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
)
"""


def apply_migrations(connection) -> None:
    """Create tables and indexes if they do not exist."""
    connection.execute(CREATE_SCHEMA_VERSION)
    connection.execute(CREATE_ATTENDANCE_EVENTS)
    for statement in CREATE_INDEXES:
        connection.execute(statement)
    row = connection.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        connection.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    elif int(row[0]) < SCHEMA_VERSION:
        connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
