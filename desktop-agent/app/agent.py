"""Compose detectors, event recording, SQLite persistence, and the console viewer."""

from __future__ import annotations

import logging
import signal
import sys
import threading
from collections.abc import Sequence

from app.config import AgentSettings
from app.detectors.idle_detector import IdleDetector
from app.detectors.win32_loop import Win32EventLoop, is_windows
from app.device import DeviceIdentity, load_or_create_device_identity
from app.logger import configure_logging
from app.models import EventType
from app.runtime.instance import InstanceLock, InstanceLockError
from app.runtime.status import AgentHealth, collect_health, render_health, write_status_file
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
        self._stop = threading.Event()
        self._heartbeat: threading.Thread | None = None
        try:
            self.repository.cleanup_synced_events(settings.LOCAL_EVENT_RETENTION_DAYS)
        except Exception:
            logger.exception("Synced-event retention cleanup failed")

    def attach_console(self) -> None:
        self.service.add_listener(self._print_event)

    def request_stop(self) -> None:
        self._stop.set()

    def _print_event(self, event: object) -> None:
        from app.models import AgentEvent

        if not isinstance(event, AgentEvent):
            return
        with self._print_lock:
            print(render_event_line(event, SyncStatus.PENDING), flush=True)

    def _record(self, event_type: EventType, metadata: dict | None = None, source: str = "detector") -> object:
        recorded = self.service.record(event_type, metadata=metadata, source=source)
        if recorded is not None:
            logger.info("Event persisted %s %s", event_type.value, recorded.event_id)
        return recorded

    def start_live_detectors(self) -> None:
        self._win32 = Win32EventLoop(self._record, on_session_ending=self._on_windows_session_ending)
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
            logger.info("Synchronization is disabled; events stay in SQLite")
            return
        logger.info("Starting background synchronization")
        self._sync = SyncService(self.settings, self.device, self.repository)
        self._sync.start()

    def run_sync_once(self) -> dict[str, int]:
        logger.info("Sync started (once)")
        service = self._sync or SyncService(self.settings, self.device, self.repository)
        try:
            summary = service.sync_once()
            logger.info("Sync completed %s", summary)
            return summary
        except Exception:
            logger.exception("Sync failed")
            raise
        finally:
            if self._sync is None:
                service.stop()

    def start_heartbeat(self) -> None:
        if self._heartbeat and self._heartbeat.is_alive():
            return
        self._heartbeat = threading.Thread(target=self._heartbeat_loop, name="workpulse-status", daemon=True)
        self._heartbeat.start()

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.settings.STATUS_HEARTBEAT_SECONDS):
            try:
                health = self.health_snapshot(agent_status="RUNNING")
                write_status_file(self.settings.status_file_path, health)
                logger.info(
                    "Status RUNNING device=%s employee=%s backend=%s pending=%s last_event=%s last_sync=%s",
                    health.device_id,
                    health.employee or "-",
                    health.backend,
                    health.pending_events,
                    health.last_event or "-",
                    health.last_successful_sync or "-",
                )
            except Exception:
                logger.exception("Status heartbeat failed")

    def health_snapshot(self, *, agent_status: str) -> AgentHealth:
        backend = "DISABLED"
        authenticated = self.settings.device_secret_path.is_file() or bool(self.settings.DEVICE_SECRET)
        last_sync = None
        if self._sync is not None:
            backend = self._sync.status
            last_sync = self._sync.last_successful_sync
            authenticated = authenticated or backend == "CONNECTED"
        elif self.settings.SYNC_ENABLED and self.settings.api_base_url:
            backend = "OFFLINE"
        return collect_health(
            self.settings,
            agent_status=agent_status,
            backend=backend,
            device=self.device,
            last_successful_sync=last_sync,
            device_authenticated=authenticated,
        )

    def _on_windows_session_ending(self) -> None:
        logger.info("Windows session ending; SQLite persistence has priority over network sync")
        self.service.begin_shutdown()
        self.request_stop()

    def stop(self) -> None:
        logger.info("Agent shutdown starting")
        self.service.begin_shutdown()
        self.request_stop()
        if self._idle:
            self._idle.stop()
        if self._win32:
            self._win32.stop()
        if self._sync:
            logger.info("Stopping synchronization worker without waiting for a full upload")
            self._sync.stop()
        if self._heartbeat:
            self._heartbeat.join(timeout=1)
        try:
            write_status_file(self.settings.status_file_path, self.health_snapshot(agent_status="STOPPED"))
        except Exception:
            logger.exception("Failed to write stopped status file")
        logger.info("Agent shutdown complete")

    def wait(self) -> None:
        self._stop.wait()

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


def print_status(settings: AgentSettings) -> int:
    configure_logging(settings)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    health = collect_health(settings, agent_status="STOPPED")
    lock = settings.instance_lock_path
    try:
        with InstanceLock(lock):
            pass
        health.agent_status = "STOPPED"
    except InstanceLockError:
        health.agent_status = "RUNNING"
    print(render_health(health), flush=True)
    return 0


def run_agent(
    settings: AgentSettings,
    *,
    once: bool = False,
    sequence: Sequence[str] | None = None,
    sync_once: bool = False,
) -> int:
    configure_logging(settings)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Agent startup data_dir=%s sqlite=%s", settings.DATA_DIR, settings.local_database_path)

    lock = InstanceLock(settings.instance_lock_path)
    try:
        lock.acquire()
    except InstanceLockError:
        logger.error("Another WorkPulse agent is already running")
        print("Another WorkPulse agent is already running. Exiting.", file=sys.stderr)
        return 2

    agent = DesktopAgent(settings)
    _install_signal_handlers(agent)
    agent.attach_console()
    agent.print_banner(status="RUNNING")
    print(render_health(agent.health_snapshot(agent_status="RUNNING")), flush=True)

    test_mode = settings.is_test_mode
    try:
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
            agent.start_heartbeat()
        elif not is_windows():
            logger.error("Live mode requires Windows. Use AGENT_MODE=test or python main.py --test")
            print("Live mode requires Windows. Re-run with --test to simulate events.", file=sys.stderr)
            return 1
        else:
            pending = agent.repository.get_event_count(SyncStatus.PENDING)
            logger.info("Startup recovery pending_events=%s", pending)
            agent.start_live_detectors()
            agent.start_sync()
            agent.start_heartbeat()
            if settings.MIX_SIMULATED_AND_REAL:
                logger.warning("MIX_SIMULATED_AND_REAL is enabled; simulated events will also be recorded")
                agent.run_test_scenario(sequence)

        if not test_mode or not once:
            agent.wait()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        agent.stop()
        lock.release()
    return 0


def _install_signal_handlers(agent: DesktopAgent) -> None:
    def _handle(signum: int, _frame: object) -> None:
        logger.info("Received signal %s; beginning graceful shutdown", signum)
        agent.request_stop()

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            logger.debug("Could not install handler for %s", name)
