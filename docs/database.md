# WorkPulse database

Phase 2 defines the PostgreSQL schema only. Authentication, attendance capture, timesheet workflows, dashboards, notifications, location tracking, and reports are not implemented yet.

The schema is built so those features can enforce:

- **Employee** — own records (`employees.id`, plus child rows keyed by `employee_id`)
- **Team lead** — assigned team (`teams.team_lead_id` and `employees.team_id`)
- **HR / Admin** — organization scope (`organization_id` on people and structure tables, plus `roles` / `permissions`)

Permissions live in tables (`roles`, `permissions`, `role_permissions`, `employee_roles`). Application code must not hard-code which role may perform which action.

## Overview

- Engine: PostgreSQL 16
- ORM: SQLAlchemy 2.x (`Mapped` / `mapped_column`)
- Migrations: Alembic
- Connection: `DATABASE_URL` from the environment (never hard-coded)
- Primary keys: UUID
- Timestamps: timezone-aware `timestamptz`

## Tables

| Table | Purpose |
| --- | --- |
| `organizations` | Company / tenant |
| `departments` | Departments inside an organization |
| `teams` | Teams; optional department; optional team lead |
| `employees` | People; required organization; optional department, team, manager |
| `roles` | Named roles (`ADMIN`, `HR`, `TEAM_LEAD`, `EMPLOYEE` in seed data) |
| `permissions` | Named permissions assigned to roles |
| `role_permissions` | Role ↔ permission many-to-many |
| `employee_roles` | Employee ↔ role assignment |
| `devices` | Registered endpoints for an employee |
| `attendance` | One daily attendance summary per employee |
| `attendance_events` | Fine-grained device/session events |
| `timesheets` | Employee time entries |
| `timesheet_approvals` | Review history for a timesheet |
| `locations` | Location snapshots (capture later) |
| `notifications` | In-app notifications (delivery later) |
| `audit_logs` | Organization audit trail |
| `user_accounts` | Login accounts (email + password hash) linked 1:1 to employees |
| `refresh_tokens` | Hashed refresh tokens for rotation and logout |
| `revoked_access_tokens` | Access-token `jti` denylist used at logout |

## Relationships

```
Organization 1──* Department 1──* Team 1──* Employee
Organization 1──* Team
Organization 1──* Employee
Organization 1──* AuditLog

Employee 1──1 UserAccount 1──* RefreshToken / RevokedAccessToken
Role     *──* Permission           (via role_permissions)

Employee 1──* Device
Employee 1──* Attendance 1──* AttendanceEvent
Employee 1──* AttendanceEvent
Employee 1──* Timesheet 1──* TimesheetApproval
Employee 1──* Location
Employee 1──* Notification
Employee 1──* AuditLog             (as actor, user_id)

Team.team_lead_id ──> Employee     (optional, SET NULL)
Employee.manager_id ──> Employee   (optional self-FK, SET NULL)
Device <── AttendanceEvent, Location
```

## ASCII ER diagram

```
+------------------+       +------------------+       +------------------+
| organizations    |       | departments      |       | teams            |
|------------------|       |------------------|       |------------------|
| id PK            |<------| organization_id  |       | id PK            |
| name             |       | id PK            |<------| department_id    |
| code UQ          |       | name             |       | organization_id  |
| email            |       | code             |       | name             |
| phone            |       | description      |       | team_lead_id --------+
| address          |       | is_active        |       | is_active        |   |
| timezone         |       +------------------+       +--------+---------+   |
| is_active        |                                           |             |
+--------+---------+                                           |             |
         |                                                     |             |
         |         +-------------------------------------------+             |
         |         |                                                         |
         v         v                                                         |
+------------------+       +------------------+       +------------------+   |
| employees        |       | employee_roles   |       | roles            |   |
|------------------|       |------------------|       |------------------|   |
| id PK            |<------| employee_id      |------>| id PK            |   |
| organization_id  |       | role_id          |       | name UQ          |   |
| employee_code    |       +------------------+       +--------+---------+   |
| first_name       |                                           |             |
| last_name        |       +------------------+                |             |
| email            |       | role_permissions |<---------------+             |
| department_id    |       |------------------|                              |
| team_id          |       | role_id          |       +------------------+   |
| manager_id ------|--+    | permission_id    |------>| permissions      |   |
| joining_date     |  |    +------------------+       |------------------|   |
| employment_status|  |                               | id PK            |   |
| is_active        |  |                               | name UQ          |   |
+--------+---------+  |                               +------------------+   |
         |            |                                                      |
         |            +-- self (manager / direct reports)                    |
         |                                                                   |
         +-- team_lead_id (from teams) <-------------------------------------+
         |
         +--* devices
         +--* attendance ----* attendance_events
         +--* attendance_events
         +--* timesheets ----* timesheet_approvals
         +--* locations
         +--* notifications
         +--* audit_logs
```

