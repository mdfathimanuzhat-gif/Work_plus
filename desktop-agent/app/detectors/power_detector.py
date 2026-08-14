"""Map Windows power and end-session messages to agent events.

    WM_POWERBROADCAST  (0x0218)
        PBT_APMSUSPEND          = 0x0004  -> SYSTEM_SLEEP
        PBT_APMRESUMESUSPEND    = 0x0007  -> SYSTEM_WAKE
        PBT_APMRESUMEAUTOMATIC  = 0x0012  -> SYSTEM_WAKE

    WM_ENDSESSION      (0x0016)
        ENDSESSION_LOGOFF       = 0x80000000 -> WINDOWS_LOGOUT
        otherwise shutdown/restart

Restart vs shutdown is best-effort: Windows does not always expose the reboot
flag to a user-mode listener. When the restart flag cannot be determined, the
event is SYSTEM_SHUTDOWN with metadata noting the uncertainty.
"""

from __future__ import annotations

from app.models import EventType

WM_POWERBROADCAST = 0x0218
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016

PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMECRITICAL = 0x0006

ENDSESSION_LOGOFF = 0x80000000
ENDSESSION_CRITICAL = 0x40000000
ENDSESSION_CLOSEAPP = 0x00000001

# Undocumented but widely used: lParam bit set when a reboot was requested.
ENDSESSION_RESTART = 0x00400000


def map_power_broadcast(wparam: int) -> EventType | None:
    """Return SYSTEM_SLEEP or SYSTEM_WAKE for a WM_POWERBROADCAST wParam."""
    mapping = {
        PBT_APMSUSPEND: EventType.SYSTEM_SLEEP,
        PBT_APMRESUMESUSPEND: EventType.SYSTEM_WAKE,
        PBT_APMRESUMEAUTOMATIC: EventType.SYSTEM_WAKE,
        PBT_APMRESUMECRITICAL: EventType.SYSTEM_WAKE,
    }
    return mapping.get(int(wparam))


def map_end_session(wparam: int, lparam: int, *, restart_requested: bool | None = None) -> EventType | None:
    """Map WM_ENDSESSION to logout, shutdown, or restart.

    `wparam` is FALSE if the session is not actually ending.
    """
    if not wparam:
        return None
    if lparam & ENDSESSION_LOGOFF:
        return EventType.WINDOWS_LOGOUT
    if restart_requested is True or (lparam & ENDSESSION_RESTART):
        return EventType.SYSTEM_RESTART
    return EventType.SYSTEM_SHUTDOWN


def end_session_metadata(wparam: int, lparam: int, *, restart_requested: bool | None = None) -> dict[str, object]:
    return {
        "wparam": int(wparam),
        "lparam": int(lparam),
        "end_session_logoff": bool(lparam & ENDSESSION_LOGOFF),
        "end_session_critical": bool(lparam & ENDSESSION_CRITICAL),
        "restart_requested": restart_requested,
    }
