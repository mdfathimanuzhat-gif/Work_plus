"""Unit tests for the attendance state machine and duration engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.models.enums import AttendanceEventType, AttendanceStatus
from app.services.attendance_engine import EngineEvent, WorkState, replay_events, seconds_between


def _at(hour: int, minute: int = 0, day: int = 14, month: int = 8, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _event(moment: datetime, event_type: AttendanceEventType) -> EngineEvent:
    return EngineEvent(event_id=uuid4(), event_type=event_type, event_time=moment)


def _replay(events: list[EngineEvent], as_of: datetime | None = None, tz: str = "UTC"):
    last = max(item.event_time for item in events)
    return replay_events(events, timezone_name=tz, as_of=as_of or last + timedelta(seconds=1))


def test_normal_login_logout_is_nine_hours() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = result.days[datetime(2026, 8, 14, tzinfo=timezone.utc).date()]
    assert day.total_session_seconds == 9 * 3600
    assert day.total_active_seconds == 9 * 3600
    assert day.total_locked_seconds == 0
    assert day.status is AttendanceStatus.PRESENT
    assert day.session_count == 1
    assert day.is_complete is True


def test_lock_unlock_thirty_minutes() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(13), AttendanceEventType.LOCK),
            _event(_at(13, 30), AttendanceEventType.UNLOCK),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_session_seconds == 9 * 3600
    assert day.total_locked_seconds == 30 * 60
    assert day.total_active_seconds == 9 * 3600 - 30 * 60


def test_idle_thirty_minutes() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(15), AttendanceEventType.IDLE_START),
            _event(_at(15, 30), AttendanceEventType.IDLE_END),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_idle_seconds == 30 * 60
    assert day.total_active_seconds == 9 * 3600 - 30 * 60


def test_lock_and_idle_are_not_double_counted() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(13), AttendanceEventType.LOCK),
            _event(_at(13, 10), AttendanceEventType.IDLE_START),
            _event(_at(13, 30), AttendanceEventType.UNLOCK),
            _event(_at(13, 40), AttendanceEventType.IDLE_END),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_session_seconds == 9 * 3600
    assert day.total_locked_seconds == 30 * 60
    assert day.total_idle_seconds == 10 * 60
    assert day.total_active_seconds == 9 * 3600 - 40 * 60
    assert day.total_locked_seconds + day.total_idle_seconds + day.total_active_seconds + day.total_sleep_seconds == day.total_session_seconds


def test_sleep_wake() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(12), AttendanceEventType.SLEEP),
            _event(_at(12, 45), AttendanceEventType.WAKE),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_sleep_seconds == 45 * 60
    assert day.total_active_seconds == 9 * 3600 - 45 * 60
    assert day.total_active_seconds >= 0


def test_multiple_sessions() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(12), AttendanceEventType.LOGOUT),
            _event(_at(13), AttendanceEventType.LOGIN),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.session_count == 2
    assert day.total_session_seconds == 8 * 3600
    assert day.status is AttendanceStatus.PRESENT


def test_open_session_is_incomplete() -> None:
    events = [_event(_at(9), AttendanceEventType.LOGIN)]
    result = replay_events(events, timezone_name="UTC", as_of=_at(12))
    day = next(iter(result.days.values()))
    assert day.status is AttendanceStatus.INCOMPLETE
    assert day.is_complete is False
    assert day.last_logout_time is None
    assert day.total_session_seconds == 3 * 3600
    assert result.live_state is WorkState.ACTIVE
    assert day.sessions[0].session_end is None


def test_shutdown_without_logout_closes_session() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(18), AttendanceEventType.SHUTDOWN),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_session_seconds == 9 * 3600
    assert day.last_logout_time == _at(18)
    assert day.status is AttendanceStatus.PRESENT
    assert day.sessions[0].ended_reason == "shutdown"


def test_unexpected_unlock_does_not_crash() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(10), AttendanceEventType.UNLOCK),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_active_seconds == 9 * 3600
    assert any(item.code == "unexpected_unlock" for item in result.anomalies)


def test_duplicate_events_are_anomalies() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(9, 1), AttendanceEventType.LOGIN),
            _event(_at(13), AttendanceEventType.LOCK),
            _event(_at(13, 1), AttendanceEventType.LOCK),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_session_seconds == 9 * 3600
    assert {item.code for item in result.anomalies} >= {"duplicate_login", "duplicate_lock"}


def test_missing_events_outside_session() -> None:
    result = _replay(
        [
            _event(_at(8), AttendanceEventType.LOCK),
            _event(_at(8, 30), AttendanceEventType.LOGOUT),
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_session_seconds == 9 * 3600
    assert any(item.code == "event_outside_session" for item in result.anomalies)
    assert any(item.code == "logout_without_login" for item in result.anomalies)


def test_cross_midnight_session_splits_dates() -> None:
    events = [
        _event(_at(23), AttendanceEventType.LOGIN),
        _event(_at(23, 50), AttendanceEventType.LOCK),
        _event(_at(0, 10, day=15), AttendanceEventType.UNLOCK),
        _event(_at(1, 0, day=15), AttendanceEventType.LOGOUT),
    ]
    result = _replay(events)
    first = result.days[datetime(2026, 8, 14, tzinfo=timezone.utc).date()]
    second = result.days[datetime(2026, 8, 15, tzinfo=timezone.utc).date()]
    assert first.total_session_seconds == 3600
    assert first.total_locked_seconds == 10 * 60
    assert first.status is AttendanceStatus.PARTIAL
    assert second.last_logout_time == _at(1, 0, day=15)
    assert second.status is AttendanceStatus.PRESENT
    assert first.total_session_seconds + second.total_session_seconds == 2 * 3600


def test_organization_timezone_groups_local_date() -> None:
    # 22:30 UTC on the 14th is 04:00+ next calendar day in Asia/Tokyo (+9).
    login = datetime(2026, 8, 14, 22, 30, tzinfo=timezone.utc)
    logout = datetime(2026, 8, 14, 23, 30, tzinfo=timezone.utc)
    result = replay_events(
        [_event(login, AttendanceEventType.LOGIN), _event(logout, AttendanceEventType.LOGOUT)],
        timezone_name="Asia/Tokyo",
        as_of=logout + timedelta(seconds=1),
    )
    assert datetime(2026, 8, 14, tzinfo=timezone.utc).date() not in result.days
    tokyo_day = login.astimezone(ZoneInfo("Asia/Tokyo")).date()
    assert tokyo_day in result.days
    assert result.days[tokyo_day].total_session_seconds == 3600


def test_active_time_never_negative() -> None:
    result = _replay(
        [
            _event(_at(9), AttendanceEventType.LOGIN),
            _event(_at(10), AttendanceEventType.LOCK),
            _event(_at(10, 1), AttendanceEventType.IDLE_START),
            _event(_at(10, 2), AttendanceEventType.SLEEP),
            _event(_at(18), AttendanceEventType.LOGOUT),
        ]
    )
    day = next(iter(result.days.values()))
    assert day.total_active_seconds >= 0
    assert day.total_session_seconds >= day.total_active_seconds


def test_recalculation_is_deterministic() -> None:
    events = [
        _event(_at(9, 5), AttendanceEventType.LOGIN),
        _event(_at(13), AttendanceEventType.LOCK),
        _event(_at(13, 30), AttendanceEventType.UNLOCK),
        _event(_at(15, 10), AttendanceEventType.IDLE_START),
        _event(_at(15, 25), AttendanceEventType.IDLE_END),
        _event(_at(18, 5), AttendanceEventType.LOGOUT),
    ]
    first = _replay(events)
    second = _replay(events)
    day = next(iter(first.days.values()))
    again = next(iter(second.days.values()))
    assert day.total_session_seconds == 9 * 3600
    assert day.total_locked_seconds == 30 * 60
    assert day.total_idle_seconds == 15 * 60
    assert day.total_active_seconds == 8 * 3600 + 15 * 60
    assert day.status is AttendanceStatus.PRESENT
    assert day.session_count == 1
    assert day.total_session_seconds == again.total_session_seconds
    assert day.total_active_seconds == again.total_active_seconds
    assert day.total_locked_seconds == again.total_locked_seconds
    assert day.total_idle_seconds == again.total_idle_seconds


def test_seconds_between_clamps_negative() -> None:
    later = _at(10)
    earlier = _at(9)
    assert seconds_between(later, earlier) == 0
