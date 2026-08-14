# WorkPulse desktop agent

Local Windows event detection and **offline SQLite storage** for attendance.
This phase does **not** connect to FastAPI, PostgreSQL, or the web UI. It does
**not** calculate worked time, track location, or capture screen/keyboard content.

## Purpose

Run on an employee Windows PC and record session, power, and idle transitions.
Events are written to a local SQLite file so they are not lost when the network
or backend is unavailable. Synchronization with the server is a later phase.

## Local SQLite architecture

```text
Windows event
      ↓
Detector (session / power / idle)
      ↓
EventService (de-duplication, UTC timestamp, UUID)
      ↓
SQLite EventRepository.save_event()
      ↓
attendance_events.sync_status = PENDING
```

The event is treated as captured only after the SQLite insert succeeds. The
rotating text log is written as well. Nothing in this path requires internet
access.

Code lives in `desktop-agent/app/storage/` (`database.py`, `migrations.py`,
`models.py`, `repository.py`). Runtime data (the `.db` file, identity, logs)
is **not** stored in that package.

## Database location

Default (no administrator rights required):

| OS | Directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\WorkPulse\events.db` |
| Linux (dev) | `$XDG_DATA_HOME/WorkPulse/events.db` or `~/.local/share/WorkPulse/events.db` |

Override with `LOCAL_DATABASE_PATH`. `DATA_DIR` still holds `device_identity.json`
and, unless `LOG_DIR` is set, `logs/`.

Do not point a system-wide install at the source tree. Tests use a temporary
file and never the developer’s real queue.

## Event schema

Table `attendance_events`:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | Local row id |
| `event_id` | TEXT UNIQUE | UUID; unchanged when later synced |
| `event_type` | TEXT | `WINDOWS_LOGIN`, `SYSTEM_LOCK`, … |
| `event_timestamp` | TEXT | UTC ISO-8601 with `Z` |
| `device_identifier` | TEXT | Stable local UUID |
| `device_name` | TEXT | Hostname |
| `username` | TEXT | Windows session user |
| `metadata` | TEXT | JSON (source, Win32 params, `operating_system`, anomaly). No secrets |
| `sync_status` | TEXT | See below |
| `sync_attempts` | INTEGER | Incremented by `mark_event_syncing` |
| `last_sync_attempt` | TEXT | UTC, nullable |
| `synced_at` | TEXT | UTC, nullable |
| `created_at` | TEXT | UTC insert time |

SQLite is opened with WAL, a 5s busy timeout, and foreign keys enabled.

## Sync status meaning

| Status | Meaning |
| --- | --- |
| `PENDING` | Saved locally; not sent to the server (all new events) |
| `SYNCING` | Reserved for Phase 5C |
| `SYNCED` | Reserved for Phase 5C after the server confirms the UUID |
| `FAILED` | Reserved for Phase 5C |

Helpers exist (`mark_event_syncing`, `mark_event_synced`, `mark_event_failed`)
but **no network client** is implemented. Events stay `PENDING` through agent
and computer restarts.

## Offline behavior

| Situation | Result |
| --- | --- |
| Internet up or down | Event → SQLite `PENDING` |
| Agent restart | Existing rows remain; in-memory state is restored from SQLite |
| Computer restart | Same file on disk; events remain `PENDING` |

Duplicate `event_id` values are rejected (`UNIQUE`). Repeated lock-while-locked
events are still filtered by Phase 5A before insert. Valid lock/unlock pairs
are stored separately.

## Retention policy

`LOCAL_EVENT_RETENTION_DAYS` (default **30**). `cleanup_synced_events()` deletes
only `SYNCED` rows whose `synced_at` is older than that window. `PENDING` rows
are never deleted by cleanup. Synced events are **not** removed immediately
after a future successful sync.

## Events collected

| Event | Typical Windows source |
| --- | --- |
| `WINDOWS_LOGIN` | `WM_WTSSESSION_CHANGE` / `WTS_SESSION_LOGON` (and console/remote connect) |
| `WINDOWS_LOGOUT` | `WTS_SESSION_LOGOFF` / `WM_ENDSESSION` with `ENDSESSION_LOGOFF` |
| `SYSTEM_LOCK` | `WTS_SESSION_LOCK` |
| `SYSTEM_UNLOCK` | `WTS_SESSION_UNLOCK` |
| `SYSTEM_SLEEP` | `WM_POWERBROADCAST` / `PBT_APMSUSPEND` |
| `SYSTEM_WAKE` | `PBT_APMRESUMESUSPEND` or `PBT_APMRESUMEAUTOMATIC` |
| `SYSTEM_SHUTDOWN` | `WM_ENDSESSION` (session ending, not logoff) |
| `SYSTEM_RESTART` | `WM_ENDSESSION` when a restart is indicated (best-effort) |
| `IDLE_START` | `GetLastInputInfo` idle time ≥ `IDLE_THRESHOLD_SECONDS` |
| `IDLE_END` | Input resumes after idle, or the session is locked while idle |

Each event has a unique `event_id`, a UTC `event_timestamp`, an `event_type`,
and device labels. Duplicate transitions (for example repeated `SYSTEM_LOCK`
while already locked) are ignored. Unexpected order (unlock without lock,
shutdown without logout) is recorded with an `anomaly` flag and does not crash
the agent.

## Data collected

- Stable local `device_identifier` (UUID stored next to the database)
- Computer hostname (`device_name`)
- Operating system label (in metadata)
- Windows session username
- Event type, UTC timestamp, and small metadata (source, Win32 parameters, anomaly)

## Data NOT collected

- Keystrokes, screenshots, mouse coordinates
- Webcam, microphone, browser history, file contents
- Passwords, JWT tokens, chat content, location, application titles

## Idle detection

`GetLastInputInfo` is polled every `IDLE_POLL_INTERVAL_SECONDS` (default 5).
Default idle threshold: **300 seconds**. While the session is locked, new
idle-start events are not emitted.

## Privacy and security

Attendance facts only. The SQLite file is created with owner-only permissions
where the OS allows (`chmod 600` on Unix; `icacls` on Windows). The agent
continues if permission tightening fails. Do not copy `events.db` into source
control or shared folders.

## Configuration

Copy `desktop-agent/.env.example` to `desktop-agent/.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `IDLE_THRESHOLD_SECONDS` | `300` | Seconds without input before `IDLE_START` |
| `IDLE_POLL_INTERVAL_SECONDS` | `5` | How often to read `GetLastInputInfo` |
| `LOG_LEVEL` | `INFO` | Diagnostic log level |
| `AGENT_MODE` | `live` | `live` or `test` |
| `MIX_SIMULATED_AND_REAL` | `false` | Mix simulator with live detectors |
| `TEST_EVENT_DELAY_SECONDS` | `0.5` | Pause between simulated events |
| `DATA_DIR` | per-user WorkPulse dir | Identity file |
| `LOG_DIR` | `{DATA_DIR}/logs` | Rotating logs |
| `LOCAL_DATABASE_PATH` | `{DATA_DIR}/events.db` | SQLite queue |
| `LOCAL_EVENT_RETENTION_DAYS` | `30` | Age after which `SYNCED` rows may be deleted |

## Running locally

```bash
cd desktop-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --test --once
```

On Windows, live detection: `python main.py`.

```text
WorkPulse Desktop Agent
Status: RUNNING

Device: DESKTOP-TEST

Local Database:
C:\Users\...\AppData\Local\WorkPulse\events.db

Events:
[09:00:01] WINDOWS_LOGIN     PENDING
[13:05:20] SYSTEM_LOCK       PENDING
[13:20:10] SYSTEM_UNLOCK     PENDING

Total events: 3
Pending sync: 3
```

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Agent starts but events vanish after restart | Confirm `LOCAL_DATABASE_PATH` is a persistent disk path, not a temp dir |
| `Failed to initialize local database` | Directory permissions; disk full; path not writable without admin |
| Duplicate event_id in logs | Same UUID inserted twice; the second insert is rejected and not captured |
| WAL files (`events.db-wal`) beside the db | Normal while the agent is running |
| Events stay PENDING | Expected until Phase 5C |

```bash
cd desktop-agent
pytest
```
