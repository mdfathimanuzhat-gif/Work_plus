# WorkPulse attendance engine

Phase 5D turns synchronized `AttendanceEvent` rows into daily attendance
records and sessions. Raw events remain the source of truth. Calculated
fields are derived, read-only, and recalculated from events.

Timesheets, dashboards, approvals, and manual corrections are out of scope.

## Architecture

```text
AttendanceEvent (PostgreSQL, immutable)
        ↓
State machine (interval walk)
        ↓
Non-overlapping state intervals
        ↓
Split on organization-local midnight
        ↓
AttendanceSession slices + daily Attendance
```

The desktop agent and browser never submit durations. `POST /api/agent/events/batch`
still stores events; after accepted inserts the server recalculates affected dates.

## State machine

```text
                 LOGIN
      OFFLINE ──────────► ACTIVE
         ▲                  │
         │ LOGOUT           │ LOCK
         │ SHUTDOWN         ▼
         │ RESTART       LOCKED
         │                  │
         │                  │ UNLOCK
         │                  ▼
         └──────────────  ACTIVE ◄── IDLE_END
                            │
                   IDLE_START│
                            ▼
                           IDLE
                            │
              SLEEP from ACTIVE / IDLE / LOCKED
                            ▼
                        SLEEPING
                            │
                          WAKE
                            ▼
                          ACTIVE
```

States: `OFFLINE`, `ACTIVE`, `LOCKED`, `IDLE`, `SLEEPING`.

Live status (`GET /api/attendance/me/live`) is the state after replaying events
up to the current UTC time. It is not stored separately.

## Event interpretation

| Event | Typical transition |
| --- | --- |
| LOGIN | OFFLINE → ACTIVE (starts a session) |
| LOGOUT / SHUTDOWN / RESTART | any in-session state → OFFLINE (ends a session) |
| LOCK | ACTIVE or IDLE → LOCKED |
| UNLOCK | LOCKED → ACTIVE, or IDLE if an idle period started during the lock |
| IDLE_START | ACTIVE → IDLE; while LOCKED or SLEEPING, idle is pending but the stronger state is kept |
| IDLE_END | IDLE → ACTIVE |
| SLEEP | in-session → SLEEPING |
| WAKE | SLEEPING → ACTIVE |

Unexpected events produce an anomaly and do not crash the engine. Events outside
an open session are ignored for duration (except LOGIN).

## Duration calculation

The engine walks events in UTC order and emits **non-overlapping** intervals of
exactly one state. Durations are integer seconds of those intervals.

- Session duration = ACTIVE + LOCKED + IDLE + SLEEPING
- Active working time = ACTIVE only
- Locked / idle / sleep = time in those states

Because intervals do not overlap, lock + idle cannot be counted twice. LOCK is
the stronger inactive state: `IDLE_START` during a lock does not create idle
seconds until after `UNLOCK` (if idle is still pending).

Active seconds are clamped at zero.

## Multiple sessions

Each LOGIN after OFFLINE starts a new session. A day may have several
login/logout pairs. Daily totals sum the session slices for that local date.
`session_count` is the number of slices that day.

## Open sessions

If the last state is not OFFLINE, the session is `OPEN`. Durations for live
display use `as_of` (usually now). Stored `last_logout_time` / `session_end`
stay null. Daily status is `INCOMPLETE`. The engine does not invent a logout.

## Cross-midnight

Intervals are split at midnight **in the organization timezone**. One logical
session can produce two `AttendanceSession` rows:

- Previous local date: status `CONTINUED`, `ended_reason=midnight_split`
- Next local date: continues until logout (`CLOSED`) or still `OPEN`

Daily attendance for the first date is `PARTIAL` when work happened but there
was no logout that local date. Canonical timestamps remain UTC.

## Timezone

`organizations.timezone` (IANA name, default `UTC`) is used only to assign an
`attendance_date`. Missing/invalid names fall back to UTC.

No late/overtime rules and no shift calendars are implemented. A future work
schedule should be configuration, not hard-coded policy.

## Status

| Status | Meaning |
| --- | --- |
| PRESENT | At least one session closed that local date |
| INCOMPLETE | A session is still open as of calculation time |
| PARTIAL | Activity that local date, but the session continued past local midnight without a logout that day |
| ABSENT | No in-session time that local date |
| HALF_DAY / ON_LEAVE / HOLIDAY | Reserved; not assigned by this engine |

`total_work_seconds` on `attendance` stores **active** seconds (existing column).
`total_session_seconds` stores full in-session time. `total_sleep_seconds` is new.

## Recalculation

`recalculate_employee` deletes existing session rows for the day and writes a
fresh derived record. Running it twice on the same events yields the same
seconds and status. Anomalies are stored on `attendance.anomalies` and a
replaceable audit row `attendance.recalculated`.

## Security

- No POST/PATCH/PUT for calculated attendance
- Employees cannot change events or durations
- `GET /api/attendance/{employee_id}/{date}` uses the same isolation as people
  access: own / team / organization via `attendance.view_*` permissions
- HR can view; HR cannot rewrite raw events in this phase
- Manual corrections are a later, audited feature

## API

| Method | Path |
| --- | --- |
| GET | `/api/attendance/me` |
| GET | `/api/attendance/me/live` |
| GET | `/api/attendance/me/{date}` |
| GET | `/api/attendance/team/{date}` |
| GET | `/api/attendance/{employee_id}/{date}` |

## Example

09:05 LOGIN, 13:00 LOCK, 13:30 UNLOCK, 15:10 IDLE_START, 15:25 IDLE_END, 18:05 LOGOUT

- first_login 09:05, last_logout 18:05
- session 9h, locked 30m, idle 15m, active 8h 15m
- status PRESENT, session_count 1
