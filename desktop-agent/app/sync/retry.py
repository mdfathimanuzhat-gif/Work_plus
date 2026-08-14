"""Exponential backoff for temporary sync failures."""

from __future__ import annotations

DEFAULT_DELAYS: tuple[int, ...] = (5, 15, 30, 60)


def backoff_seconds(attempt: int, *, delays: tuple[int, ...] = DEFAULT_DELAYS, max_delay: int = 60) -> int:
    """Return the wait after a failed attempt (1-based)."""
    if attempt < 1:
        return 0
    if attempt <= len(delays):
        return min(delays[attempt - 1], max_delay)
    return max_delay
