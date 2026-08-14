# WorkPulse desktop agent

Local Windows event detection, **offline SQLite storage**, **background
synchronization**, and a **continuous Windows runtime** (Phase 5E) for the
WorkPulse FastAPI API. This phase does **not** calculate timesheets, track
location, or capture screen/keyboard content.

Real Windows lock/unlock/idle validation is documented in
[windows-testing.md](windows-testing.md).


## Purpose

Run on an employee Windows PC and record session, power, and idle transitions.
Events are written to a local SQLite file so they are not lost when the network
or backend is unavailable. When the API is reachable, a background sync service
uploads pending rows to PostgreSQL (see [event-sync.md](event-sync.md)).

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
| `PENDING` | Saved locally; not confirmed by the server |
| `SYNCING` | Upload in flight (reverted to `PENDING` if the process stops) |
| `SYNCED` | Server accepted or reported `already_processed` |
| `FAILED` | Permanent validation failure (not used for network outages) |

The background sync service lives in `desktop-agent/app/sync/` (`sync_service.py`,
`api_client.py`, `auth.py`, `retry.py`). Detectors do not call HTTP.

## Offline behavior

| Situation | Result |
| --- | --- |
| Internet up or down | Event → SQLite `PENDING` |
| Agent restart | Existing rows remain; in-memory state is restored from SQLite; `SYNCING` is reverted to `PENDING` |
| Computer restart | Same file on disk; pending events upload when the API is reachable |
| API down | New events stay `PENDING`; sync retries with exponential backoff |
| API up | Batches of `SYNC_BATCH_SIZE` are posted to `/api/agent/events/batch` |

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
| `API_BASE_URL` | unset | WorkPulse origin, e.g. `https://company.example.com` (no trailing `/api`) |
| `ALLOW_INSECURE_HTTP` | `false` | Set `true` only for local `http://` development |
| `SYNC_ENABLED` | `false` | Start the background uploader |
| `SYNC_BATCH_SIZE` | `50` | Max events per request |
| `SYNC_INTERVAL_SECONDS` | `15` | Pause between successful sync cycles |
| `SYNC_MAX_BACKOFF_SECONDS` | `60` | Cap for retry delays |
| `SYNC_REQUEST_TIMEOUT_SECONDS` | `15` | HTTP timeout |
| `STATUS_HEARTBEAT_SECONDS` | `30` | How often status is written to `status.json` and the log |
| `AGENT_EMAIL` / `AGENT_PASSWORD` | unset | Used only to enroll the device (never committed) |
| `DEVICE_SECRET` | unset | Optional; otherwise `{DATA_DIR}/device_secret` |

`desktop-agent/.env.example` enables `SYNC_ENABLED=true` and local HTTP for
Windows development. Production must use HTTPS and `ALLOW_INSECURE_HTTP=false`.

## Windows runtime (Phase 5E)

Entry point: `python main.py`. The process runs until Ctrl+C, a termination
signal, or a Windows session-end notification. It does **not** exit after one
event.

| Path (Windows) | File |
| --- | --- |
| `%LOCALAPPDATA%\WorkPulse\events.db` | SQLite queue |
| `%LOCALAPPDATA%\WorkPulse\logs\agent.log` | Rotating diagnostic log |
| `%LOCALAPPDATA%\WorkPulse\logs\events.log` | Rotating event lines |
| `%LOCALAPPDATA%\WorkPulse\device_identity.json` | Stable device UUID (not MAC) |
| `%LOCALAPPDATA%\WorkPulse\device_secret` | Device secret (never logged) |
| `%LOCALAPPDATA%\WorkPulse\agent.lock` | Single-instance lock |
| `%LOCALAPPDATA%\WorkPulse\status.json` | Last health snapshot |

**Single instance:** a second `python main.py` logs the condition and exits
with code 2.

**Graceful shutdown:** stop new activity events, persist logout/shutdown if
Windows delivers `WM_ENDSESSION`, stop the sync worker without waiting for a
full upload, close Win32 listeners, then exit. SQLite persistence always
wins over network sync.

**Health:** `python main.py --status` prints RUNNING/STOPPED, device id,
employee email (if configured), backend CONNECTED/OFFLINE/DISABLED, pending
count, last event, and last successful sync. No passwords, secrets, or JWTs.

**Startup (development):** do not install a Windows Service. Optional reversible
current-user Startup shortcut:

```powershell
.\scripts\windows\register-dev-startup.ps1
.\scripts\windows\unregister-dev-startup.ps1
```

**Packaging:** `desktop-agent/workpulse-agent.spec` is a PyInstaller starting
point. Do not bundle `.env` or `device_secret`. Packaging is not required for
this phase.

Real Windows lock/unlock/idle/reboot steps: [windows-testing.md](windows-testing.md).
First Windows test machine: enroll **EMP001 — Israh Zunain** only.

## Running locally

```bash
cd desktop-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --test --once --sync-once
```

On Windows, live detection (continuous): `python main.py`.

```powershell
python main.py --status
```

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
| Events stay PENDING | Confirm `SYNC_ENABLED`, `API_BASE_URL`, and that `GET /api/health` succeeds |
| AUTH_ERROR in logs | Re-enroll; check device secret and that the device is active |
| Another WorkPulse agent is already running | Stop the existing instance; `--status` reports RUNNING |
| Live mode requires Windows | Use `--test` on Linux/macOS |

Automated tests (unit + integration) run on any OS. Windows-only and
`WINDOWS_MANUAL_TEST` cases are marked and documented in
[windows-testing.md](windows-testing.md).

```bash
cd desktop-agent
pytest
```
