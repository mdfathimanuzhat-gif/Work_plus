"""Local SQLite connection helpers.

The database is an offline queue. Nothing here talks to the network.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.storage.migrations import apply_migrations

logger = logging.getLogger("workpulse.agent.sqlite")

BUSY_TIMEOUT_MS = 5000


class DatabaseError(Exception):
    """Raised when the local database cannot be opened or initialized."""


def restrict_path_to_owner(path: Path) -> None:
    """Best-effort: owner-only access. Never required for the agent to run."""
    try:
        if sys.platform == "win32":
            _restrict_windows_acl(path)
            return
        mode = stat.S_IRUSR | stat.S_IWUSR
        if path.is_dir():
            mode |= stat.S_IXUSR
        os.chmod(path, mode)
    except OSError:
        logger.warning("Could not restrict permissions on %s", path)


def _restrict_windows_acl(path: Path) -> None:
    """Grant the current user modify access and remove inherited Everyone ACEs."""
    try:
        import subprocess

        user = os.environ.get("USERNAME") or os.getlogin()
        subprocess.run(
            ["icacls", str(path), "/inheritance:d", "/grant:r", f"{user}:(M)"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        logger.warning("Could not set Windows ACL on %s", path, exc_info=True)


def connect(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL and a busy timeout."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    restrict_path_to_owner(path.parent)
    connection = sqlite3.connect(str(path), timeout=BUSY_TIMEOUT_MS / 1000, isolation_level="DEFERRED")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=NORMAL")
    return connection


def initialize_database(path: Path) -> Path:
    """Create the directory, database, and tables; verify the file is writable."""
    try:
        connection = connect(path)
        try:
            apply_migrations(connection)
            connection.execute("SELECT COUNT(*) FROM attendance_events")
            connection.execute("UPDATE schema_version SET version = version")
            connection.commit()
        finally:
            connection.close()
        restrict_path_to_owner(path)
        logger.info("Local event database ready at %s", path)
        return path
    except sqlite3.Error as exc:
        raise DatabaseError(f"Failed to initialize local database at {path}") from exc


@contextmanager
def database_connection(path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