## Important constraints

| Rule | Implementation |
| --- | --- |
| Employee code unique per organization | `uq_employees_organization_id_employee_code` |
| Employee email unique per organization | `uq_employees_organization_id_email` |
| Organization code unique | `organizations.code` unique |
| Department code unique per organization | `uq_departments_organization_id_code` |
| Team name unique per organization | `uq_teams_organization_id_name` |
| One attendance row per employee per date | `uq_attendance_employee_id_attendance_date` |
| One timesheet row per employee/date/project/task | `uq_timesheets_employee_id_date_project_task` |
| Device identifier unique | `devices.device_identifier` unique |
| Agent event UUID unique | `attendance_events.client_event_id` unique |
| Device secret hash unique | `devices.secret_hash` unique (nullable until enrolled) |
| Role / permission names unique | `roles.name`, `permissions.name` |
| Non-negative duration and hours | check constraints on attendance seconds and timesheet hours |
| Employee requires an organization | `employees.organization_id` NOT NULL |
| Circular team-lead FK | `teams.team_lead_id` uses `use_alter` so employees can exist before the lead is assigned |

## Indexes

Unique constraints already provide supporting indexes. Additional indexes:

- `employees.organization_id`, `department_id`, `team_id`, `employee_code`, `email`
- `attendance.employee_id`, `attendance.attendance_date`
- `attendance_events.employee_id`, `attendance_events.event_time`
- `attendance_events.employee_id + event_time`, `attendance_events.device_id + event_time`
- `timesheets.employee_id`, `timesheets.date`, `timesheets.status`
- `devices.employee_id`
- `audit_logs.user_id`, `audit_logs.created_at`
- Foreign keys used for team lead, manager, and common joins

## Enums

| Enum | Values |
| --- | --- |
| `employment_status` | ACTIVE, INACTIVE, ON_LEAVE, TERMINATED |
| `attendance_status` | PRESENT, ABSENT, HALF_DAY, ON_LEAVE, HOLIDAY, INCOMPLETE |
| `attendance_event_type` | LOGIN, LOGOUT, LOCK, UNLOCK, SHUTDOWN, RESTART, SLEEP, WAKE, IDLE_START, IDLE_END |
| `timesheet_status` | DRAFT, SUBMITTED, APPROVED, REJECTED |
| `timesheet_approval_status` | PENDING, APPROVED, REJECTED |
| `location_type` | GPS, IP, MANUAL, UNKNOWN |
| `notification_type` | SYSTEM, ATTENDANCE, TIMESHEET, APPROVAL |

## Migration commands

From `backend/` with `DATABASE_URL` set:

```bash
# Apply all migrations
alembic upgrade head

# Show current revision
alembic current

# Generate a new revision after model changes (review the file before committing)
alembic revision --autogenerate -m "describe the change"

# Roll back one revision
alembic downgrade -1
```

Do not apply schema changes by editing PostgreSQL by hand.

## Seed command (local development only)

```bash
cd backend
# ENVIRONMENT must be development (or dev / local)
python scripts/seed_dev.py
```

The script refuses to run when `ENVIRONMENT` is not a development value. It does
not store passwords. Login hashes are created only when `DEV_SEED_PASSWORD` is
set. Development placeholders:

- Organization `FIN-DEV` — Finance Company - Development
- Department Finance Operations (`FINOPS`) / Finance Operations Team
- HR `sidrah.hunain@workpulse.local` (`HR001`)
- Team lead `nayab.rasul@workpulse.local` (`EMP003`)
- Employees `israh.zunain@workpulse.local` (`EMP001`), `sameer@workpulse.local` (`EMP002`)

See [employee-management.md](employee-management.md).

## Tests

```bash
cd backend
pytest
```

Schema tests run Alembic against `TEST_DATABASE_URL` when set, otherwise `postgresql+psycopg://workpulse:workpulse@127.0.0.1:5432/workpulse_test`. They do not use the developer `DATABASE_URL` from `.env`.
