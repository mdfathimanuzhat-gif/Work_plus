"""Test configuration. Settings are provided via environment variables."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://workpulse:workpulse@127.0.0.1:5432/workpulse_test",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("ENVIRONMENT", "test")
