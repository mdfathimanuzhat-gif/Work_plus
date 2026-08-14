# WorkPulse

WorkPulse is a company-specific **employee attendance and timesheet management** system. It is an online web application with a Windows desktop agent for automatic attendance tracking.

This repository currently contains the **project foundation only**: application layout, configuration, health check, and Docker wiring. Attendance tracking, timesheets, dashboards, reports, notifications, location tracking, and the desktop agent behavior are not implemented yet.

## Roles (planned)

Access will be strictly role-based in later phases:

| Role | Scope |
| --- | --- |
| Employee | Own attendance, hours, timesheets, and history only |
| Team lead | Assigned team only; review/approve/reject team timesheets |
| HR | Organization-wide employees, departments, teams, attendance, timesheets, reports, and access |

## Technology stack

- **Frontend:** React, Vite, JavaScript, React Router, Axios
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Authentication (later):** JWT and secure password hashing
- **Desktop agent (later):** Python, Windows-compatible, SQLite for local events
- **Deployment:** Docker, Docker Compose, Nginx, Ubuntu VPS

## Folder structure

```
.
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── api/             HTTP routers (health only for now)
│   │   ├── core/            Settings and logging
│   │   ├── models/          SQLAlchemy schema (Phase 2)
│   │   ├── schemas/         Pydantic schemas (later)
│   │   ├── services/        Business logic (later)
│   │   ├── repositories/    Data access (later)
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
- **Frontend auth is a placeholder:** React Router and a `ProtectedRoute` wrapper are in place; JWT login is not implemented and the guard does not fake a session.
- **Desktop agent is a skeleton:** entrypoint and folders only; it does not pretend to capture Windows events.
- **Compose credentials are required:** `docker compose up` expects a local `.env` (from `.env.example`). Postgres password and `DATABASE_URL` are not hard-coded in images.

## Environment variables

Copy examples before running locally. **Never commit `.env`.**

Backend (`backend/.env.example`):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME` |
| `SECRET_KEY` | Application secret (JWT will use this later) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (used when auth is added) |
| `ENVIRONMENT` | `development`, `test`, or `production` |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API |

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

`seed_dev.py` runs only when `ENVIRONMENT` is `development`, `dev`, or `local`. It does not store passwords. See [docs/database.md](docs/database.md).

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

No business endpoints are implemented in this phase.

Database schema, migrations, and seed data are documented in [docs/database.md](docs/database.md).
