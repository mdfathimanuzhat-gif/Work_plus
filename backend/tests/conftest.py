"""Test configuration. Settings are provided via environment variables."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://workpulse:workpulse@127.0.0.1:5432/workpulse_test",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEV_SEED_PASSWORD", "TestPassw0rd!")

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def migrated_database() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
