# WorkPulse desktop agent (Phase 5A)

Local Windows event detection for attendance. This phase does **not** connect
to FastAPI, PostgreSQL, or the web UI. It does **not** calculate worked time,
track location, or capture screen/keyboard content.

## Purpose

Run on an employee Windows PC and record session, power, and idle transitions
that later phases will turn into attendance. The agent is structured so it can
be hosted as a Windows background service later; it is **not** installed as a
service in this phase.

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

- Stable local `device_identifier` (UUID stored in `storage/device_identity.json`)
- Computer hostname (`device_name`)
- Operating system label
- Windows session username
- Event type, UTC timestamp, and small metadata (source, Win32 parameters, anomaly)

Idle metadata may include a rounded idle duration in seconds. It never includes
keystrokes or pointer coordinates.

## Data NOT collected

- Keystrokes or typed text
- Screenshots or screen video
- Mouse coordinates
- Webcam or microphone
- Browser history
- File contents
- Passwords or password hashes
- Chat or message content
- Location / GPS
- Application titles or URLs

## Idle detection

`GetLastInputInfo` is polled every `IDLE_POLL_INTERVAL_SECONDS` (default 5).
That poll is required: Windows does not raise an idle event. Session and power
changes use window messages, not polling.

Default idle threshold: **300 seconds**. After five minutes without keyboard or
mouse input, the agent records `IDLE_START`. When input resumes, it records
`IDLE_END`. While the session is locked, new idle-start events are not emitted.

## Privacy considerations

This component exists only to support attendance and working-time calculation.
Collect the minimum session facts listed above. Do not extend the agent into
productivity surveillance. Logs must not contain secrets. Device identity is a
random UUID, not a MAC address.

## Configuration

Copy `desktop-agent/.env.example` to `desktop-agent/.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `IDLE_THRESHOLD_SECONDS` | `300` | Seconds without input before `IDLE_START` |
| `IDLE_POLL_INTERVAL_SECONDS` | `5` | How often to read `GetLastInputInfo` |
| `LOG_LEVEL` | `INFO` | Diagnostic log level |
| `AGENT_MODE` | `live` | `live` (Windows APIs) or `test` (simulator) |
| `MIX_SIMULATED_AND_REAL` | `false` | If true in live mode, also emit the test scenario |
| `TEST_EVENT_DELAY_SECONDS` | `0.5` | Pause between simulated events |
| `DATA_DIR` / `LOG_DIR` | `storage/` | Identity file and rotating logs |

Simulated events are not mixed with live detectors unless
`MIX_SIMULATED_AND_REAL=true`.

## Running locally

```bash
cd desktop-agent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py --test --once
```

On Windows, live detection:

```text
python main.py
```

Expected console shape:

```text
WorkPulse Desktop Agent
Device: DESKTOP-TEST
Status: RUNNING

[09:00:01] WINDOWS_LOGIN
[13:05:20] SYSTEM_LOCK
[13:20:10] SYSTEM_UNLOCK
```

Rotating event log (`storage/logs/events.log`):

```text
2026-08-14T09:00:01Z WINDOWS_LOGIN
2026-08-14T13:05:20Z SYSTEM_LOCK
```

`pywin32` is installed only on Windows (`sys_platform == "win32"`). Live session
and power capture need Windows plus pywin32. Unit tests mock those APIs and run
on Linux.

## Test mode

```bash
python main.py --test
python main.py --test --once
python main.py --test --once --events WINDOWS_LOGIN SYSTEM_LOCK SYSTEM_UNLOCK
```

`--test` sets `AGENT_MODE=test` and records a scripted sequence through the same
`EventService` used by live detectors. `SYSTEM_LOGOUT` is accepted as an alias
of `WINDOWS_LOGOUT`.

```bash
cd desktop-agent
pytest
```

Windows-only integration checks are marked `skipif` when not running on Windows.
