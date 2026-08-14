# Windows desktop agent testing

Development/testing guide for running the WorkPulse agent on a **real Windows PC**.
Use demo account **EMP001 — Israh Zunain** only. Do not use production credentials.

This document is the source of truth for `WINDOWS_MANUAL_TEST` procedures.
Cursor’s Linux environment cannot generate Windows session events; those steps
must be executed on Windows.

## 1. Windows requirements

- Windows 10 or 11 (64-bit)
- A dedicated development machine or VM (not a production employee laptop)
- Local admin is **not** required for the default `%LOCALAPPDATA%\WorkPulse` paths
- Network access to the WorkPulse API (or HTTP to `127.0.0.1` with `ALLOW_INSECURE_HTTP=true`)

## 2. Python requirements

- Python 3.12+
- `pip install -r requirements.txt` from `desktop-agent/`
- `pywin32` installs only on Windows (`pywin32>=306`)

## 3. Installation

```powershell
cd desktop-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Do **not** run `register-dev-startup.ps1` unless you want a reversible current-user
Startup shortcut. There is no Windows Service in this phase.

## 4. Configuration

Edit `desktop-agent/.env` (never commit it):

| Variable | Development example |
| --- | --- |
| `API_BASE_URL` | `http://127.0.0.1:8000` (local) or `https://...` (server) |
| `ALLOW_INSECURE_HTTP` | `true` only for local HTTP |
| `SYNC_ENABLED` | `true` |
| `IDLE_THRESHOLD_SECONDS` | `300` (use `30` to speed up idle tests) |
| `SYNC_BATCH_SIZE` | `50` |
| `SYNC_MAX_BACKOFF_SECONDS` | `60` |
| `LOCAL_DATABASE_PATH` | leave empty to use `%LOCALAPPDATA%\WorkPulse\events.db` |
| `LOG_LEVEL` | `INFO` |
| `AGENT_EMAIL` | `israh.zunain@workpulse.local` |
| `AGENT_PASSWORD` | demo seed password from `DEV_SEED_PASSWORD` |

Production must use `https://` and `ALLOW_INSECURE_HTTP=false`.

## 5. Device enrollment

1. Start the FastAPI backend and apply migrations.
2. Confirm EMP001 can log in.
3. Start the agent with `AGENT_EMAIL` / `AGENT_PASSWORD` for EMP001.
4. The agent calls `POST /api/agent/devices/enroll` then stores the secret in
   `%LOCALAPPDATA%\WorkPulse\device_secret` (not in git, not in logs).
5. The server binds the device to EMP001. The agent cannot pick another employee id.

## 6. Running the agent

```powershell
python main.py
```

The process stays running until Ctrl+C or Windows session end. It does not exit
after the first event.

```powershell
python main.py --status
```

Status fields: agent RUNNING/STOPPED, device id, employee email, backend
CONNECTED/OFFLINE/DISABLED, pending count, last event, last successful sync.

## 6b. Login / logout (WINDOWS_MANUAL_TEST)

Verify `WINDOWS_LOGIN` and `WINDOWS_LOGOUT` against a real interactive session.

**Limitation:** if the agent starts **after** the user is already logged on,
Windows may not send `WTS_SESSION_LOGON` again. Do not synthesize a login
event. The first captured events may be lock/unlock or idle.

If you start the agent from a Startup shortcut **before** the desktop is
fully up, you may see `WINDOWS_LOGIN` when the session becomes interactive.
Sign-out should produce `WINDOWS_LOGOUT` via `WTS_SESSION_LOGOFF` or
`WM_ENDSESSION` with `ENDSESSION_LOGOFF`.

## 7. Lock/unlock test (WINDOWS_MANUAL_TEST)

1. `python main.py` — confirm Status RUNNING.
2. Win+L (lock).
3. Confirm `SYSTEM_LOCK` in the console and in SQLite (`sync_status` PENDING or SYNCED).
4. Unlock.
5. Confirm `SYSTEM_UNLOCK`.
6. If the API is up, wait for sync (or `python main.py --status`).
7. PostgreSQL `attendance_events` has one row per `client_event_id`.
8. `GET /api/attendance/me/{date}` as EMP001 — `total_locked_seconds` includes the lock interval.

