"""Stored event wrapper. Reuses AgentEvent rather than duplicating fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.models import AgentEvent


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class StoredEvent:
    id: int
    event: AgentEvent
    sync_status: SyncStatus
    sync_attempts: int
    last_sync_attempt: datetime | None
    synced_at: datetime | None
    created_at: datetime
