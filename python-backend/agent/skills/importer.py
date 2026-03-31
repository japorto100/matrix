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
from pathlib import Path, PurePosixPath, PureWindowsPath

from agent.skills.loader import SKILLS_BASE, parse_skill_file

logger = logging.getLogger(__name__)

MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_FILES_IN_ZIP = 100


# ── 5.3: GitHub / SkillsMP Import ───────────────────────────────────────────


ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}


async def import_from_github(
    repo_url: str,
    target_tier: str = "global",
    target_owner: str | None = None,
) -> list[str]:
    """Importiert Skills aus einem GitHub Repository.

    Klont das Repo (shallow), sucht SKILL.md Dateien, kopiert sie
    in das passende Tier-Verzeichnis.

    Args:
        repo_url: GitHub URL (z.B. https://github.com/anthropics/skills)
        target_tier: Ziel-Tier (global/team/personal)
        target_owner: Owner-ID fuer team/personal Tier

    Returns:
        Liste der importierten Skill-Namen.
    """
    import asyncio
    import subprocess
    from urllib.parse import urlparse

    # Security: nur erlaubte Git-Hosts
    parsed = urlparse(repo_url)
    if parsed.hostname not in ALLOWED_GIT_HOSTS:
        raise ValueError(f"Git host '{parsed.hostname}' not allowed. Allowed: {ALLOWED_GIT_HOSTS}")
    if parsed.scheme not in ("https",):
        raise ValueError(f"Only HTTPS git URLs allowed, got '{parsed.scheme}'")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Shallow clone
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", repo_url, tmpdir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        imported = []
        tmp_path = Path(tmpdir)

        # Suche SKILL.md Dateien rekursiv
        for skill_file in tmp_path.rglob("SKILL.md"):
            skill = parse_skill_file(skill_file, tier=target_tier, owner=target_owner)
            if skill is None:
                continue

            # Ziel-Verzeichnis bestimmen
            if target_tier == "global":
                dest_dir = SKILLS_BASE / "global" / skill.name
            elif target_tier == "team" and target_owner:
                dest_dir = SKILLS_BASE / "team" / target_owner / skill.name
            elif target_tier == "personal" and target_owner:
                dest_dir = SKILLS_BASE / "personal" / target_owner / skill.name
            else:
                dest_dir = SKILLS_BASE / "global" / skill.name

            # Ganzes Skill-Verzeichnis kopieren (SKILL.md + Assets)
            skill_dir = skill_file.parent
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(skill_dir, dest_dir)
            imported.append(skill.name)
            logger.info("Imported skill '%s' from %s → %s", skill.name, repo_url, dest_dir)

        return imported


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
        return {"success": False, "skill_name": "", "message": f"Archive not found: {archive_path}"}

    if archive_path.stat().st_size > MAX_ZIP_SIZE:
        return {"success": False, "skill_name": "", "message": f"Archive too large (max {MAX_ZIP_SIZE // 1024 // 1024}MB)"}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Sicherheits-Checks
                members = zf.infolist()
                if len(members) > MAX_FILES_IN_ZIP:
                    return {"success": False, "skill_name": "", "message": f"Too many files in archive (max {MAX_FILES_IN_ZIP})"}

                for member in members:
                    if _is_unsafe_member(member):
                        return {"success": False, "skill_name": "", "message": f"Unsafe member in archive: {member.filename}"}

                zf.extractall(tmp_path)
        except zipfile.BadZipFile:
            return {"success": False, "skill_name": "", "message": "Invalid ZIP archive"}

        # Skill-Root finden (kann direkt oder in Unterverzeichnis sein)
        items = [p for p in tmp_path.iterdir() if not _should_ignore(p)]
        if not items:
            return {"success": False, "skill_name": "", "message": "Archive is empty"}
        skill_root = items[0] if len(items) == 1 and items[0].is_dir() else tmp_path

        # SKILL.md suchen
        skill_file = skill_root / "SKILL.md"
        if not skill_file.exists():
            return {"success": False, "skill_name": "", "message": "No SKILL.md found in archive"}

        skill = parse_skill_file(skill_file, tier=target_tier, owner=target_owner)
        if skill is None:
            return {"success": False, "skill_name": "", "message": "Failed to parse SKILL.md"}

        # Installieren
        if target_tier == "global":
            dest_dir = SKILLS_BASE / "global" / skill.name
        elif target_tier == "team" and target_owner:
            dest_dir = SKILLS_BASE / "team" / target_owner / skill.name
        elif target_tier == "personal" and target_owner:
            dest_dir = SKILLS_BASE / "personal" / target_owner / skill.name
        else:
            dest_dir = SKILLS_BASE / "global" / skill.name

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(skill_root, dest_dir)

        logger.info("Installed skill '%s' from archive → %s", skill.name, dest_dir)
        return {"success": True, "skill_name": skill.name, "message": f"Installed to {dest_dir}"}
