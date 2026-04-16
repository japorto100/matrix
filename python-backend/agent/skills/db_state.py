"""User skill enable/disable overrides — `agent.user_skill_preferences` (exec-skills).

Cutover from legacy `agent.skills_state` to `agent.user_skill_preferences`
(Migration 014). Shared by `agent.skills.finder` and `agent.control.skills`.
"""

from __future__ import annotations

import logging
import os

import psycopg

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def load_skill_toggle_overrides(user_id: str) -> dict[str, bool]:
    """Return {tier:name: enabled} from agent.user_skill_preferences.

    Joins with agent.agent_skills to resolve skill_id UUID → tier:name key
    used by finder.filter_disabled_skills.
    Falls back to legacy agent.skills_state if user_skill_preferences is empty
    (transition period).
    """
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            # Primary: user_skill_preferences (014+)
            rows = conn.execute(
                """
                SELECT s.tier || ':' || s.name AS skill_key,
                       NOT p.disabled           AS enabled
                FROM agent.user_skill_preferences p
                JOIN agent.agent_skills s ON s.id = p.skill_id
                WHERE p.user_id = %s
                """,
                (user_id,),
            ).fetchall()
            if rows:
                return {row[0]: bool(row[1]) for row in rows}

            # Fallback: legacy skills_state (008)
            legacy = conn.execute(
                "SELECT skill_id, enabled FROM agent.skills_state WHERE user_id = %s",
                (user_id,),
            ).fetchall()
            if legacy:
                return {row[0]: bool(row[1]) for row in legacy}
    except Exception as e:  # noqa: BLE001
        logger.debug("skill_toggle_overrides: %s", e)
    return {}
