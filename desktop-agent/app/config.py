"""Environment-driven settings for the desktop agent."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AGENT_ROOT = Path(__file__).resolve().parents[1]


def default_user_data_dir() -> Path:
    """Per-user application data directory (no administrator rights required)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / "WorkPulse"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "WorkPulse"
    return Path.home() / ".local" / "share" / "WorkPulse"


class AgentSettings(BaseSettings):
    """Runtime configuration. Secrets are never required in this phase."""

    model_config = SettingsConfigDict(
        env_file=(AGENT_ROOT / ".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    IDLE_THRESHOLD_SECONDS: int = 300
    IDLE_POLL_INTERVAL_SECONDS: float = 5.0
    LOG_LEVEL: str = "INFO"
    AGENT_MODE: str = "live"
    MIX_SIMULATED_AND_REAL: bool = False
    DATA_DIR: Path = Field(default_factory=default_user_data_dir)
    LOG_DIR: Path | None = None
    LOCAL_DATABASE_PATH: Path | None = None
    LOCAL_EVENT_RETENTION_DAYS: int = 30
    LOG_MAX_BYTES: int = 1_048_576
    LOG_BACKUP_COUNT: int = 5
    TEST_EVENT_DELAY_SECONDS: float = 0.05

    @field_validator("LOG_DIR", "LOCAL_DATABASE_PATH", mode="before")
    @classmethod
    def empty_path_is_missing(cls, value: object) -> object:
        if value == "" or value is None:
            return None
        return value

    @field_validator("IDLE_THRESHOLD_SECONDS")
    @classmethod
    def idle_threshold_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("IDLE_THRESHOLD_SECONDS must be at least 1")
        return value

    @field_validator("IDLE_POLL_INTERVAL_SECONDS")
    @classmethod
    def poll_interval_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("IDLE_POLL_INTERVAL_SECONDS must be greater than 0")
        return value

    @field_validator("LOCAL_EVENT_RETENTION_DAYS")
    @classmethod
    def retention_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("LOCAL_EVENT_RETENTION_DAYS must be at least 1")
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def log_level_must_be_known(cls, value: str) -> str:
        level = value.strip().upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if level not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return level

    @field_validator("AGENT_MODE")
    @classmethod
    def agent_mode_must_be_known(cls, value: str) -> str:
        mode = value.strip().lower()
        if mode not in {"live", "test"}:
            raise ValueError("AGENT_MODE must be 'live' or 'test'")
        return mode

    @model_validator(mode="after")
    def fill_derived_paths(self) -> AgentSettings:
        if self.LOG_DIR is None:
            self.LOG_DIR = self.DATA_DIR / "logs"
        if self.LOCAL_DATABASE_PATH is None:
            self.LOCAL_DATABASE_PATH = self.DATA_DIR / "events.db"
        return self

    @property
    def is_test_mode(self) -> bool:
        return self.AGENT_MODE == "test"

    @property
    def device_identity_path(self) -> Path:
        return self.DATA_DIR / "device_identity.json"

    @property
    def events_log_path(self) -> Path:
        assert self.LOG_DIR is not None
        return self.LOG_DIR / "events.log"

    @property
    def local_database_path(self) -> Path:
        assert self.LOCAL_DATABASE_PATH is not None
        return self.LOCAL_DATABASE_PATH


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()


def load_settings(**overrides: object) -> AgentSettings:
    """Build settings without the process-wide cache (used by tests)."""
    return AgentSettings(**overrides)
