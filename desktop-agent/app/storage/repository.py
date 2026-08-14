"""Local attendance-event repository. No network I/O."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models import AgentEvent, EventType, format_utc, utc_now
from app.storage.database import database_connection, initialize_database
from app.storage.models import StoredEvent, SyncStatus

logger = logging.getLogger("workpulse.agent.sqlite.repository")


class DuplicateEventError(Exception):
    """Raised when event_id already exists in the local database."""


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _row_to_stored(row: sqlite3.Row) -> StoredEvent:
    metadata = json.loads(row["metadata"] or "{}")
    operating_system = str(metadata.get("operating_system") or "Windows")
    event = AgentEvent(
        event_id=row["event_id"],
        event_type=EventType(row["event_type"]),
        event_timestamp=_parse_utc(row["event_timestamp"]) or utc_now(),
        device_identifier=row["device_identifier"],
        device_name=row["device_name"],
        operating_system=operating_system,
        username=row["username"],
        metadata=metadata,
    )
    return StoredEvent(
        id=int(row["id"]),
        event=event,
        sync_status=SyncStatus(row["sync_status"]),
        sync_attempts=int(row["sync_attempts"]),
        last_sync_attempt=_parse_utc(row["last_sync_attempt"]),
        synced_at=_parse_utc(row["synced_at"]),
        created_at=_parse_utc(row["created_at"]) or utc_now(),
    )


class EventRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = initialize_database(Path(database_path))

    def save_event(self, event: AgentEvent) -> StoredEvent:
        """Insert a PENDING event. The event_id is unique and never rewritten."""
        metadata = dict(event.metadata)
        metadata.setdefault("operating_system", event.operating_system)
        payload = (
            event.event_id,
            event.event_type.value,
            format_utc(event.event_timestamp),
            event.device_identifier,
            event.device_name,
            event.username,
            json.dumps(metadata, separators=(",", ":")),
            SyncStatus.PENDING.value,
            format_utc(utc_now()),
        )
        try:
            with database_connection(self.database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO attendance_events (
                        event_id, event_type, event_timestamp, device_identifier,
                        device_name, username, metadata, sync_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
        except sqlite3.IntegrityError as exc:
            logger.warning("Duplicate event_id rejected: %s", event.event_id)
            raise DuplicateEventError(event.event_id) from exc
        except sqlite3.Error:
            logger.exception("Failed to save event %s", event.event_id)
            raise
        stored = self.get_event_by_id(event.event_id)
        if stored is None:
            raise RuntimeError(f"Saved event {event.event_id} could not be reloaded")
        logger.info("Persisted %s %s PENDING", event.event_type.value, event.event_id)
        return stored

    def save_events_atomic(self, events: list[AgentEvent]) -> None:
        """Insert several events in one transaction. Rolls back if any insert fails."""
        try:
            with database_connection(self.database_path) as connection:
                for event in events:
                    metadata = dict(event.metadata)
                    metadata.setdefault("operating_system", event.operating_system)
                    connection.execute(
                        """
                        INSERT INTO attendance_events (
                            event_id, event_type, event_timestamp, device_identifier,
                            device_name, username, metadata, sync_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.event_type.value,
                            format_utc(event.event_timestamp),
                            event.device_identifier,
                            event.device_name,
                            event.username,
                            json.dumps(metadata, separators=(",", ":")),
                            SyncStatus.PENDING.value,
                            format_utc(utc_now()),
                        ),
                    )
        except sqlite3.IntegrityError as exc:
            raise DuplicateEventError("atomic insert rolled back") from exc

    def get_event_by_id(self, event_id: str) -> StoredEvent | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM attendance_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return _row_to_stored(row) if row else None

    def get_pending_events(self, limit: int | None = None) -> list[StoredEvent]:
        query = """
            SELECT * FROM attendance_events
            WHERE sync_status = ?
            ORDER BY event_timestamp ASC, id ASC
        """
        params: list[object] = [SyncStatus.PENDING.value]
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        with database_connection(self.database_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_stored(row) for row in rows]

    def list_events(self) -> list[StoredEvent]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM attendance_events ORDER BY event_timestamp ASC, id ASC"
            ).fetchall()
        return [_row_to_stored(row) for row in rows]

    def get_latest_event(self) -> StoredEvent | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM attendance_events ORDER BY event_timestamp DESC, id DESC LIMIT 1"
            ).fetchone()
        return _row_to_stored(row) if row else None

    def get_latest_synced_at(self) -> datetime | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT synced_at FROM attendance_events
                WHERE sync_status = ? AND synced_at IS NOT NULL
                ORDER BY synced_at DESC LIMIT 1
                """,
                (SyncStatus.SYNCED.value,),
            ).fetchone()
        if not row:
            return None
        return _parse_utc(row["synced_at"])

    def get_event_count(self, sync_status: SyncStatus | None = None) -> int:
        with database_connection(self.database_path) as connection:
            if sync_status is None:
                row = connection.execute("SELECT COUNT(*) AS n FROM attendance_events").fetchone()
            else:
                row = connection.execute(
                    "SELECT COUNT(*) AS n FROM attendance_events WHERE sync_status = ?",
                    (sync_status.value,),
                ).fetchone()
        return int(row["n"] if row else 0)

    def mark_event_syncing(self, event_id: str) -> StoredEvent | None:
        now = format_utc(utc_now())
        with database_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE attendance_events
                SET sync_status = ?,
                    sync_attempts = sync_attempts + 1,
                    last_sync_attempt = ?
                WHERE event_id = ?
                """,
                (SyncStatus.SYNCING.value, now, event_id),
            )
        return self.get_event_by_id(event_id)

    def mark_event_synced(self, event_id: str) -> StoredEvent | None:
        now = format_utc(utc_now())
        with database_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE attendance_events
                SET sync_status = ?, synced_at = ?, last_sync_attempt = ?
                WHERE event_id = ?
                """,
                (SyncStatus.SYNCED.value, now, now, event_id),
            )
        return self.get_event_by_id(event_id)

    def mark_event_failed(self, event_id: str) -> StoredEvent | None:
        now = format_utc(utc_now())
        with database_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE attendance_events
                SET sync_status = ?, last_sync_attempt = ?
                WHERE event_id = ?
                """,
                (SyncStatus.FAILED.value, now, event_id),
            )
        return self.get_event_by_id(event_id)

    def mark_events_synced(self, event_ids: list[str]) -> None:
        for event_id in event_ids:
            self.mark_event_synced(event_id)

    def mark_events_failed(self, event_ids: list[str]) -> None:
        for event_id in event_ids:
            self.mark_event_failed(event_id)

    def revert_syncing_to_pending(self, event_ids: list[str] | None = None) -> int:
        """Temporary failures return events to PENDING so they are retried."""
        with database_connection(self.database_path) as connection:
            if event_ids:
                placeholders = ",".join("?" for _ in event_ids)
                cursor = connection.execute(
                    f"""
                    UPDATE attendance_events
                    SET sync_status = ?
                    WHERE sync_status = ? AND event_id IN ({placeholders})
                    """,
                    [SyncStatus.PENDING.value, SyncStatus.SYNCING.value, *event_ids],
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE attendance_events
                    SET sync_status = ?
                    WHERE sync_status = ?
                    """,
                    (SyncStatus.PENDING.value, SyncStatus.SYNCING.value),
                )
            return int(cursor.rowcount or 0)

    def events_eligible_for_cleanup(self, retention_days: int) -> list[StoredEvent]:
        """SYNCED rows older than the retention window. Does not delete them."""
        cutoff = utc_now() - timedelta(days=retention_days)
        cutoff_text = format_utc(cutoff)
        with database_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM attendance_events
                WHERE sync_status = ?
                  AND synced_at IS NOT NULL
                  AND synced_at <= ?
                ORDER BY synced_at ASC
                """,
                (SyncStatus.SYNCED.value, cutoff_text),
            ).fetchall()
        return [_row_to_stored(row) for row in rows]

    def cleanup_synced_events(self, retention_days: int) -> int:
        """Delete SYNCED events older than retention_days. PENDING rows are kept."""
        if retention_days < 1:
            raise ValueError("retention_days must be at least 1")
        cutoff = format_utc(utc_now() - timedelta(days=retention_days))
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM attendance_events
                WHERE sync_status = ?
                  AND synced_at IS NOT NULL
                  AND synced_at <= ?
                """,
                (SyncStatus.SYNCED.value, cutoff),
            )
            deleted = int(cursor.rowcount or 0)
        if deleted:
            logger.info("Removed %s synced events older than %s days", deleted, retention_days)
        return deleted
