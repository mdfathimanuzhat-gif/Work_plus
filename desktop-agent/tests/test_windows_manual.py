"""WINDOWS_MANUAL_TEST procedures.

These tests never pass or fail a real lock/unlock on this runner. Cursor's Linux
environment cannot generate Windows session events. Run the matching steps in
docs/windows-testing.md on a Windows PC enrolled as EMP001 (Israh Zunain).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_manual


def test_real_windows_lock_unlock() -> None:
    pytest.skip("WINDOWS_MANUAL_TEST: lock/unlock on a Windows PC. See docs/windows-testing.md")


def test_real_windows_login_logout() -> None:
    pytest.skip("WINDOWS_MANUAL_TEST: login/logout session lifecycle. See docs/windows-testing.md")


def test_real_windows_idle_detection() -> None:
    pytest.skip("WINDOWS_MANUAL_TEST: idle threshold on a Windows PC. See docs/windows-testing.md")


def test_windows_restart_recovery() -> None:
    pytest.skip("WINDOWS_MANUAL_TEST: reboot the Windows PC. See docs/windows-testing.md")


def test_windows_shutdown_persists_locally() -> None:
    pytest.skip("WINDOWS_MANUAL_TEST: shutdown/restart notifications. See docs/windows-testing.md")


def test_offline_then_online_on_windows() -> None:
    pytest.skip("WINDOWS_MANUAL_TEST: disconnect NIC, generate events, reconnect. See docs/windows-testing.md")
