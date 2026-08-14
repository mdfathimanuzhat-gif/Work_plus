"""Background upload of PENDING SQLite events to FastAPI."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from app.config import AgentSettings
from app.device import DeviceIdentity
from app.storage.models import SyncStatus
from app.storage.repository import EventRepository
from app.sync.api_client import AgentApiClient, AgentApiError
from app.sync.auth import ensure_device_token
from app.sync.retry import backoff_seconds

logger = logging.getLogger("workpulse.agent.sync")


class SyncService:
    def __init__(
        self,
        settings: AgentSettings,
        device: DeviceIdentity,
        repository: EventRepository,
        *,
        client: AgentApiClient | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._settings = settings
        self._device = device
        self._repository = repository
        self._client = client
        self._owns_client = client is None
        self._sleep = sleeper or time.sleep
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._failure_attempt = 0
        self._auth_blocked = False
        self.status = "OFFLINE"

    def start(self) -> None:
        self._repository.revert_syncing_to_pending()
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="workpulse-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._owns_client and self._client is not None:
            self._client.close()

    def sync_once(self) -> dict[str, int]:
        """Upload pending batches until empty or a retryable failure. Used by tests and --sync-once."""
        totals = {"accepted": 0, "duplicates": 0, "failed": 0, "pending": 0}
        if not self._ensure_client():
            self.status = "OFFLINE"
            totals["pending"] = self._repository.get_event_count(SyncStatus.PENDING)
            return totals
        try:
            ensure_device_token(self._client, self._settings, self._device)
            self._auth_blocked = False
        except AgentApiError as exc:
            self._handle_auth_error(exc)
            totals["pending"] = self._repository.get_event_count(SyncStatus.PENDING)
            return totals
        while not self._stop.is_set():
            pending = self._repository.get_pending_events(limit=self._settings.SYNC_BATCH_SIZE)
            totals["pending"] = self._repository.get_event_count(SyncStatus.PENDING)
            if not pending:
                self.status = "CONNECTED"
                logger.info("Pending events: 0; Sync status: CONNECTED")
                return totals
            logger.info("Pending events: %s; Sync status: CONNECTED; Uploading: %s", totals["pending"], len(pending))
            ids = [item.event.event_id for item in pending]
            for event_id in ids:
                self._repository.mark_event_syncing(event_id)
            try:
                response = self._client.upload_batch(self._device.device_identifier, [item.event for item in pending])
            except AgentApiError as exc:
                if exc.status_code == 409:
                    self._repository.mark_events_synced(ids)
                    totals["duplicates"] += len(ids)
                    self._failure_attempt = 0
                    continue
                self._repository.revert_syncing_to_pending(ids)
                if exc.status_code in {401, 403}:
                    self._handle_auth_error(exc)
                    return totals
                if exc.status_code in {400, 422}:
                    logger.error("Batch rejected (%s): %s", exc.code, exc.message)
                    self._repository.mark_events_failed(ids)
                    totals["failed"] += len(ids)
                    return totals
                self._failure_attempt += 1
                logger.warning("Temporary sync failure %s %s; will retry", exc.status_code, exc.code)
                raise
            self._apply_results(response)
            totals["accepted"] += int(response.get("accepted") or 0)
            totals["duplicates"] += int(response.get("duplicates") or 0)
            totals["failed"] += int(response.get("failed") or 0)
            logger.info(
                "Accepted: %s Duplicates: %s Failed: %s",
                response.get("accepted"),
                response.get("duplicates"),
                response.get("failed"),
            )
            self._failure_attempt = 0
            if len(pending) < self._settings.SYNC_BATCH_SIZE:
                totals["pending"] = self._repository.get_event_count(SyncStatus.PENDING)
                self.status = "CONNECTED"
                return totals
        totals["pending"] = self._repository.get_event_count(SyncStatus.PENDING)
        return totals

    def _apply_results(self, response: dict) -> None:
        for row in response.get("results") or []:
            event_id = str(row.get("event_id", ""))
            status = row.get("status")
            if not event_id:
                continue
            if status in {"accepted", "duplicate"}:
                self._repository.mark_event_synced(event_id)
            elif status == "failed":
                self._repository.mark_event_failed(event_id)
                logger.error("Event %s marked FAILED: %s", event_id, row.get("reason"))
            else:
                self._repository.revert_syncing_to_pending([event_id])

    def _ensure_client(self) -> bool:
        if self._client is None:
            try:
                self._client = AgentApiClient(self._settings)
            except ValueError:
                logger.warning("Sync client is not configured")
                return False
        if not self._client.ping():
            self.status = "OFFLINE"
            logger.info(
                "Pending events: %s; Sync status: OFFLINE",
                self._repository.get_event_count(SyncStatus.PENDING),
            )
            return False
        self.status = "CONNECTED"
        return True

    def _handle_auth_error(self, exc: AgentApiError) -> None:
        self._auth_blocked = True
        self.status = "AUTH_ERROR"
        logger.error("Device authentication failed (%s). Not retrying rapidly. %s", exc.code, exc.message)

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._auth_blocked:
                self._sleep(max(self._settings.SYNC_MAX_BACKOFF_SECONDS, 60))
                self._auth_blocked = False
                continue
            try:
                self.sync_once()
                if self.status == "OFFLINE":
                    self._failure_attempt += 1
                    delay = backoff_seconds(self._failure_attempt, max_delay=self._settings.SYNC_MAX_BACKOFF_SECONDS)
                    logger.info("API unreachable; retrying sync in %s seconds", delay)
                    self._sleep(delay)
                else:
                    self._sleep(self._settings.SYNC_INTERVAL_SECONDS)
            except AgentApiError:
                delay = backoff_seconds(self._failure_attempt, max_delay=self._settings.SYNC_MAX_BACKOFF_SECONDS)
                logger.info("Retrying sync in %s seconds", delay)
                self._sleep(delay)
            except Exception:
                logger.exception("Sync loop failed")
                delay = backoff_seconds(max(self._failure_attempt, 1), max_delay=self._settings.SYNC_MAX_BACKOFF_SECONDS)
                self._sleep(delay)
