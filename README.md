# WorkPulse

WorkPulse is a company-specific **employee attendance and timesheet management** system. It is an online web application with a Windows desktop agent for automatic attendance tracking.

This repository currently includes project foundation, the database schema, JWT authentication/RBAC, and employee/department/team management. Attendance tracking, timesheets, dashboards, reports, notifications, location tracking, and the desktop agent behavior are not implemented yet.

## Roles

Access is role-based. Attendance and timesheet scopes are reserved for later phases.

| Role | Current people-management scope |
| --- | --- |
| Employee | Own profile only |
| Team lead | Assigned team only |
| HR | Organization-wide employees, departments, and teams |
| Admin | Administrative employee-management operations when present |

## Technology stack

- **Frontend:** React, Vite, JavaScript, React Router, Axios
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Authentication:** JWT and Argon2id password hashing
- **Desktop agent (later):** Python, Windows-compatible, SQLite for local events
- **Deployment:** Docker, Docker Compose, Nginx, Ubuntu VPS

## Folder structure

```
.
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── api/             HTTP routers
│   │   ├── core/            Settings and logging
│   │   ├── models/          SQLAlchemy schema
│   │   ├── schemas/         Pydantic schemas
│   │   ├── services/        Business logic
│   │   ├── repositories/    Data access
│   │   ├── database/        Engine, session, declarative base
│   │   └── main.py
│   ├── alembic/             Alembic migrations
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                React + Vite SPA
├── desktop-agent/           Windows agent skeleton
├── database/                Optional SQL notes (schema via Alembic)
├── deployment/
│   ├── docker/              Backend and frontend Dockerfiles
│   └── nginx/               SPA + /api reverse proxy
├── docs/
├── docker-compose.yml
└── .env.example             Compose / deployment variables
```

## Architectural decisions

- **Layered backend:** routers → services → repositories → SQLAlchemy. The folders exist so later modules drop into a consistent place without a rewrite.
- **Settings from the environment:** `DATABASE_URL`, `SECRET_KEY`, and related values come from env vars / `.env`. Nothing secret is committed.
- **Alembic uses the app metadata:** `alembic/env.py` reads `DATABASE_URL` and `Base.metadata` so migrations stay aligned with models.
- **Health check is liveness-only:** `GET /api/health` returns `{"status":"ok"}` without querying PostgreSQL, so the API process can be probed independently of the database.
- **Frontend auth:** Login stores access/refresh tokens in `sessionStorage` and loads `/api/auth/me`. Route menus are role-based; authorization is enforced on the API.
- **Desktop agent is a skeleton:** entrypoint and folders only; it does not pretend to capture Windows events.
- **Compose credentials are required:** `docker compose up` expects a local `.env` (from `.env.example`). Postgres password and `DATABASE_URL` are not hard-coded in images.

## Environment variables

Copy examples before running locally. **Never commit `.env`.**

Backend (`backend/.env.example`):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME` |
| `SECRET_KEY` | Application secret used to sign JWTs |
| `JWT_ALGORITHM` | JWT signing algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime |
| `ENVIRONMENT` | `development`, `test`, or `production` |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API |
| `DEV_SEED_PASSWORD` | Optional local-only password for seeded login accounts |

Root `.env.example` additionally defines Compose values: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`.

For Docker, `DATABASE_URL` must use hostname `db` (the Compose service name), not `localhost`.

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (or Docker for the database only)
- Docker and Docker Compose (for the full stack)

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set DATABASE_URL and SECRET_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

Run tests:

```bash
cd backend
pytest
```

Apply the schema and optional development seed (from `backend/`):

```bash
alembic upgrade head
python scripts/seed_dev.py
```

`seed_dev.py` runs only when `ENVIRONMENT` is `development`, `dev`, or `local`. Login accounts are created only when `DEV_SEED_PASSWORD` is set. See [docs/database.md](docs/database.md) and [docs/authentication.md](docs/authentication.md).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at http://localhost:5173 and proxies `/api` to http://localhost:8000.

### 3. Docker

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD, DATABASE_URL, and SECRET_KEY
docker compose up --build
```

- API: http://localhost:8000/api/health
- Web UI: http://localhost/

`DATABASE_URL` in `.env` for Compose should look like:

```text
DATABASE_URL=postgresql+psycopg://workpulse:YOUR_PASSWORD@db:5432/workpulse
```

## Current API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Liveness. Returns `{"status":"ok"}`. |
| POST | `/api/auth/login` | Issue access and refresh tokens |
| POST | `/api/auth/refresh` | Rotate tokens |
| POST | `/api/auth/logout` | Revoke access and refresh tokens |
| GET | `/api/auth/me` | Current account, roles, and permissions |
| GET | `/api/employees` | Employees visible to the caller (search/filter query params) |
| POST | `/api/employees` | Create employee (HR / Admin) |
| GET | `/api/employees/me` | Authenticated employee profile |
| GET | `/api/employees/{employee_id}` | One employee if the caller is allowed to view them |
| PATCH | `/api/employees/{employee_id}` | Update employee (self: limited fields; HR / Admin: management fields) |
| POST | `/api/employees/{employee_id}/deactivate` | Deactivate employee (HR / Admin) |
| GET/POST | `/api/departments` | List / create departments |
| PATCH | `/api/departments/{department_id}` | Update department |
| GET/POST | `/api/teams` | List / create teams |
| GET/PATCH | `/api/teams/{team_id}` | Team details / update |
| GET | `/api/teams/{team_id}/members` | Team members visible to the caller |

Authentication is in [docs/authentication.md](docs/authentication.md). People management is in [docs/employee-management.md](docs/employee-management.md). Attendance and timesheet APIs are not implemented yet.
