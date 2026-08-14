"""WINDOWS_ONLY automated checks. Skipped on Linux/macOS. Do not fake Win32 results."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.config import default_user_data_dir

pytestmark = pytest.mark.windows

requires_windows = pytest.mark.skipif(sys.platform != "win32", reason="WINDOWS_ONLY")


@requires_windows
def test_idle_clock_returns_non_negative_seconds() -> None:
    from app.detectors.idle_detector import WindowsIdleClock

    seconds = WindowsIdleClock().idle_seconds()
    assert seconds >= 0


@requires_windows
def test_default_data_dir_is_localappdata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Demo\AppData\Local")
    path = default_user_data_dir()
    assert path == Path(r"C:\Users\Demo\AppData\Local\WorkPulse")
