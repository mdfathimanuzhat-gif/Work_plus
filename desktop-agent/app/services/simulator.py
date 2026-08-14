"""Development simulator. Does not mix with live detectors unless configured."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence

from app.models import EventType, parse_event_type

logger = logging.getLogger("workpulse.agent.simulator")

RecordFn = Callable[..., object]

DEFAULT_SCENARIO: tuple[str, ...] = (
    "WINDOWS_LOGIN",
    "SYSTEM_LOCK",
    "SYSTEM_UNLOCK",
    "IDLE_START",
    "IDLE_END",
    "SYSTEM_LOGOUT",
    "SYSTEM_SHUTDOWN",
    "SYSTEM_RESTART",
)


def simulate_events(
    record: RecordFn,
    sequence: Sequence[str] | None = None,
    *,
    delay_seconds: float = 0.0,
) -> list[EventType]:
    """Emit a scripted sequence of events through the same EventService path."""
    names = list(sequence) if sequence is not None else list(DEFAULT_SCENARIO)
    emitted: list[EventType] = []
    for name in names:
        event_type = parse_event_type(name)
        try:
            record(event_type, metadata={"simulated": True}, source="test_mode")
            emitted.append(event_type)
        except Exception:
            logger.exception("Simulator failed to record %s", event_type.value)
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    return emitted
