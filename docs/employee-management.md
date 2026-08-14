# Employee, department, and team management

Phase 4 adds organization people management on top of Phase 3 authentication
and RBAC. Attendance capture, timesheets, dashboards, reports, and the Windows
desktop agent are not implemented here.

## Employee structure

Employees belong to one organization. Unique constraints are
`(organization_id, employee_code)` and `(organization_id, email)`.

| Field | Notes |
| --- | --- |
| Employee ID/code | Organization-unique business identifier (for example `EMP001`) |
| Name | `first_name`, `last_name` |
| Email | Organization-unique; also used as the login email when an account exists |
| Phone | Optional personal field employees may update on their own profile |
| Department | Optional; must belong to the same organization and be active |
| Team | Optional; must belong to the same organization and be active |
| Reporting Team Lead | `manager_id`; must be an active `TEAM_LEAD` or `ADMIN` in the same organization |
| Joining date | Optional |
| Employment status | `ACTIVE`, `INACTIVE`, `ON_LEAVE`, `TERMINATED` |
| Account status | Derived: `ACTIVE`, `INACTIVE`, or `NONE` if no login account |
| Created / updated | Timestamps from the employee row |

API responses never include passwords, password hashes, JWT secrets, or other
authentication secrets.

## Department structure

| Field | Notes |
| --- | --- |
| Name | Display name |
| Code | Unique within the organization |
| Description | Optional |
| Active | Inactive departments cannot be assigned to new employees |

## Team structure

| Field | Notes |
| --- | --- |
| Name | Unique within the organization |
| Department | Optional; must be in the same organization |
| Team lead | Optional; must be an active Team Lead or Admin in the same organization |
| Active | Inactive teams cannot be assigned to employees |

## Demo users (development only)

Seeded organization: **Finance Company - Development** (`FIN-DEV`).

Department: **Finance Operations** (`FINOPS`).

Team: **Finance Operations Team** (lead: Nayab Rasul).

| Code | Name | Role | Team |
| --- | --- | --- | --- |
| EMP001 | Israh Zunain | EMPLOYEE | Finance Operations Team |
| EMP002 | Sameer | EMPLOYEE | Finance Operations Team |
| EMP003 | Nayab Rasul | TEAM_LEAD | Finance Operations Team (team lead) |
| HR001 | Sidrah Hunain | HR | None |

These are development accounts. Login passwords come from `DEV_SEED_PASSWORD`.
Do not commit that value. Do not use production credentials here.

Development emails (not production mailboxes):

- `israh.zunain@workpulse.local`
- `sameer@workpulse.local`
- `nayab.rasul@workpulse.local`
- `sidrah.hunain@workpulse.local`

## Role permissions

Enforced in backend services. Frontend menus are convenience only.

| Role | Employee access |
| --- | --- |
| EMPLOYEE | Own profile only. May update phone and name. Cannot list the directory, change role, team, department, or employment status. |
| TEAM_LEAD | Own profile plus employees on assigned/led teams. Cannot create or deactivate employees. Cannot see other teams, HR-only records, or other organizations. |
| HR | Organization-wide create, view, update, deactivate, search, filter, assign department/team/lead. |
| ADMIN | Same employee-management operations as HR when present. |

Identity is taken from the access token (`sub` → account → employee). Path
`employee_id` values from the client are authorization targets, never the
caller’s identity.

## Data isolation

| Caller | Own profile | Teammate | Other team same org | Other organization |
| --- | --- | --- | --- | --- |
| Israh / Sameer | 200 | 403 | 403 | 404 |
| Nayab Rasul | 200 | 200 (Finance Operations Team) | 403 | 404 |
| Sidrah Hunain | 200 | 200 | 200 | 404 |

`GET /api/employees` for an EMPLOYEE returns only that employee (HTTP 200),
not the full directory.

## API endpoints

All routes below require a Bearer access token except where noted in
[authentication.md](authentication.md).

| Method | Path | Who |
| --- | --- | --- |
| GET | `/api/employees` | Visible employees; supports `search`, `department_id`, `team_id`, `employment_status`, `is_active` |
| POST | `/api/employees` | HR / Admin create |
| GET | `/api/employees/me` | Authenticated caller’s profile |
| GET | `/api/employees/{employee_id}` | If `can_view_employee` |
| PATCH | `/api/employees/{employee_id}` | Self (limited fields) or HR / Admin |
| POST | `/api/employees/{employee_id}/deactivate` | HR / Admin |
| GET | `/api/departments` | Own department, or HR / Admin (all in org) |
| POST | `/api/departments` | HR / Admin |
| PATCH | `/api/departments/{department_id}` | HR / Admin |
| GET | `/api/teams` | Assigned/led teams, or HR / Admin (all in org) |
| POST | `/api/teams` | HR / Admin |
| GET | `/api/teams/{team_id}` | If allowed to view the team |
| PATCH | `/api/teams/{team_id}` | HR / Admin |
| GET | `/api/teams/{team_id}/members` | Members the caller is allowed to view |

Validation errors use `400` with codes such as `invalid_department`,
`invalid_team`, `invalid_team_lead`, and `invalid_manager`. Duplicate employee
code or email uses `409`. Missing records in another organization use `404`.
Forbidden actions use `403`. Database exceptions are not returned to clients.

## Development seed process

From `backend/` with `ENVIRONMENT` set to `development`, `dev`, or `local`:

```bash
alembic upgrade head
# Set DEV_SEED_PASSWORD in backend/.env (never commit it)
python scripts/seed_dev.py
```

The seed is idempotent: re-running updates the same four people, one
organization, one finance department, and one finance team. It does not create
duplicate rows. Login accounts are created only when `DEV_SEED_PASSWORD` is set.
