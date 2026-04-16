"""PostgreSQL-backed skill store (`agent.agent_skills`).

Used by loader/seed scripts while the runtime transitions from filesystem-only
global skills to DB-backed skills (exec-skills + exec-18).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import psycopg

from agent.skills.loader import Skill

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def _row_to_skill(row: dict[str, Any]) -> Skill:
    name = str(row["name"])
    tier = str(row.get("tier") or "global")
    skill_type_raw = str(row.get("skill_type") or "task_specific")
    return Skill(
        name=name,
        description=str(row.get("description") or ""),
        category=str(row.get("category") or "general"),
        content=str(row.get("content") or ""),
        path=Path(f"db://agent_skills/{name}"),
        tier=tier if tier in {"global", "team", "personal"} else "global",
        owner=row.get("owner_id"),
        generation=int(row.get("generation") or 0),
        enabled=bool(row.get("enabled", True)),
        db_id=str(row["id"]),
        skill_type=skill_type_raw if skill_type_raw in ("general", "task_specific") else "task_specific",
        api_version=row.get("api_version"),
        assets=row.get("assets") or {},
    )


def fetch_enabled_skills(
    *,
    tiers: tuple[str, ...] = ("global",),
    category: str | None = None,
) -> list[Skill]:
    """Fetch enabled skills from `agent.agent_skills`; empty list on failure."""
    sql = """
        SELECT id, name, description, category, content, tier, owner_id,
               generation, enabled, skill_type, api_version, assets
        FROM agent.agent_skills
        WHERE enabled = true
          AND tier = ANY(%s)
    """
    params: list[Any] = [list(tiers)]
    if category:
        sql += " AND category = %s"
        params.append(category)
    sql += " ORDER BY name ASC"

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                rows = cur.execute(sql, params).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.debug("fetch_enabled_skills failed: %s", e)
        return []

    return [_row_to_skill(row) for row in rows]


def increment_usage_counts(skill_db_ids: list[str]) -> None:
    """Bump usage_count by 1 for each db_id. Best-effort, no raise."""
    ids = [x for x in skill_db_ids if x]
    if not ids:
        return
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                UPDATE agent.agent_skills
                SET usage_count = usage_count + 1,
                    updated_at = now()
                WHERE id = ANY(%s::uuid[])
                """,
                (ids,),
            )
    except Exception as e:  # noqa: BLE001
        logger.debug("increment_usage_counts failed: %s", e)


def increment_success_counts(skill_db_ids: list[str]) -> None:
    """Bump success_count by 1 for each db_id. Called on positive session signal."""
    ids = [x for x in skill_db_ids if x]
    if not ids:
        return
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                UPDATE agent.agent_skills
                SET success_count = success_count + 1,
                    updated_at = now()
                WHERE id = ANY(%s::uuid[])
                """,
                (ids,),
            )
    except Exception as e:  # noqa: BLE001
        logger.debug("increment_success_counts failed: %s", e)


def upsert_global_skill(skill: Skill) -> None:
    """Upsert one global skill by name (without requiring a unique constraint)."""
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM agent.agent_skills
            WHERE name = %s AND tier = 'global'
            LIMIT 1
            """,
            (skill.name,),
        ).fetchone()
        import json as _json

        assets_json = _json.dumps(skill.assets) if skill.assets else "{}"

        if existing:
            conn.execute(
                """
                UPDATE agent.agent_skills
                SET description = %s,
                    category = %s,
                    content = %s,
                    generation = %s,
                    enabled = %s,
                    skill_type = %s,
                    api_version = %s,
                    assets = %s::jsonb,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    skill.description,
                    skill.category,
                    skill.content,
                    skill.generation,
                    skill.enabled,
                    skill.skill_type,
                    skill.api_version or "v1",
                    assets_json,
                    existing[0],
                ),
            )
            return

        conn.execute(
            """
            INSERT INTO agent.agent_skills
                (name, description, category, content, tier, generation, enabled,
                 skill_type, api_version, assets)
            VALUES (%s, %s, %s, %s, 'global', %s, %s, %s, %s, %s::jsonb)
            """,
            (
                skill.name,
                skill.description,
                skill.category,
                skill.content,
                skill.generation,
                skill.enabled,
                skill.skill_type,
                skill.api_version or "v1",
                assets_json,
            ),
        )
