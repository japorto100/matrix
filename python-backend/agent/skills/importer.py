"""Skill Importer — Import Skills aus GitHub und SkillsMP (exec-10 Phase 5.3 + 5.4).

5.3: SkillsMP / GitHub Import
  - GitHub Repo klonen → SKILL.md Dateien extrahieren → agent/skills/global/
  - Anthropic Official: github.com/anthropics/skills
  - Microsoft: github.com/microsoft/skills
  - Community: skillsmp.com (700K+ Skills)

5.4: .skill ZIP Archive Support
  - ZIP mit SKILL.md + Scripts + Assets
  - Sicherheits-Checks (Path Traversal, Symlinks, Size Limits)
  - Pattern uebernommen von deer-flow installer.py

SKILL.md Standard (agentskills.io):
  - YAML Frontmatter (name, description, category)
  - Markdown Body (Instructions, Examples, Guidelines)
  - Optional: Scripts, Templates, Assets
  - Adoptiert von: Anthropic, OpenAI, Microsoft, Google, 30+ Tools
"""

from __future__ import annotations

import logging
import shutil
import stat
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from agent.security.skills_guard import scan_skill, should_allow_install
from agent.skills.loader import SKILLS_BASE, Skill, parse_skill_file
from agent.skills.usage_state import PinnedSkillWriteError, reject_if_pinned

logger = logging.getLogger(__name__)

MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_FILES_IN_ZIP = 100


def _skill_to_scan_input(skill: Skill, skill_file: Path) -> dict[str, Any]:
    """Flatten a parsed Skill + its on-disk SKILL.md into scan_skill's input shape.

    The scanner wants ``{"name": str, "files": {path: content}}`` with content
    as raw strings. We read SKILL.md from disk (so frontmatter is scannable too)
    and flatten ``skill.assets`` (``{subdir: {fname: body}}``) into flat
    ``"scripts/foo.sh"`` keys.
    """
    files: dict[str, str] = {}
    try:
        files["SKILL.md"] = skill_file.read_text(encoding="utf-8")
    except OSError:
        # Fallback to the parsed body so a missing-file doesn't break the scan
        files["SKILL.md"] = skill.content
    for subdir, entries in (skill.assets or {}).items():
        if not isinstance(entries, dict):
            continue
        for fname, body in entries.items():
            if isinstance(body, str):
                files[f"{subdir}/{fname}"] = body
    return {"name": skill.name, "files": files}


def _findings_to_dicts(findings: list) -> list[dict[str, Any]]:
    """Dataclass Finding → plain dict for JSON responses."""
    return [asdict(f) for f in findings]


def _scan_trust_source_for_tier(target_tier: str) -> str:
    """Map the Phase-1 target_tier to a skills_guard trust source string.

    - ``global`` tier installs are typically ops-curated → ``matrix-official``.
    - ``team`` tier installs are org-curated → ``trusted``.
    - ``personal`` tier installs are user-generated → ``agent-created``
      (keeps ``dangerous`` at "ask", blocking install without HITL).
    - Anything else defaults to ``community`` (strictest).
    """
    if target_tier == "global":
        return "matrix-official"
    if target_tier == "team":
        return "trusted"
    if target_tier == "personal":
        return "agent-created"
    return "community"


def _pinned_rejection(skill_name: str, target_tier: str, reason: str) -> dict[str, Any]:
    return {
        "name": skill_name,
        "verdict": "blocked",
        "trust_level": _scan_trust_source_for_tier(target_tier),
        "findings": [],
        "reason": reason,
        "code": "pinned_skill_write_refused",
    }


# ── 5.3: GitHub / SkillsMP Import ───────────────────────────────────────────


ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}


