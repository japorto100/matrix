"""Auto-run Alembic migrations on agent service startup.

Activated via AGENT_AUTO_MIGRATE=true (default: true in dev, false in prod).
Runs `alembic upgrade head` against HINDSIGHT_DB_URL before the service accepts requests.

Idempotent: Alembic tracks applied revisions in `alembic_version` table.
Safe to run on every startup.

When AUDIT_DB_URL or HINDSIGHT_DB_URL is not set → no-op (uses JSONL fallback).
When AGENT_AUTO_MIGRATE=false → no-op (operator runs migrations manually).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_migrations_if_enabled() -> None:
    """Run alembic upgrade head on startup. Non-fatal on error."""
    if os.environ.get("AGENT_AUTO_MIGRATE", "true").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        logger.info("Auto-migrations disabled (AGENT_AUTO_MIGRATE=false)")
        return

    db_url = os.environ.get("AUDIT_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        logger.info("Auto-migrations skipped: no DB URL configured (JSONL fallback)")
        return

    try:
        from alembic.config import Config

        from alembic import command

        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        if not alembic_ini.exists():
            logger.warning(
                "alembic.ini not found at %s — skipping auto-migrate", alembic_ini
            )
            return

        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", db_url)

        logger.info("Running alembic upgrade head on %s", db_url.split("@")[-1])
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied successfully")

    except Exception as e:
        # Non-fatal: service should still start if migrations fail
        # (e.g. Postgres not reachable yet, will retry on next start)
        logger.warning("Alembic auto-migration failed: %s", e)
