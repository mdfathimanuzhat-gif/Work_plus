"""Test configuration. Settings are provided via environment variables."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://workpulse:workpulse@localhost:5432/workpulse",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("ENVIRONMENT", "test")
