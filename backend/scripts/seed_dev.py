"""Load development seed data. Refuses to run outside development."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.database.seed import seed_development_data  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402


def main() -> int:
    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)
    logger = logging.getLogger("seed_dev")

    if settings.ENVIRONMENT.lower() not in {"development", "dev", "local"}:
        logger.error(
            "Refusing to seed: ENVIRONMENT=%s (development only)",
            settings.ENVIRONMENT,
        )
        return 1

    session = SessionLocal()
    try:
        organization = seed_development_data(session)
        session.commit()
        logger.info("Seed complete for organization code=%s id=%s", organization.code, organization.id)
        return 0
    except Exception:
        session.rollback()
        logger.exception("Seed failed")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