Do not insert fake lock events for this test.

## 8. Idle test (WINDOWS_MANUAL_TEST)

1. Optionally set `IDLE_THRESHOLD_SECONDS=30`.
2. Start the agent, unlock, do not use keyboard/mouse.
3. Wait for the threshold — `IDLE_START`.
4. Move the mouse — `IDLE_END`.
5. Confirm SQLite, then sync, then attendance idle seconds.

The agent never stores keystrokes or mouse coordinates.

## 9. Offline test (WINDOWS_MANUAL_TEST)

1. Start the agent while online.
2. Disable the network adapter (or unplug).
3. Lock, unlock, and/or idle.
4. Events remain `PENDING`. The agent stays RUNNING.
5. Reconnect.
6. Sync retries with backoff; rows become `SYNCED`.
7. PostgreSQL has exactly one copy per `event_id`.

## 10. Restart recovery (WINDOWS_MANUAL_TEST)

**Application restart:** generate an event, stop the agent (Ctrl+C), start it again.
SQLite still has the row; pending items sync after authenticate.

**Windows restart:** reboot. After login, start `python main.py` (or the optional
Startup shortcut). PENDING events from before the reboot must still be present
and then sync.

## 11. Shutdown test (WINDOWS_MANUAL_TEST)

Shut down or restart Windows while the agent is running.

- `WM_QUERYENDSESSION` / `WM_ENDSESSION` should persist `SYSTEM_SHUTDOWN` or
  `SYSTEM_RESTART` (or `WINDOWS_LOGOUT` on logoff) to SQLite **before** the
  process exits.
- Network sync is **not** required to finish. Leftover rows stay PENDING and
  upload on the next start.
- Restart vs shutdown is best-effort; `WM_ENDSESSION` with no logoff/restart
  bits is stored as `SYSTEM_SHUTDOWN`. A pending Windows Update reboot is not
  used as evidence.

## 12. Troubleshooting

| Symptom | Check |
| --- | --- |
| Live mode exits immediately | Must run on Windows; use `--test` elsewhere |
| “Another WorkPulse agent is already running” | Only one instance; `python main.py --status` |
| Events stay PENDING | `API_BASE_URL`, `SYNC_ENABLED`, `python main.py --status` Backend |
| AUTH_ERROR | Re-enroll EMP001; device active |
| No lock events | Session notifications need an interactive user session |
| No idle events | `GetLastInputInfo`; threshold; session not locked |

## 13. Log locations (Windows)

`%LOCALAPPDATA%\WorkPulse\logs\agent.log` (rotating)
`%LOCALAPPDATA%\WorkPulse\logs\events.log`

Do not log passwords, device secrets, or JWTs.

## 14. SQLite location (Windows)

Default: `%LOCALAPPDATA%\WorkPulse\events.db`  
Also: `device_identity.json`, `device_secret`, `agent.lock`, `status.json`

## 15. Known Windows limitations

- If the agent starts **after** Windows logon, `WINDOWS_LOGIN` for that boot may
  be missing. The first event may be lock/unlock or idle. Documented; no fake login.
- Fast User Switching / remote desktop extra sessions are not fully modeled.
- Sleep/wake depend on `WM_POWERBROADCAST`; some devices skip messages.
- Restart vs shutdown: `WM_ENDSESSION` does not officially say which. The agent
  records `SYSTEM_SHUTDOWN` unless this message has `ENDSESSION_LOGOFF`
  (logout) or the undocumented restart bit. A pending Windows Update reboot
  (`RebootRequired`) is **not** treated as a restart — that key is often set
  for days and would mis-label Shut down.
- No Windows Service in this phase (development Startup shortcut is optional and reversible).
- Packaging: `workpulse-agent.spec` is a PyInstaller starting point; do not bundle `.env`.

## Automated tests

From `desktop-agent/`:

```powershell
pytest
```

- Unit/integration tests run on any OS.
- `WINDOWS_ONLY` tests run only on Windows (`GetLastInputInfo`, LocalAppData path).
- `WINDOWS_MANUAL_TEST` cases skip everywhere and point here.
