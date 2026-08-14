"""Focused WM_ENDSESSION mapping tests.

WM_ENDSESSION does not document restart vs shutdown. wParam=TRUE and lParam=0
is SYSTEM_SHUTDOWN. SYSTEM_RESTART requires the restart bit on this message.
"""

from __future__ import annotations

import inspect

from app.detectors.power_detector import ENDSESSION_LOGOFF, ENDSESSION_RESTART, WM_ENDSESSION, map_end_session
from app.detectors.win32_loop import Win32EventLoop
from app.detectors import win32_loop as win32_loop_module
from app.models import EventType


def test_wparam_true_lparam_zero_is_shutdown() -> None:
    assert map_end_session(1, 0) is EventType.SYSTEM_SHUTDOWN
    assert map_end_session(True, 0) is EventType.SYSTEM_SHUTDOWN
    assert map_end_session(1, 0, restart_requested=True) is EventType.SYSTEM_SHUTDOWN


def test_end_session_logoff_and_restart_bit() -> None:
    assert map_end_session(1, ENDSESSION_LOGOFF) is EventType.WINDOWS_LOGOUT
    assert map_end_session(1, ENDSESSION_RESTART) is EventType.SYSTEM_RESTART


def test_loop_endsession_zero_flags_is_shutdown_not_restart() -> None:
    recorded: list[EventType] = []

    def record(event_type: EventType, metadata=None, source="detector") -> None:
        recorded.append(event_type)

    loop = Win32EventLoop(record)
    loop.handle_message(WM_ENDSESSION, 1, 0)
    loop.handle_message(WM_ENDSESSION, 1, ENDSESSION_RESTART)
    assert recorded == [EventType.SYSTEM_SHUTDOWN, EventType.SYSTEM_RESTART]


def test_handle_message_source_has_no_reboot_registry_heuristic() -> None:
    source = inspect.getsource(win32_loop_module)
    assert "RebootRequired" not in source
    assert "_restart_requested" not in source
    handle_src = inspect.getsource(Win32EventLoop.handle_message)
    assert "restart_requested" not in handle_src
