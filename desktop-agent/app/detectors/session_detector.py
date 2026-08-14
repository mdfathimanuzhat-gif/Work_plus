"""Map Windows Terminal Services session notifications to agent events.

Canonical WTS values (winuser.h / wtsapi32.h):

    WTS_SESSION_LOGON  = 5
    WTS_SESSION_LOGOFF = 6
    WTS_SESSION_LOCK   = 7
    WTS_SESSION_UNLOCK = 8

The message pump in `win32_loop` delivers WM_WTSSESSION_CHANGE here. Mapping is
pure so unit tests do not need a Windows session.
"""

from __future__ import annotations

from app.models import EventType

WTS_CONSOLE_CONNECT = 0x1
WTS_CONSOLE_DISCONNECT = 0x2
WTS_REMOTE_CONNECT = 0x3
WTS_REMOTE_DISCONNECT = 0x4
WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8

WM_WTSSESSION_CHANGE = 0x02B1
NOTIFY_FOR_THIS_SESSION = 0


def map_session_notification(wparam: int) -> EventType | None:
    """Return the attendance event for a WM_WTSSESSION_CHANGE wParam, if any."""
    mapping = {
        WTS_SESSION_LOGON: EventType.WINDOWS_LOGIN,
        WTS_CONSOLE_CONNECT: EventType.WINDOWS_LOGIN,
        WTS_REMOTE_CONNECT: EventType.WINDOWS_LOGIN,
        WTS_SESSION_LOGOFF: EventType.WINDOWS_LOGOUT,
        WTS_CONSOLE_DISCONNECT: EventType.WINDOWS_LOGOUT,
        WTS_REMOTE_DISCONNECT: EventType.WINDOWS_LOGOUT,
        WTS_SESSION_LOCK: EventType.SYSTEM_LOCK,
        WTS_SESSION_UNLOCK: EventType.SYSTEM_UNLOCK,
    }
    return mapping.get(int(wparam))
