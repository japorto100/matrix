"""Skill Evolver — Auto-Skill-Generation aus Failures (exec-10 + MetaClaw Insights).

3-Tier Skill Storage:
  - Global: von uns erstellt (manuell)
  - Team: team-shared (noch nicht implementiert)
  - Personal: auto-generiert pro User ← das macht der Evolver

MetaClaw Paper Insights:
  - Skill Generation Versioning (Sec. 3.2): Jeder Skill hat generation Index
  - Deduplication: gleiche Failures erzeugen nicht doppelte Skills
  - PRM-Scoring (Zukunft): Process Reward Model bewertet Trajectories

Aktivierung: AGENT_SKILL_EVOLUTION=true (default: false)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_BASE = Path(__file__).parent

EVOLUTION_PROMPT = """You are a Skill Evolver. Analyze the failed agent session below.
Generate a new skill that would have helped the agent succeed.

## Failed Session
User request: {user_request}
Agent response: {agent_response}
Failure reason: {failure_reason}

## Output Format (JSON)
{{
    "name": "skill-name-kebab-case",
    "description": "One-line description of what this skill teaches",
    "category": "general|trading|risk|research",
    "content": "Full markdown content with ## Workflow, ## Best Practices, ## Output Format sections"
}}

Generate exactly ONE skill. Be specific and actionable. Do not generate generic advice."""


class SkillEvolver:
    """Analysiert Failures und generiert personalisierte Skills."""

    def __init__(self) -> None:
        self.enabled = os.environ.get("AGENT_SKILL_EVOLUTION", "false").lower() == "true"
        self._generation_counter: dict[str, int] = {}  # user_id → current generation

    def _get_generation(self, user_id: str) -> int:
        """Gibt den aktuellen Generation-Index fuer einen User zurueck."""
        if user_id not in self._generation_counter:
            # Zähle existierende Skills als Basis
            user_dir = SKILLS_BASE / "personal" / user_id
            if user_dir.exists():
                self._generation_counter[user_id] = len(list(user_dir.iterdir()))
            else:
                self._generation_counter[user_id] = 0
        return self._generation_counter[user_id]

    def _is_duplicate(self, user_id: str, failure_hash: str) -> bool:
        """Prueft ob ein identischer Failure bereits einen Skill generiert hat."""
        user_dir = SKILLS_BASE / "personal" / user_id
        if not user_dir.exists():
            return False
        for skill_dir in user_dir.iterdir():
            dedup_file = skill_dir / ".failure_hash"
            if dedup_file.exists() and dedup_file.read_text().strip() == failure_hash:
                return True
        return False

    async def analyze_failure(
        self,
        user_id: str,
        user_request: str,
        agent_response: str,
        failure_reason: str,
    ) -> Path | None:
        """Analysiert einen Failure und generiert einen personaliserten Skill.

        Returns: Pfad zur generierten SKILL.md oder None.
        """
        if not self.enabled:
            return None

        # Deduplication: gleicher Failure → kein neuer Skill
        failure_hash = hashlib.sha256(f"{user_request}:{failure_reason}".encode()).hexdigest()[:16]
        if self._is_duplicate(user_id, failure_hash):
            logger.debug("Duplicate failure for user %s, skipping skill generation", user_id)
            return None

        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic()
            prompt = EVOLUTION_PROMPT.format(
                user_request=user_request,
                agent_response=agent_response,
                failure_reason=failure_reason,
            )

            response = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text if response.content else ""
            # JSON extrahieren (auch wenn in Markdown Code-Block)
            if "```" in text:
                text = text.split("```")[1].removeprefix("json").strip()
            skill_data = json.loads(text)

            name = skill_data["name"]
            generation = self._get_generation(user_id) + 1

            # Personal Skill Directory
            skill_dir = SKILLS_BASE / "personal" / user_id / name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # SKILL.md schreiben
            skill_md = (
                f"---\n"
                f"name: {name}\n"
                f"description: {skill_data['description']}\n"
                f"category: {skill_data.get('category', 'general')}\n"
                f"generation: {generation}\n"
                f"generated: {datetime.now().isoformat()}\n"
                f"user_id: {user_id}\n"
                f"---\n\n"
                f"{skill_data['content']}\n"
            )
            (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

            # Dedup Hash speichern
            (skill_dir / ".failure_hash").write_text(failure_hash, encoding="utf-8")

            self._generation_counter[user_id] = generation
            logger.info("Generated personal skill '%s' for user %s (gen %d)", name, user_id, generation)
            return skill_dir / "SKILL.md"

        except Exception as e:
            logger.warning("Skill evolution failed for user %s: %s", user_id, e)
            return None


# Trajectory Logging — Grundlage fuer PRM Scoring (MetaClaw Sec. 3.3)
# Aktuell: nur Logging. Zukunft: PRM bewertet Trajectories → bessere Skill-Evolution.

class TrajectoryLogger:
    """Loggt Agent-Trajectories fuer spaetere Analyse + PRM Scoring."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or (SKILLS_BASE / ".trajectories")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        user_id: str,
        thread_id: str,
        messages: list[dict],
        tool_calls: list[dict],
        success: bool,
        failure_reason: str | None = None,
    ) -> Path:
        """Loggt eine Agent-Trajectory."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        entry = {
            "user_id": user_id,
            "thread_id": thread_id,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "failure_reason": failure_reason,
            "messages_count": len(messages),
            "tool_calls_count": len(tool_calls),
            "messages": messages[-5:],  # Letzte 5 Messages (Token-Budget)
            "tool_calls": tool_calls,
        }
        path = self.storage_dir / f"{user_id}_{ts}.json"
        path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
