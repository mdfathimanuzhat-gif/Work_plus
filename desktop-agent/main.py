"""WorkPulse Windows desktop agent.

Local system-event detection, SQLite queue, and optional API synchronization.

Usage:
    python main.py              # live detectors (Windows)
    python main.py --test       # simulate events (any OS)
    python main.py --test --once
    python main.py --test --once --sync-once
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import run_agent  # noqa: E402
from app.config import load_settings  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkPulse desktop agent (local events)")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Simulate attendance events without using live Windows APIs",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="In test mode, emit the scenario and exit (for automated checks)",
    )
    parser.add_argument(
        "--events",
        nargs="+",
        help="Optional test-mode event names, for example WINDOWS_LOGIN SYSTEM_LOCK",
    )
    parser.add_argument(
        "--sync-once",
        action="store_true",
        help="After recording events, upload pending SQLite rows once",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    overrides: dict[str, object] = {}
    if args.test:
        overrides["AGENT_MODE"] = "test"
    settings = load_settings(**overrides)
    return run_agent(settings, once=args.once, sequence=args.events, sync_once=args.sync_once)


if __name__ == "__main__":
    raise SystemExit(main())
