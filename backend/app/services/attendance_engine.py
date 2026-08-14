"""Deterministic attendance state machine and interval calculator.

Raw events are the source of truth. Durations are integer seconds derived from
non-overlapping state intervals. Organization timezone is used only to group
intervals onto attendance dates; timestamps remain UTC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.enums import AttendanceEventType, AttendanceStatus


class WorkState(str, Enum):
    OFFLINE = "OFFLINE"
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    IDLE = "IDLE"
    SLEEPING = "SLEEPING"


class SessionSliceStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CONTINUED = "CONTINUED"


@dataclass(frozen=True)
class EngineEvent:
    event_id: UUID
    event_type: AttendanceEventType
    event_time: datetime
    device_id: UUID | None = None


@dataclass(frozen=True)
class Anomaly:
    code: str
    message: str
    event_time: datetime
    event_type: str


@dataclass(frozen=True)
class StateInterval:
    start: datetime
    end: datetime
    state: WorkState
    device_id: UUID | None


@dataclass
class SessionSlice:
    attendance_date: date
    session_start: datetime
    session_end: datetime | None
    device_id: UUID | None
    status: SessionSliceStatus
    active_seconds: int = 0
    locked_seconds: int = 0
    idle_seconds: int = 0
    sleep_seconds: int = 0
    session_duration_seconds: int = 0
    ended_reason: str | None = None


@dataclass
class DailyAttendance:
    attendance_date: date
    first_login_time: datetime | None
    last_logout_time: datetime | None
    total_session_seconds: int
    total_locked_seconds: int
    total_idle_seconds: int
    total_sleep_seconds: int
    total_active_seconds: int
    session_count: int
    status: AttendanceStatus
    is_complete: bool
    sessions: list[SessionSlice] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)


@dataclass
class EngineResult:
    live_state: WorkState
    days: dict[date, DailyAttendance]
    anomalies: list[Anomaly]


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def load_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local_date(moment: datetime, tz: ZoneInfo) -> date:
    return ensure_utc(moment).astimezone(tz).date()


def local_day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(timezone.utc)
    next_day = datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(days=1)
    end = next_day.astimezone(timezone.utc)
    return start, end


def seconds_between(start: datetime, end: datetime) -> int:
    return max(0, int((ensure_utc(end) - ensure_utc(start)).total_seconds()))


def _transition(
    state: WorkState,
    event_type: AttendanceEventType,
    idle_pending: bool,
) -> tuple[WorkState, bool, list[tuple[str, str]], str | None]:
    """Return (next_state, idle_pending, anomalies, session_action)."""
    anomalies: list[tuple[str, str]] = []
    session_action: str | None = None

    if event_type is AttendanceEventType.LOGIN:
        if state is WorkState.OFFLINE:
            return WorkState.ACTIVE, False, anomalies, "start"
        anomalies.append(("duplicate_login", "LOGIN received while a session was already open"))
        return state, idle_pending, anomalies, None

    if event_type in {AttendanceEventType.LOGOUT, AttendanceEventType.SHUTDOWN, AttendanceEventType.RESTART}:
        if state is WorkState.OFFLINE:
            anomalies.append(
                (
                    "logout_without_login",
                    f"{event_type.value} received while offline",
                )
            )
            return state, False, anomalies, None
        if event_type is AttendanceEventType.SHUTDOWN:
            session_action = "shutdown"
        elif event_type is AttendanceEventType.RESTART:
            session_action = "restart"
        else:
            session_action = "logout"
        return WorkState.OFFLINE, False, anomalies, session_action

    if state is WorkState.OFFLINE:
        anomalies.append(
            (
                "event_outside_session",
                f"{event_type.value} ignored because no session is open",
            )
        )
        return state, idle_pending, anomalies, None

    if event_type is AttendanceEventType.LOCK:
        if state is WorkState.LOCKED:
            anomalies.append(("duplicate_lock", "LOCK received while already locked"))
            return state, idle_pending, anomalies, None
        if state is WorkState.SLEEPING:
            anomalies.append(("lock_while_sleeping", "LOCK while sleeping; remaining SLEEPING"))
            return state, idle_pending, anomalies, None
        return WorkState.LOCKED, idle_pending, anomalies, None

    if event_type is AttendanceEventType.UNLOCK:
        if state is WorkState.LOCKED:
            return (WorkState.IDLE if idle_pending else WorkState.ACTIVE), idle_pending, anomalies, None
        anomalies.append(("unexpected_unlock", "UNLOCK received without an active LOCK"))
        return state, idle_pending, anomalies, None

    if event_type is AttendanceEventType.IDLE_START:
        if state is WorkState.IDLE:
            anomalies.append(("duplicate_idle_start", "IDLE_START received while already idle"))
            return state, True, anomalies, None
        if state is WorkState.LOCKED:
            return state, True, anomalies, None
        if state is WorkState.SLEEPING:
            return state, True, anomalies, None
        return WorkState.IDLE, True, anomalies, None

    if event_type is AttendanceEventType.IDLE_END:
        if state is WorkState.IDLE:
            return WorkState.ACTIVE, False, anomalies, None
        if idle_pending and state in {WorkState.LOCKED, WorkState.SLEEPING}:
            return state, False, anomalies, None
        anomalies.append(("idle_end_without_start", "IDLE_END received without IDLE_START"))
        return state, False, anomalies, None

    if event_type is AttendanceEventType.SLEEP:
        if state is WorkState.SLEEPING:
            anomalies.append(("duplicate_sleep", "SLEEP received while already sleeping"))
            return state, idle_pending, anomalies, None
        return WorkState.SLEEPING, idle_pending, anomalies, None

    if event_type is AttendanceEventType.WAKE:
        if state is WorkState.SLEEPING:
            return WorkState.ACTIVE, False, anomalies, None
        anomalies.append(("unexpected_wake", "WAKE received without SLEEP"))
        if state is not WorkState.OFFLINE:
            return WorkState.ACTIVE, False, anomalies, None
        return state, idle_pending, anomalies, None

    return state, idle_pending, anomalies, session_action


def replay_events(
    events: list[EngineEvent],
    *,
    timezone_name: str,
    as_of: datetime,
) -> EngineResult:
    """Walk events in order and produce daily derived attendance."""
    tz = load_zoneinfo(timezone_name)
    as_of = ensure_utc(as_of)
    ordered = sorted(events, key=lambda item: (ensure_utc(item.event_time), str(item.event_id)))

    state = WorkState.OFFLINE
    idle_pending = False
    last_time: datetime | None = None
    last_device: UUID | None = None
    intervals: list[StateInterval] = []
    anomalies: list[Anomaly] = []
    session_end_at: dict[datetime, str] = {}
    open_session_start: datetime | None = None

    def close_interval(until: datetime) -> None:
        nonlocal last_time
        if state is WorkState.OFFLINE or last_time is None:
            return
        until_utc = ensure_utc(until)
        if until_utc <= last_time:
            return
        intervals.append(StateInterval(last_time, until_utc, state, last_device))

    for event in ordered:
        moment = ensure_utc(event.event_time)
        if moment > as_of:
            break
        if last_time is not None and moment < last_time:
            anomalies.append(
                Anomaly("out_of_order", "Event timestamp is earlier than the previous event", moment, event.event_type.value)
            )
            continue

        next_state, next_idle, codes, session_action = _transition(state, event.event_type, idle_pending)
        for code, message in codes:
            anomalies.append(Anomaly(code, message, moment, event.event_type.value))

        if next_state is not state:
            close_interval(moment)
            last_time = moment
            last_device = event.device_id
            if session_action == "start":
                open_session_start = moment
            if session_action in {"logout", "shutdown", "restart"} and open_session_start is not None:
                session_end_at[open_session_start] = session_action
                open_session_start = None
            state = next_state
            idle_pending = next_idle
        else:
            idle_pending = next_idle

    close_interval(as_of)

    slices = _slices_from_intervals(intervals, tz, as_of, session_end_at, state is not WorkState.OFFLINE)
    days = _aggregate_days(slices, anomalies, tz)
    return EngineResult(live_state=state, days=days, anomalies=anomalies)


def _split_interval(interval: StateInterval, tz: ZoneInfo) -> list[tuple[date, StateInterval]]:
    parts: list[tuple[date, StateInterval]] = []
    cursor = interval.start
    end = interval.end
    while cursor < end:
        day = local_date(cursor, tz)
        _, day_end = local_day_bounds(day, tz)
        clip_end = min(end, day_end)
        parts.append((day, StateInterval(cursor, clip_end, interval.state, interval.device_id)))
        cursor = clip_end
    return parts


def _slices_from_intervals(
    intervals: list[StateInterval],
    tz: ZoneInfo,
    as_of: datetime,
    session_end_at: dict[datetime, str],
    still_open: bool,
) -> list[SessionSlice]:
    if not intervals:
        return []

    sessions: list[list[StateInterval]] = []
    current: list[StateInterval] = []
    for interval in intervals:
        if current and interval.start > current[-1].end:
            sessions.append(current)
            current = []
        current.append(interval)
    if current:
        sessions.append(current)

    slices: list[SessionSlice] = []
    for group in sessions:
        session_start = group[0].start
        session_end = group[-1].end
        ended_reason = session_end_at.get(session_start)
        logical_closed = ended_reason is not None
        day_parts: dict[date, list[StateInterval]] = {}
        for interval in group:
            for day, part in _split_interval(interval, tz):
                day_parts.setdefault(day, []).append(part)
        ordered_days = sorted(day_parts)
        for index, day in enumerate(ordered_days):
            parts = day_parts[day]
            start = parts[0].start
            end = parts[-1].end
            is_last_day = index == len(ordered_days) - 1
            if not is_last_day:
                status = SessionSliceStatus.CONTINUED
                stored_end = end
            elif logical_closed:
                status = SessionSliceStatus.CLOSED
                stored_end = end
            else:
                status = SessionSliceStatus.OPEN
                stored_end = None
            counts = {WorkState.ACTIVE: 0, WorkState.LOCKED: 0, WorkState.IDLE: 0, WorkState.SLEEPING: 0}
            for part in parts:
                counts[part.state] = counts.get(part.state, 0) + seconds_between(part.start, part.end)
            active = counts[WorkState.ACTIVE]
            locked = counts[WorkState.LOCKED]
            idle = counts[WorkState.IDLE]
            sleep = counts[WorkState.SLEEPING]
            session_seconds = active + locked + idle + sleep
            if active < 0:
                active = 0
            slices.append(
                SessionSlice(
                    attendance_date=day,
                    session_start=start,
                    session_end=stored_end,
                    device_id=parts[0].device_id,
                    status=status,
                    active_seconds=active,
                    locked_seconds=locked,
                    idle_seconds=idle,
                    sleep_seconds=sleep,
                    session_duration_seconds=session_seconds,
                    ended_reason=ended_reason if is_last_day else "midnight_split",
                )
            )
    return slices


def _aggregate_days(slices: list[SessionSlice], anomalies: list[Anomaly], tz: ZoneInfo) -> dict[date, DailyAttendance]:
    by_day: dict[date, list[SessionSlice]] = {}
    for item in slices:
        by_day.setdefault(item.attendance_date, []).append(item)

    result: dict[date, DailyAttendance] = {}
    for day, day_slices in by_day.items():
        day_anomalies = [item for item in anomalies if local_date(item.event_time, tz) == day]
        first_login = min((item.session_start for item in day_slices), default=None)
        logout_times = [item.session_end for item in day_slices if item.status is SessionSliceStatus.CLOSED and item.session_end]
        last_logout = max(logout_times) if logout_times else None
        open_or_continued = any(item.status is not SessionSliceStatus.CLOSED for item in day_slices)
        only_continued = all(item.status is SessionSliceStatus.CONTINUED for item in day_slices)
        has_open = any(item.status is SessionSliceStatus.OPEN for item in day_slices)
        total_session = sum(item.session_duration_seconds for item in day_slices)
        total_locked = sum(item.locked_seconds for item in day_slices)
        total_idle = sum(item.idle_seconds for item in day_slices)
        total_sleep = sum(item.sleep_seconds for item in day_slices)
        total_active = sum(item.active_seconds for item in day_slices)
        if total_active < 0:
            total_active = 0
        if has_open:
            status = AttendanceStatus.INCOMPLETE
            complete = False
        elif only_continued or (open_or_continued and last_logout is None):
            status = AttendanceStatus.PARTIAL
            complete = False
        elif total_session > 0:
            status = AttendanceStatus.PRESENT
            complete = True
        else:
            status = AttendanceStatus.ABSENT
            complete = True
        result[day] = DailyAttendance(
            attendance_date=day,
            first_login_time=first_login,
            last_logout_time=last_logout,
            total_session_seconds=total_session,
            total_locked_seconds=total_locked,
            total_idle_seconds=total_idle,
            total_sleep_seconds=total_sleep,
            total_active_seconds=total_active,
            session_count=len(day_slices),
            status=status,
            is_complete=complete,
            sessions=day_slices,
            anomalies=day_anomalies,
        )
    return result


def empty_day(day: date) -> DailyAttendance:
    return DailyAttendance(
        attendance_date=day,
        first_login_time=None,
        last_logout_time=None,
        total_session_seconds=0,
        total_locked_seconds=0,
        total_idle_seconds=0,
        total_sleep_seconds=0,
        total_active_seconds=0,
        session_count=0,
        status=AttendanceStatus.ABSENT,
        is_complete=True,
        sessions=[],
        anomalies=[],
    )
