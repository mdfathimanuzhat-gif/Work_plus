"""Windows message loop for session and power notifications.

Creates a message-only window, registers for WTS session change notifications,
and dispatches WM_WTSSESSION_CHANGE, WM_POWERBROADCAST, and WM_ENDSESSION.

This process is not installed as a Windows service in this phase. It is designed
so a future service wrapper can host the same loop.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from typing import Any

from app.detectors.power_detector import (
    WM_ENDSESSION,
    WM_POWERBROADCAST,
    WM_QUERYENDSESSION,
    end_session_metadata,
    map_end_session,
    map_power_broadcast,
)
from app.detectors.session_detector import (
    NOTIFY_FOR_THIS_SESSION,
    WM_WTSSESSION_CHANGE,
    map_session_notification,
)
from app.models import EventType

logger = logging.getLogger("workpulse.agent.win32")

RecordFn = Callable[..., object]


def is_windows() -> bool:
    return sys.platform == "win32"


class Win32EventLoop:
    """Background Win32 message pump. No-op to construct on non-Windows."""

    def __init__(self, record: RecordFn, *, on_session_ending: Callable[[], None] | None = None) -> None:
        self._record = record
        self._on_session_ending = on_session_ending
        self._thread: threading.Thread | None = None
        self._hwnd = None
        self._stop = threading.Event()

    def start(self) -> None:
        if not is_windows():
            logger.warning("Win32 session/power loop is unavailable on %s", sys.platform)
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="workpulse-win32", daemon=False)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if not is_windows() or self._hwnd is None:
            return
        try:
            import win32con
            import win32gui

            win32gui.PostMessage(self._hwnd, win32con.WM_QUIT, 0, 0)
        except Exception:
            logger.exception("Failed to stop Win32 message loop")
        if self._thread:
            self._thread.join(timeout=5)

    def handle_message(self, msg: int, wparam: int, lparam: int) -> None:
        """Dispatch a single window message. Used by the pump and by tests."""
        try:
            if msg == WM_WTSSESSION_CHANGE:
                event_type = map_session_notification(wparam)
                if event_type is not None:
                    self._safe_record(event_type, wparam=wparam, source="session")
                return
            if msg == WM_POWERBROADCAST:
                event_type = map_power_broadcast(wparam)
                if event_type is not None:
                    self._safe_record(event_type, wparam=wparam, source="power")
                return
            if msg == WM_ENDSESSION:
                # Map only from this WM_ENDSESSION. wParam=TRUE, lParam=0 is
                # SYSTEM_SHUTDOWN. Do not pass restart heuristics; they override
                # the message and mis-label shutdown as restart.
                event_type = map_end_session(wparam, lparam)
                if event_type is not None:
                    metadata = end_session_metadata(wparam, lparam)
                    self._safe_record(event_type, source="end_session", **metadata)
                if wparam and self._on_session_ending is not None:
                    try:
                        self._on_session_ending()
                    except Exception:
                        logger.exception("Session-ending callback failed")
                return
            if msg == WM_QUERYENDSESSION:
                logger.info("WM_QUERYENDSESSION received; persisting locally takes priority over sync")
        except Exception:
            logger.exception("Failed handling Win32 message %s", msg)

    def _safe_record(self, event_type: EventType, source: str, **metadata: Any) -> None:
        try:
            self._record(event_type, metadata=metadata, source=source)
        except Exception:
            logger.exception("Failed to record %s", event_type.value)

    def _run(self) -> None:
        try:
            import win32con
            import win32gui
            import win32ts
        except ImportError:
            logger.exception("pywin32 is required for live Windows session detection")
            return
        try:
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = self._wnd_proc
            wc.lpszClassName = "WorkPulseDesktopAgent"
            wc.hInstance = win32gui.GetModuleHandle(None)
            class_atom = win32gui.RegisterClass(wc)
            self._hwnd = win32gui.CreateWindow(
                class_atom,
                "WorkPulseDesktopAgent",
                0,
                0,
                0,
                0,
                0,
                win32con.HWND_MESSAGE,
                0,
                wc.hInstance,
                None,
            )
            win32ts.WTSRegisterSessionNotification(self._hwnd, NOTIFY_FOR_THIS_SESSION)
            logger.info("Registered for Windows session notifications")
            while not self._stop.is_set():
                win32gui.PumpWaitingMessages()
                self._stop.wait(0.2)
        except Exception:
            logger.exception("Win32 message loop failed")
        finally:
            if self._hwnd:
                try:
                    import win32ts

                    win32ts.WTSUnRegisterSessionNotification(self._hwnd)
                except Exception:
                    logger.exception("Failed to unregister session notifications")

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        self.handle_message(msg, wparam, lparam)
        try:
            import win32gui

            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        except Exception:
            return 0