async def import_from_github(
    repo_url: str,
    target_tier: str = "global",
    target_owner: str | None = None,
) -> dict[str, Any]:
    """Importiert Skills aus einem GitHub Repository.

    Two-pass: (1) parse + scan ALL SKILL.md candidates via skills_guard, then
    (2) install. If ANY candidate is disallowed by the policy matrix, the
    whole import is rejected — no partial dest_dir is written.

    Args:
        repo_url: GitHub URL (z.B. https://github.com/anthropics/skills)
        target_tier: Ziel-Tier (global/team/personal)
        target_owner: Owner-ID fuer team/personal Tier

    Returns:
        ``{"success": bool, "imported": [...names], "rejected": [{name,
        verdict, findings, reason}], "repo_url": str}``. REST caller maps
        ``success=False`` to HTTP 422.
    """
    scan_source = _scan_trust_source_for_tier(target_tier)
    import asyncio
    import subprocess
    from urllib.parse import urlparse

    # Security: nur erlaubte Git-Hosts
    parsed = urlparse(repo_url)
    if parsed.hostname not in ALLOWED_GIT_HOSTS:
        raise ValueError(
            f"Git host '{parsed.hostname}' not allowed. Allowed: {ALLOWED_GIT_HOSTS}"
        )
    if parsed.scheme not in ("https",):
        raise ValueError(f"Only HTTPS git URLs allowed, got '{parsed.scheme}'")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Shallow clone
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            repo_url,
            tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        tmp_path = Path(tmpdir)

        # Pass 1: parse + scan ALL candidates before any install
        candidates: list[tuple[Skill, Path, Path]] = []
        rejected: list[dict[str, Any]] = []

        for skill_file in tmp_path.rglob("SKILL.md"):
            skill = parse_skill_file(skill_file, tier=target_tier, owner=target_owner)
            if skill is None:
                continue
            scan_result = scan_skill(
                _skill_to_scan_input(skill, skill_file), source=scan_source
            )
            allowed, reason = should_allow_install(scan_result)
            if allowed is not True:
                rejected.append(
                    {
                        "name": skill.name,
                        "verdict": scan_result.verdict,
                        "trust_level": scan_result.trust_level,
                        "findings": _findings_to_dicts(scan_result.findings),
                        "reason": reason,
                    }
                )
                logger.warning(
                    "skills_guard blocked import of '%s' from %s: %s",
                    skill.name, repo_url, reason,
                )
                continue
            if target_tier == "team" and target_owner:
                dest_dir = SKILLS_BASE / "team" / target_owner / skill.name
            elif target_tier == "personal" and target_owner:
                dest_dir = SKILLS_BASE / "personal" / target_owner / skill.name
            else:
                dest_dir = SKILLS_BASE / "global" / skill.name
            try:
                reject_if_pinned(
                    f"{target_tier}:{skill.name}",
                    skills_base=SKILLS_BASE,
                )
            except PinnedSkillWriteError as e:
                rejected.append(_pinned_rejection(skill.name, target_tier, str(e)))
                logger.warning(
                    "pinned skill blocked import overwrite of '%s' from %s",
                    skill.name,
                    repo_url,
                )
                continue
            candidates.append((skill, skill_file, dest_dir))

        # Any block → reject the whole import (no partial dest_dir on disk).
        if rejected:
            # ADR-004: surface-dialog HITL. When any rejection is at verdict
            # ``dangerous`` (not just ``caution``), hint the frontend BFF to
            # route to the skills-guard-drawer instead of a generic toast.
            has_dangerous = any(r.get("verdict") == "dangerous" for r in rejected)
            response: dict[str, Any] = {
                "success": False,
                "imported": [],
                "rejected": rejected,
                "repo_url": repo_url,
            }
            if has_dangerous:
                response["suggested_action"] = "hitl_confirm"
            return response

        # Pass 2: install the vetted candidates
        imported: list[str] = []
        for skill, skill_file, dest_dir in candidates:
            skill_dir = skill_file.parent
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(skill_dir, dest_dir)
            imported.append(skill.name)
            logger.info(
                "Imported skill '%s' from %s → %s", skill.name, repo_url, dest_dir
            )

        return {
            "success": True,
            "imported": imported,
            "rejected": [],
            "repo_url": repo_url,
        }


# ── 5.4: .skill ZIP Archive Support ─────────────────────────────────────────


def _is_unsafe_member(info: zipfile.ZipInfo) -> bool:
    """Prueft ob ein ZIP-Member unsicher ist (Path Traversal, Symlinks)."""
    name = info.filename.replace("\\", "/")
    if name.startswith("/"):
        return True
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return True
    if PureWindowsPath(name).is_absolute():
        return True
    # Symlink detection
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        return True
    return False


def _should_ignore(path: Path) -> bool:
    """Ignoriert macOS Metadaten und Dotfiles."""
    return path.name.startswith(".") or path.name == "__MACOSX"


