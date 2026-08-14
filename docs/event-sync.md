# WorkPulse desktop agent ↔ server event sync

Phase 5C uploads locally stored attendance events from the Windows desktop
agent to FastAPI, which writes them to PostgreSQL. Attendance totals,
timesheets, and dashboards are not calculated here.

## Architecture

```text
Desktop Agent
      ↓
SQLite
      ↓
Sync Service
      ↓
HTTPS
      ↓
FastAPI
      ↓
PostgreSQL
```

Detectors never call the API. They write to SQLite (`PENDING`). A background
sync service reads batches of pending rows, authenticates as the device, and
posts them to `POST /api/agent/events/batch`.

## API endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/agent/devices/enroll` | Employee access JWT | Register this PC to the logged-in employee; returns a device secret once |
| POST | `/api/agent/auth/token` | Device identifier + secret | Issue a device JWT (`typ=device`) |
| POST | `/api/agent/events/batch` | Device JWT | Ingest a batch of events |

Employee access tokens are rejected on the ingest endpoint. Device tokens are
rejected on employee APIs.

## Authentication

Secrets are not stored in source code.

1. First run (optional bootstrap): the agent uses `AGENT_EMAIL` / `AGENT_PASSWORD`
   from the environment to log in as the employee and enroll the device.
2. The server stores only `devices.secret_hash` (SHA-256). The plaintext secret
   is written to `{DATA_DIR}/device_secret` (mode 0600) or can be supplied as
   `DEVICE_SECRET`.
3. Each sync cycle exchanges identifier + secret for a short-lived device JWT
   (`DEVICE_TOKEN_EXPIRE_MINUTES`, default 60).
4. Ingest uses that JWT. `employee_id`, `organization_id`, and `team_id` on the
   payload are ignored (and extra fields are rejected). Identity comes from the
   token and the `devices` row.

A device cannot submit events for another employee: the server always stores
`AttendanceEvent.employee_id` from the authenticated device’s employee.

## Batch processing

The agent loads at most `SYNC_BATCH_SIZE` pending rows (default 50). 200 pending
events become four requests. Events are ordered by `event_timestamp`, then local id.

The server rejects batches larger than `AGENT_EVENT_MAX_BATCH` (default 100).

## Idempotency

Each local event has `event_id` (UUID). PostgreSQL stores it as
`attendance_events.client_event_id` with a **unique constraint**.

| First delivery | Insert row, status `accepted` |
| Retry of the same UUID | No second row, status `duplicate` / `already_processed` |

The agent treats both `accepted` and `duplicate` as `SYNCED`. HTTP 409 is also
treated as synchronized.

## Retry strategy

Temporary failures (network timeout, 429, 500, 502, 503, 504) leave rows
`PENDING` (after reverting `SYNCING`). Backoff waits:

| Attempt | Delay |
| --- | --- |
| 1 | 5 seconds |
| 2 | 15 seconds |
| 3 | 30 seconds |
| 4+ | 60 seconds (capped by `SYNC_MAX_BACKOFF_SECONDS`) |

Connectivity is tested by calling `GET /api/health`, not by OS “internet connected”
flags. Event detection continues on a separate path while sync waits.

| HTTP | Agent behavior |
| --- | --- |
| 401 / 403 | Keep `PENDING`. Do not retry rapidly (`AUTH_ERROR`, long backoff). |
| 400 / 422 | Mark the batch `FAILED` and log the reason (invalid payload). |
| 409 | Treat as `SYNCED`. |
| 429, 5xx, timeout | Revert to `PENDING` and backoff. |

## Offline behavior

1. Events are always inserted into SQLite first.
2. If the API is unreachable, they stay `PENDING`.
3. When the API is reachable again, the sync loop uploads them automatically.
4. `event_timestamp` remains the original UTC capture time, not the upload time.

Delayed offline events are accepted if they are not older than
`AGENT_EVENT_MAX_AGE_DAYS` (default 400) and not more than
`AGENT_EVENT_MAX_FUTURE_SECONDS` (default 7200) in the future.

## Event type mapping

Local agent names are mapped to the existing PostgreSQL enum:

| Agent | Server (`attendance_event_type`) |
| --- | --- |
| WINDOWS_LOGIN | LOGIN |
| WINDOWS_LOGOUT | LOGOUT |
| SYSTEM_LOCK | LOCK |
| SYSTEM_UNLOCK | UNLOCK |
| SYSTEM_SHUTDOWN | SHUTDOWN |
| SYSTEM_RESTART | RESTART |
| SYSTEM_SLEEP | SLEEP |
| SYSTEM_WAKE | WAKE |
| IDLE_START | IDLE_START |
| IDLE_END | IDLE_END |

## Security

- Production must use `API_BASE_URL=https://...`. HTTP is allowed only when
  `ALLOW_INSECURE_HTTP=true` (local development).
- The device must be active and tied to an active employee in the same
  organization as the token.
- Incoming `device_id` / `device_identifier` must match the authenticated device.
- Credentials, device secrets, and JWTs are not written to application logs.

## Observability

Agent logs include pending counts and status (`OFFLINE`, `CONNECTED`, `AUTH_ERROR`)
plus accepted / duplicate / failed totals after each batch.

Server ingest logs: device identifier, employee id, accepted / duplicate / failed
counts. No secrets.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Events stay PENDING | `API_BASE_URL`, network, `SYNC_ENABLED=true`, `GET /api/health` |
| AUTH_ERROR | Enroll again; confirm `device_secret`; device `is_active` |
| FAILED rows | Invalid event type/id; inspect agent error logs |
| Duplicate already_processed | Normal retry; PostgreSQL unique on `client_event_id` |
| HTTP refused | Set `ALLOW_INSECURE_HTTP=true` only for local HTTP |
