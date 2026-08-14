"""Compose detectors, event recording, SQLite persistence, and the console viewer."""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Sequence

from app.config import AgentSettings
from app.detectors.idle_detector import IdleDetector
from app.detectors.win32_loop import Win32EventLoop, is_windows
from app.device import DeviceIdentity, load_or_create_device_identity
from app.logger import configure_logging
from app.models import EventType
from app.services.event_service import EventService
from app.services.simulator import DEFAULT_SCENARIO, simulate_events
from app.services.viewer import (
    render_banner,
    render_event_line,
    render_event_summary,
    render_stored_event_line,
)
from app.storage.models import SyncStatus
from app.storage.repository import EventRepository
from app.sync.sync_service import SyncService

logger = logging.getLogger("workpulse.agent")


class DesktopAgent:
    def __init__(self, settings: AgentSettings, device: DeviceIdentity | None = None) -> None:
        self.settings = settings
        self.device = device or load_or_create_device_identity(settings)
        self.repository = EventRepository(settings.local_database_path)
        self.service = EventService(self.device, repository=self.repository)
        self._idle: IdleDetector | None = None
        self._win32: Win32EventLoop | None = None
        self._sync: SyncService | None = None
        self._print_lock = threading.Lock()
        try:
            self.repository.cleanup_synced_events(settings.LOCAL_EVENT_RETENTION_DAYS)
        except Exception:
            logger.exception("Synced-event retention cleanup failed")

    def attach_console(self) -> None:
        self.service.add_listener(self._print_event)

    def _print_event(self, event: object) -> None:
        from app.models import AgentEvent

        if not isinstance(event, AgentEvent):
            return
        with self._print_lock:
            print(render_event_line(event, SyncStatus.PENDING), flush=True)

    def _record(self, event_type: EventType, metadata: dict | None = None, source: str = "detector") -> object:
        return self.service.record(event_type, metadata=metadata, source=source)

    def start_live_detectors(self) -> None:
        self._win32 = Win32EventLoop(self._record)
        self._win32.start()
        self._idle = IdleDetector(
            threshold_seconds=self.settings.IDLE_THRESHOLD_SECONDS,
            poll_interval_seconds=self.settings.IDLE_POLL_INTERVAL_SECONDS,
            record=self._record,
            is_locked=lambda: self.service.state.locked,
        )
        if is_windows():
            self._idle.start()
        else:
            logger.warning("Idle detector requires Windows GetLastInputInfo; live idle capture is disabled")

    def start_sync(self) -> None:
        if not self.settings.SYNC_ENABLED or not self.settings.api_base_url:
            return
        self._sync = SyncService(self.settings, self.device, self.repository)
        self._sync.start()

    def run_sync_once(self) -> dict[str, int]:
        service = self._sync or SyncService(self.settings, self.device, self.repository)
        try:
            return service.sync_once()
        finally:
            if self._sync is None:
                service.stop()

    def stop(self) -> None:
        if self._idle:
            self._idle.stop()
        if self._win32:
            self._win32.stop()
        if self._sync:
            self._sync.stop()

    def run_test_scenario(self, sequence: Sequence[str] | None = None) -> None:
        simulate_events(
            self._record,
            sequence if sequence is not None else DEFAULT_SCENARIO,
            delay_seconds=self.settings.TEST_EVENT_DELAY_SECONDS,
        )

    def print_banner(self, *, status: str) -> None:
        print(
            render_banner(
                self.device,
                status=status,
                mode=self.settings.AGENT_MODE.upper(),
                database_path=self.settings.local_database_path,
            ),
            flush=True,
        )
        print(flush=True)

    def print_database_view(self) -> None:
        stored = self.repository.list_events()
        print("Events:", flush=True)
        for item in stored:
            print(render_stored_event_line(item), flush=True)
        print(flush=True)
        print(
            render_event_summary(
                total_events=self.repository.get_event_count(),
                pending_events=self.repository.get_event_count(SyncStatus.PENDING),
            ),
            flush=True,
        )


def run_agent(
    settings: AgentSettings,
    *,
    once: bool = False,
    sequence: Sequence[str] | None = None,
    sync_once: bool = False,
) -> int:
    configure_logging(settings)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    agent = DesktopAgent(settings)
    agent.attach_console()
    agent.print_banner(status="RUNNING")

    test_mode = settings.is_test_mode
    if test_mode:
        logger.info("Test mode: emitting simulated events only")
        agent.run_test_scenario(sequence)
        print(flush=True)
        agent.print_database_view()
        if sync_once or (once and settings.SYNC_ENABLED):
            try:
                summary = agent.run_sync_once()
                print(f"\nSync status: {summary}", flush=True)
                agent.print_database_view()
            except Exception:
                logger.exception("Sync-once failed")
        if once:
            print(flush=True)
            agent.print_banner(status="STOPPED")
            agent.stop()
            return 0
        agent.start_sync()
    elif not is_windows():
        logger.error("Live mode requires Windows. Use AGENT_MODE=test or python main.py --test")
        print("Live mode requires Windows. Re-run with --test to simulate events.", file=sys.stderr)
        return 1
    else:
        agent.start_live_detectors()
        agent.start_sync()
        if settings.MIX_SIMULATED_AND_REAL:
            logger.warning("MIX_SIMULATED_AND_REAL is enabled; simulated events will also be recorded")
            agent.run_test_scenario(sequence)

    try:
        if not test_mode or not once:
            _wait_until_interrupted()
    except KeyboardInterrupt:
        logger.info("Stopping desktop agent")
    finally:
        agent.stop()
    return 0


def _wait_until_interrupted() -> None:
    stop = threading.Event()
    stop.wait()
