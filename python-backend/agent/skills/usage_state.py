"""Filesystem-backed skill lifecycle state.

This is intentionally provider-free and best-effort: DB-backed skills keep
their lifetime counters in PostgreSQL, while filesystem/team/personal skills
need a small local sidecar so the runtime can track prompt usage and protect
curated/pinned skills from silent overwrites.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

USAGE_STATE_ENV = "AGENT_SKILL_USAGE_STATE_PATH"
SCHEMA_VERSION = 1
DEFAULT_STATE = "active"


class PinnedSkillWriteError(RuntimeError):
    """Raised when an install/import would overwrite a pinned skill."""


def skill_id_for(skill: Any) -> str:
    """Return the stable tier:name identifier used by Control and prompts."""
    return f"{getattr(skill, 'tier', 'global')}:{getattr(skill, 'name', '')}"


def state_path(skills_base: Path | None = None) -> Path:
    explicit = os.environ.get(USAGE_STATE_ENV, "").strip()
    if explicit:
        return Path(explicit)
    if skills_base is not None:
        return skills_base / ".usage.json"
    xdg_state_home = os.environ.get("XDG_STATE_HOME", "").strip()
    state_home = Path(xdg_state_home) if xdg_state_home else Path.home() / ".local" / "state"
    return state_home / "matrix-agent" / "skills" / "usage.json"


def _empty_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "skills": {}}


def load_state(path: Path | None = None, *, skills_base: Path | None = None) -> dict[str, Any]:
    target = path or state_path(skills_base)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _empty_state()
    except Exception:
        return _empty_state()
    if not isinstance(raw, dict):
        return _empty_state()
    skills = raw.get("skills")
    if not isinstance(skills, dict):
        raw["skills"] = {}
    raw["schema_version"] = SCHEMA_VERSION
    return raw


def save_state(
    state: dict[str, Any],
    path: Path | None = None,
    *,
    skills_base: Path | None = None,
) -> None:
    target = path or state_path(skills_base)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "skills": state.get("skills", {}),
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)


def _entry_for(skill_id: str, *, skill: Any | None = None) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    tier, _, name = skill_id.partition(":")
    return {
        "skill_id": skill_id,
        "tier": tier or getattr(skill, "tier", "global"),
        "name": name or getattr(skill, "name", ""),
        "owner": getattr(skill, "owner", None),
        "path": str(getattr(skill, "path", "")) if skill is not None else "",
        "state": DEFAULT_STATE,
        "pinned": False,
        "use_count": 0,
        "view_count": 0,
        "first_used_at": None,
        "last_used_at": None,
        "last_viewed_at": None,
        "updated_at": now,
    }


def skill_usage_snapshot(
    skill_id: str,
    *,
    path: Path | None = None,
    skills_base: Path | None = None,
) -> dict[str, Any]:
    state = load_state(path, skills_base=skills_base)
    entry = state.get("skills", {}).get(skill_id)
    if isinstance(entry, dict):
        return dict(entry)
    return _entry_for(skill_id)


def record_prompt_usage(
    skills: list[Any],
    *,
    path: Path | None = None,
    skills_base: Path | None = None,
) -> None:
    if not skills:
        return
    state = load_state(path, skills_base=skills_base)
    entries = state.setdefault("skills", {})
    now = datetime.now(UTC).isoformat()
    for skill in skills:
        skill_id = skill_id_for(skill)
        entry = entries.setdefault(skill_id, _entry_for(skill_id, skill=skill))
        entry.setdefault("first_used_at", now)
        if not entry.get("first_used_at"):
            entry["first_used_at"] = now
        entry["last_used_at"] = now
        entry["updated_at"] = now
        entry["use_count"] = int(entry.get("use_count") or 0) + 1
        entry["tier"] = getattr(skill, "tier", entry.get("tier", "global"))
        entry["name"] = getattr(skill, "name", entry.get("name", ""))
        entry["owner"] = getattr(skill, "owner", entry.get("owner"))
        entry["path"] = str(getattr(skill, "path", entry.get("path", "")))
        entry.setdefault("state", DEFAULT_STATE)
        entry.setdefault("pinned", False)
    save_state(state, path, skills_base=skills_base)


def record_view(
    skill_id: str,
    *,
    path: Path | None = None,
    skills_base: Path | None = None,
) -> dict[str, Any]:
    state = load_state(path, skills_base=skills_base)
    entries = state.setdefault("skills", {})
    entry = entries.setdefault(skill_id, _entry_for(skill_id))
    now = datetime.now(UTC).isoformat()
    entry["view_count"] = int(entry.get("view_count") or 0) + 1
    entry["last_viewed_at"] = now
    entry["updated_at"] = now
    save_state(state, path, skills_base=skills_base)
    return dict(entry)


def set_pinned(
    skill_id: str,
    pinned: bool,
    *,
    path: Path | None = None,
    skills_base: Path | None = None,
) -> dict[str, Any]:
    state = load_state(path, skills_base=skills_base)
    entries = state.setdefault("skills", {})
    entry = entries.setdefault(skill_id, _entry_for(skill_id))
    entry["pinned"] = bool(pinned)
    entry["updated_at"] = datetime.now(UTC).isoformat()
    save_state(state, path, skills_base=skills_base)
    return dict(entry)


def is_pinned(
    skill_id: str,
    *,
    path: Path | None = None,
    skills_base: Path | None = None,
) -> bool:
    return bool(skill_usage_snapshot(skill_id, path=path, skills_base=skills_base).get("pinned"))


def reject_if_pinned(
    skill_id: str,
    *,
    path: Path | None = None,
    skills_base: Path | None = None,
) -> None:
    if is_pinned(skill_id, path=path, skills_base=skills_base):
        raise PinnedSkillWriteError(f"skill '{skill_id}' is pinned and cannot be overwritten")
