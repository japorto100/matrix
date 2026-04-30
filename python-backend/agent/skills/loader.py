"""Skill Loader — 3-Tier Skill System (exec-10 Phase 3 + MetaClaw Insights).

Tiers:
  1. Global: Von uns erstellt, fuer alle User (agent/skills/global/)
  2. Team: Team-shared Skills (agent/skills/team/{team_id}/)
  3. Personal: Auto-generiert pro User (agent/skills/personal/{user_id}/)

Loading-Reihenfolge: Global → Team → Personal
Personal ueberschreibt Team, Team ueberschreibt Global (bei gleichem Skill-Name).

Skill-Format: YAML Frontmatter + Markdown (deer-flow / MetaClaw Pattern)
Versioning: Generation-Index in Frontmatter (MetaClaw Paper Sec. 3.2)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

SKILLS_BASE = Path(__file__).parent
MAX_ASSET_FILE_BYTES = 64 * 1024
MAX_ASSET_TOTAL_BYTES = 256 * 1024
IGNORED_ASSET_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    ".venv",
}
TEXT_ASSET_SUFFIXES = {
    ".bash",
    ".css",
    ".csv",
    ".go",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


@dataclass
class Skill:
    """Geladener Skill aus SKILL.md oder `agent.agent_skills`."""

    name: str
    description: str
    category: str
    content: str
    path: Path = field(repr=False)
    tier: Literal["global", "team", "personal"] = "global"
    owner: str | None = None  # team_id oder user_id
    generation: int = 0  # MetaClaw: Skill Generation Index
    enabled: bool = True
    db_id: str | None = None  # UUID aus agent.agent_skills (optional)
    skill_type: Literal["general", "task_specific"] = "task_specific"
    api_version: str | None = None  # Schema-Drift Detection (exec-skills §6.6)
    assets: dict = field(default_factory=dict)  # scripts/examples/templates JSONB


def parse_skill_file(
    skill_file: Path, tier: str = "global", owner: str | None = None
) -> Skill | None:
    """Parst eine SKILL.md Datei mit YAML Frontmatter."""
    try:
        raw = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read skill file %s: %s", skill_file, e)
        return None

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if not fm_match:
        logger.warning("No YAML frontmatter in %s", skill_file)
        return None

    metadata: dict[str, str] = {}
    for line in fm_match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip()

    name = metadata.get("name")
    if not name:
        logger.warning("Skill has no name in %s", skill_file)
        return None

    content = raw[fm_match.end() :]

    assets = _scan_skill_assets(skill_file.parent)

    skill_type_raw = metadata.get("skill_type", "task_specific")
    skill_type = skill_type_raw if skill_type_raw in ("general", "task_specific") else "task_specific"

    return Skill(
        name=name,
        description=metadata.get("description", ""),
        category=metadata.get("category", "general"),
        content=content.strip(),
        path=skill_file,
        tier=tier,
        owner=owner,
        generation=int(metadata.get("generation", "0")),
        skill_type=skill_type,
        api_version=metadata.get("api_version"),
        assets=assets,
    )


def _scan_skill_assets(skill_dir: Path) -> dict[str, dict[str, str]]:
    """Collect small text assets from a skill package for JSONB/scanning.

    Assets keep the historical ``{top_dir: {relative_path: content}}`` shape.
    We now scan all non-hidden text-code assets, not just scripts/examples/
    templates, so uploaded skill packages cannot hide unscanned code in
    arbitrary subdirectories.
    """
    assets: dict[str, dict[str, str]] = {}
    total_bytes = 0
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.name == "SKILL.md":
            continue
        rel = path.relative_to(skill_dir)
        if any(part.startswith(".") or part in IGNORED_ASSET_DIRS for part in rel.parts):
            continue
        if path.suffix.lower() not in TEXT_ASSET_SUFFIXES:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_ASSET_FILE_BYTES or total_bytes + size > MAX_ASSET_TOTAL_BYTES:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except Exception:  # noqa: BLE001
            continue
        top = rel.parts[0] if len(rel.parts) > 1 else "_root"
        inner = str(Path(*rel.parts[1:])) if len(rel.parts) > 1 else rel.name
        assets.setdefault(top, {})[inner] = body
        total_bytes += size
    return assets


def _scan_tier(
    base_dir: Path,
    tier: Literal["global", "team", "personal"],
    owner: str | None = None,
    category: str | None = None,
) -> list[Skill]:
    """Scannt ein Tier-Verzeichnis nach SKILL.md Dateien."""
    skills: list[Skill] = []
    if not base_dir.exists():
        return skills

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("_") or item.name == "__pycache__":
            continue

        skill_file = item / "SKILL.md"
        if not skill_file.exists():
            continue

        skill = parse_skill_file(skill_file, tier=tier, owner=owner)
        if skill is None:
            continue
        if category and skill.category != category:
            continue

        skills.append(skill)

    return skills


def _merge_global_from_db(
    merged: dict[str, Skill],
    *,
    category: str | None,
    prefer_db: bool,
) -> None:
    """Overlay globale Skills aus `agent.agent_skills` (Migration 014)."""
    try:
        from agent.skills.store_db import fetch_enabled_skills
    except Exception as e:  # noqa: BLE001
        logger.debug("DB skill source unavailable: %s", e)
        return

    rows = fetch_enabled_skills(tiers=("global",), category=category)
    if not rows:
        return

    for skill in rows:
        if prefer_db or skill.name not in merged:
            merged[skill.name] = skill


def load_skills(
    user_id: str | None = None,
    team_id: str | None = None,
    category: str | None = None,
    skills_base: Path | None = None,
) -> list[Skill]:
    """Laedt Skills aus allen 3 Tiers und merged sie.

    Loading-Reihenfolge: Global → Team → Personal
    Bei gleichem Name: Personal > Team > Global (Override-Semantik)

    Env `AGENT_SKILLS_SOURCE` (default: `filesystem`):
      - `filesystem` → nur Dateien unter `agent/skills/`
      - `db` → globale Skills aus `agent.agent_skills`
      - `hybrid` → Dateisystem + DB; DB-global gewinnt bei Namenskollision

    Args:
        user_id: User-ID fuer Personal-Skills (optional)
        team_id: Team-ID fuer Team-Skills (optional)
        category: Nur Skills dieser Kategorie (optional)
        skills_base: Base-Verzeichnis (default: agent/skills/)

    Returns:
        Merged Liste, sortiert nach Name.
    """
    base = skills_base or SKILLS_BASE
    source = os.environ.get("AGENT_SKILLS_SOURCE", "filesystem").strip().lower()
    merged: dict[str, Skill] = {}

    # Tier 1: Global
    if source in ("filesystem", "hybrid"):
        for skill in _scan_tier(base / "global", tier="global", category=category):
            merged[skill.name] = skill
    if source in ("db", "hybrid"):
        _merge_global_from_db(
            merged,
            category=category,
            prefer_db=(source == "hybrid" or source == "db"),
        )

    # Tier 2: Team
    if team_id:
        for skill in _scan_tier(
            base / "team" / team_id, tier="team", owner=team_id, category=category
        ):
            merged[skill.name] = skill

    # Tier 3: Personal
    if user_id:
        for skill in _scan_tier(
            base / "personal" / user_id,
            tier="personal",
            owner=user_id,
            category=category,
        ):
            merged[skill.name] = skill

    skills = sorted(merged.values(), key=lambda s: s.name)
    logger.info(
        "Loaded %d skills (source=%s, global=%d, team=%d, personal=%d)",
        len(skills),
        source,
        sum(1 for s in skills if s.tier == "global"),
        sum(1 for s in skills if s.tier == "team"),
        sum(1 for s in skills if s.tier == "personal"),
    )
    return skills


def format_skills_for_prompt(
    skills: list[Skill] | None = None,
    *,
    query: str | None = None,
    user_id: str | None = None,
    team_id: str | None = None,
    category: str | None = None,
    skills_base: Path | None = None,
) -> str:
    """Formatiert Skills als Prompt-Abschnitt fuer LLM Injection.

    Ohne `skills`: laedt via `load_skills`. Mit `query` (letzte User-Nachricht o.ae.):
    BM25+dense Hybrid-Ranking (exec-skills Phase 1, `agent.skills.finder`).
    """
    if skills is None:
        skills = load_skills(
            user_id=user_id, team_id=team_id, category=category, skills_base=skills_base
        )

    if query and query.strip():
        from agent.skills.finder import filter_disabled_skills, find_skills_for_query

        skills = filter_disabled_skills(skills, user_id)
        skills = find_skills_for_query(skills, query.strip())

    if not skills:
        return ""

    sections = ["## Available Skills\n"]
    for skill in skills:
        tier_badge = f"[{skill.tier}]" if skill.tier != "global" else ""
        sections.append(
            f"### {skill.name} {tier_badge}\n{skill.description}\n\n{skill.content}\n"
        )

    return "\n".join(sections)


async def format_skills_for_prompt_async(
    skills: list[Skill] | None = None,
    *,
    query: str | None = None,
    user_id: str | None = None,
    team_id: str | None = None,
    category: str | None = None,
    skills_base: Path | None = None,
    context_hint: str = "",
    api_key: str | None = None,
    session_id: str = "",
    thread_id: str = "",
) -> str:
    """Async variant with query-ranking, coverage-gated refinement, audit + counters.

    Audit events emitted when `query` is given:
      - SKILL_FOUND  — after ranking, with skill_ids + rank_scores
      - SKILL_REFINED — when refiner ran (per_skill or compose mode)
      - SKILL_USED   — when skills are actually rendered into the prompt
    Also increments `agent.agent_skills.usage_count` for each DB-backed
    skill and records filesystem skill usage in the lifecycle sidecar.
    """
    if skills is None:
        skills = load_skills(
            user_id=user_id, team_id=team_id, category=category, skills_base=skills_base
        )

    pre_refine: list[Skill] = skills
    refine_fired = False
    coverage_score: float | None = None

    if query and query.strip():
        from agent.skills.finder import filter_disabled_skills
        from agent.skills.iterative_search import iterative_find

        skills = filter_disabled_skills(skills, user_id)

        # General skills are broad, but still query-gated by default. Always
        # loading them made trivial/no-tool turns drag memory guidance into the
        # prompt and caused Meta-Harness runner-parity false positives.
        always_load_general = os.environ.get(
            "AGENT_SKILL_ALWAYS_LOAD_GENERAL", ""
        ).strip().lower() in ("1", "true", "yes", "on")
        general = [s for s in skills if s.skill_type == "general"]
        task_specific = [s for s in skills if s.skill_type != "general"]
        searchable = task_specific if always_load_general else skills

        search_result = await iterative_find(
            searchable, query.strip(), api_key=api_key
        )
        skills = (general + search_result.picked) if always_load_general else search_result.picked
        pre_refine = skills

        await _audit_skill(
            action="skill_found",
            skills=skills,
            query=query,
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            metadata={
                "search_rounds": search_result.rounds,
                "reformulations": search_result.queries[1:]
                if len(search_result.queries) > 1
                else None,
                "satisfied": search_result.satisfied,
                "search_traces": search_result.search_traces,
            },
        )

        if _refinement_enabled() and skills:
            try:
                from agent.skills.coverage import should_refine
                from agent.skills.refiner import refine_skills_for_query

                proceed, coverage_score = await should_refine(
                    skills, query.strip(), api_key=api_key
                )
                if proceed:
                    refined = await refine_skills_for_query(
                        skills,
                        query=query.strip(),
                        context_hint=context_hint,
                        api_key=api_key,
                    )
                    refine_fired = True
                    await _audit_skill(
                        action="skill_refined",
                        skills=refined,
                        query=query,
                        user_id=user_id,
                        session_id=session_id,
                        thread_id=thread_id,
                        metadata={
                            "coverage_score": coverage_score,
                            "source_skills": [f"{s.tier}:{s.name}" for s in pre_refine],
                            "mode": os.environ.get("AGENT_SKILL_REFINE_MODE", "compose"),
                        },
                    )
                    skills = refined
                else:
                    logger.debug(
                        "skill refinement skipped: coverage=%.1f below threshold",
                        coverage_score,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("format_skills_for_prompt_async refine failed: %s", e)

        # Final usage record — what actually lands in the prompt.
        if skills:
            await _audit_skill(
                action="skill_used",
                skills=skills,
                query=query,
                user_id=user_id,
                session_id=session_id,
                thread_id=thread_id,
                metadata={
                    "refined": refine_fired,
                    "coverage_score": coverage_score,
                    "source_skills": [
                        f"{s.tier}:{s.name}" for s in pre_refine
                    ]
                    if refine_fired
                    else None,
                },
            )
            _bump_usage(pre_refine if refine_fired else skills, skills_base=skills_base)

    return format_skills_for_prompt(skills)


def _refinement_enabled() -> bool:
    v = os.environ.get("AGENT_SKILL_REFINEMENT", "").strip().lower()
    return v in ("1", "true", "yes", "on")


async def _audit_skill(
    *,
    action: str,
    skills: list[Skill],
    query: str | None,
    user_id: str | None,
    session_id: str,
    thread_id: str,
    metadata: dict | None = None,
) -> None:
    """Emit a SKILL_* audit event. Best-effort, never raises."""
    try:
        from agent.audit.logger import AuditAction, audit_log

        try:
            act = AuditAction(action)
        except ValueError:
            logger.debug("unknown skill audit action: %s", action)
            return
        payload: dict = {
            "skill_ids": [f"{s.tier}:{s.name}" for s in skills],
            "skill_names": [s.name for s in skills],
            "query_preview": (query or "")[:200],
            "user_id": user_id or "",
        }
        if metadata:
            payload.update(metadata)
        await audit_log(
            action=act,
            agent_id="skills",
            session_id=session_id,
            thread_id=thread_id,
            success=True,
            metadata=payload,
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("_audit_skill swallowed: %s", e)


def _bump_usage(skills: list[Skill], *, skills_base: Path | None = None) -> None:
    """Record prompt usage for DB-backed and filesystem skills."""
    try:
        from agent.skills.usage_state import record_prompt_usage

        record_prompt_usage(skills, skills_base=skills_base or SKILLS_BASE)
    except Exception as e:  # noqa: BLE001
        logger.debug("_bump_usage sidecar swallowed: %s", e)

    try:
        from agent.skills.store_db import increment_usage_counts

        ids = [s.db_id for s in skills if getattr(s, "db_id", None)]
        if ids:
            increment_usage_counts([str(x) for x in ids])
    except Exception as e:  # noqa: BLE001
        logger.debug("_bump_usage swallowed: %s", e)
