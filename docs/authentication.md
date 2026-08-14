# WorkPulse authentication and RBAC

Phase 3 adds login, JWT access/refresh tokens, password hashing, and
server-side data isolation. Attendance, timesheets, dashboards, notifications,
location tracking, and reports are not implemented here.

## Authentication flow

```
Client                     API                         PostgreSQL
  |                         |                               |
  | POST /api/auth/login    |                               |
  | {email, password}       |                               |
  |------------------------>| lookup account by email       |
  |                         |------------------------------>|
  |                         | verify Argon2 hash            |
  |                         | reject inactive accounts      |
  |                         | issue access + refresh JWT    |
  |                         | persist hashed refresh token  |
  |<------------------------|                               |
  | Authorization: Bearer   |                               |
  | GET /api/auth/me        | decode JWT, check denylist    |
  |------------------------>| load roles/permissions        |
  |                         |------------------------------>|
  |<------------------------|                               |
  | POST /api/auth/refresh  | rotate refresh token          |
  | POST /api/auth/logout   | revoke access jti + refresh   |
```

1. The client sends email and password. The API never confirms whether the email exists.
2. On success it returns a short-lived **access token** and a longer-lived **refresh token**.
3. Protected routes send `Authorization: Bearer <access_token>`.
4. When the access token expires, `POST /api/auth/refresh` returns a new pair and revokes the old refresh token.
5. Logout revokes the current access token `jti` and the refresh token so both stop working immediately.

## JWT

| Token | Lifetime (defaults) | `typ` claim | Stored server-side |
| --- | --- | --- | --- |
| Access | `ACCESS_TOKEN_EXPIRE_MINUTES` (30) | `access` | Only if revoked (`revoked_access_tokens`) |
| Refresh | `REFRESH_TOKEN_EXPIRE_DAYS` (7) | `refresh` | SHA-256 hash in `refresh_tokens` |

Payload (no email, name, or other profile data):

- `sub` — account ID
- `employee_id`
- `organization_id`
- `role` — primary role (`ADMIN` > `HR` > `TEAM_LEAD` > `EMPLOYEE`)
- `roles` — all assigned role names
- `jti`, `iat`, `exp`, `typ`

Signed with `SECRET_KEY` using `JWT_ALGORITHM` (HS256). Both come from the environment.

## Password security

- Hashed with **Argon2id** (`argon2-cffi`). Plain-text passwords are never stored.
- Minimum 10 characters, at least one letter and one number (enforced when creating accounts).
- Inactive account or employee, unknown email, and wrong password all return the same `401 invalid_credentials`.
- Failed login does not log the email or password.

Rate limiting is **not implemented yet**. Deployments should add an IP/account throttle at the reverse proxy (for example Nginx `limit_req`) before production exposure of `/api/auth/login` and `/api/auth/refresh`.

## Roles and permissions

Roles and permissions remain database rows from Phase 2 (`roles`, `permissions`, `role_permissions`, `employee_roles`). Authorization dependencies load them on each request; they are not hard-coded in route handlers.

| Role | Typical access |
| --- | --- |
| EMPLOYEE | Own employee record (`employee.view_own`) |
| TEAM_LEAD | Own team (`employee.view_team` plus `teams.team_lead_id` / `employees.team_id`) |
| HR | Organization employees (`employee.manage_organization`) |
| ADMIN | Same organization-wide employee permissions as seeded for ADMIN |

Reusable FastAPI dependencies:

- `require_authenticated_user`
- `require_role_dep(...)`
- `require_permission_dep(...)`

Resource checks go through `app.services.authorization` (`can_view_employee`, `ensure_can_view_employee`). Path IDs from the client are never trusted as identity.

## Data isolation

`GET /api/employees/{employee_id}` and `GET /api/employees`:

- Identity comes from the access token, then the database account/employee row.
- EMPLOYEE: only `employee_id == current user`. Changing the URL to another employee returns **403**.
- TEAM_LEAD: employees on the assigned team (`team_id` or teams they lead). Other teams return **403**.
- HR / ADMIN: employees in the same organization.
- Other organizations return **404** (not enumerated).

## API endpoints

| Method | Path | Auth | Success |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | No | `{access_token, refresh_token, token_type, expires_in}` |
| POST | `/api/auth/refresh` | Refresh body | New token pair |
| POST | `/api/auth/logout` | Optional bearer + refresh body | `{message: "Logged out"}` |
| GET | `/api/auth/me` | Access token | Account + employee summary, roles, permissions |
| GET | `/api/employees` | Access token | Employees visible to the caller |
| GET | `/api/employees/me` | Access token | Authenticated employee profile |
| GET | `/api/employees/{employee_id}` | Access token | One employee if allowed |

Employee create/update, departments, and teams are documented in
[employee-management.md](employee-management.md).

Errors:

```json
{"error": {"code": "invalid_credentials", "message": "Invalid email or password"}}
```

Password hashes are never returned. Validation errors use `validation_error` and strip password inputs.

## Accounts

Table `user_accounts` (added in this phase):

- `email` (login, unique)
- `password_hash`
- `employee_id` (one account per employee)
- `is_active`, `last_login_at`, timestamps

Employee profile fields stay on `employees`.

Local seed creates accounts only when `DEV_SEED_PASSWORD` is set in the environment. That password is for development and must not be used in production.

## Environment variables

```
SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173
DEV_SEED_PASSWORD=
```

In `ENVIRONMENT=production`, `CORS_ORIGINS` must be an explicit allowlist (no `*`).

## Security notes

- Do not put secrets in source control.
- Do not log tokens, password hashes, or credentials.
- Access tokens remain valid until expiry unless logout adds their `jti` to the denylist; keep access lifetime short.
- Refresh tokens are rotated and stored only as hashes.