def install_from_archive(
    archive_path: Path | str,
    target_tier: str = "global",
    target_owner: str | None = None,
) -> dict:
    """Installiert einen Skill aus einem .skill ZIP Archive.

    Sicherheits-Checks (deer-flow Pattern):
    - Path Traversal Prevention
    - Symlink Detection
    - Size Limit (50 MB)
    - File Count Limit (100)
    - SKILL.md muss vorhanden sein

    Args:
        archive_path: Pfad zum .skill ZIP File
        target_tier: Ziel-Tier
        target_owner: Owner-ID

    Returns:
        {"success": bool, "skill_name": str, "message": str}
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        return {
            "success": False,
            "skill_name": "",
            "message": f"Archive not found: {archive_path}",
        }

    if archive_path.stat().st_size > MAX_ZIP_SIZE:
        return {
            "success": False,
            "skill_name": "",
            "message": f"Archive too large (max {MAX_ZIP_SIZE // 1024 // 1024}MB)",
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Sicherheits-Checks
                members = zf.infolist()
                if len(members) > MAX_FILES_IN_ZIP:
                    return {
                        "success": False,
                        "skill_name": "",
                        "message": f"Too many files in archive (max {MAX_FILES_IN_ZIP})",
                    }

                for member in members:
                    if _is_unsafe_member(member):
                        return {
                            "success": False,
                            "skill_name": "",
                            "message": f"Unsafe member in archive: {member.filename}",
                        }

                zf.extractall(tmp_path)
        except zipfile.BadZipFile:
            return {
                "success": False,
                "skill_name": "",
                "message": "Invalid ZIP archive",
            }

        # Skill-Root finden (kann direkt oder in Unterverzeichnis sein)
        items = [p for p in tmp_path.iterdir() if not _should_ignore(p)]
        if not items:
            return {"success": False, "skill_name": "", "message": "Archive is empty"}
        skill_root = items[0] if len(items) == 1 and items[0].is_dir() else tmp_path

        # SKILL.md suchen
        skill_file = skill_root / "SKILL.md"
        if not skill_file.exists():
            return {
                "success": False,
                "skill_name": "",
                "message": "No SKILL.md found in archive",
            }

        skill = parse_skill_file(skill_file, tier=target_tier, owner=target_owner)
        if skill is None:
            return {
                "success": False,
                "skill_name": "",
                "message": "Failed to parse SKILL.md",
            }

        # skills_guard static scan BEFORE touching the filesystem destination.
        scan_source = _scan_trust_source_for_tier(target_tier)
        scan_result = scan_skill(
            _skill_to_scan_input(skill, skill_file), source=scan_source
        )
        allowed, reason = should_allow_install(scan_result)
        if allowed is not True:
            logger.warning(
                "skills_guard blocked archive install of '%s': %s",
                skill.name, reason,
            )
            payload: dict[str, Any] = {
                "success": False,
                "skill_name": skill.name,
                "message": reason,
                "verdict": scan_result.verdict,
                "trust_level": scan_result.trust_level,
                "findings": _findings_to_dicts(scan_result.findings),
            }
            # ADR-004: surface-dialog HITL hint on dangerous verdict.
            if scan_result.verdict == "dangerous":
                payload["suggested_action"] = "hitl_confirm"
            return payload

        # Installieren
        if target_tier == "global":
            dest_dir = SKILLS_BASE / "global" / skill.name
        elif target_tier == "team" and target_owner:
            dest_dir = SKILLS_BASE / "team" / target_owner / skill.name
        elif target_tier == "personal" and target_owner:
            dest_dir = SKILLS_BASE / "personal" / target_owner / skill.name
        else:
            dest_dir = SKILLS_BASE / "global" / skill.name

        try:
            reject_if_pinned(f"{target_tier}:{skill.name}", skills_base=SKILLS_BASE)
        except PinnedSkillWriteError as e:
            logger.warning("pinned skill blocked archive overwrite of '%s'", skill.name)
            return {
                "success": False,
                "skill_name": skill.name,
                "message": str(e),
                "code": "pinned_skill_write_refused",
            }

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(skill_root, dest_dir)

        logger.info("Installed skill '%s' from archive → %s", skill.name, dest_dir)
        return {
            "success": True,
            "skill_name": skill.name,
            "message": f"Installed to {dest_dir}",
        }
