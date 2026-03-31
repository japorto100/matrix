"""RL Trainer — Langsame Lern-Schleife (MetaClaw Paper Sec. 3.3).

Zwei Komponenten:
1. PRM (Process Reward Model): LLM-as-Judge bewertet Trajectories
2. LoRA Training: Fine-Tuning via Cloud-API oder Self-Hosted

Aktuell: Nur PRM Scoring implementiert.
LoRA Training ist vorbereitet aber deaktiviert (AGENT_RL_ENABLED=false).

MetaClaw Paper Flow:
  Trajectories sammeln → PRM scored → bei genug Daten → LoRA Training
  Training nur in Idle-Windows (OMLS: User inaktiv >30min)

Zukunft:
  - OpenAI Fine-Tuning API (einfachster Pfad)
  - Self-Hosted: Unsloth/axolotl auf Cloud-GPU (Modal, RunPod)
  - Anthropic: Kein Public Fine-Tuning API (Stand 03/2026)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRAJECTORIES_DIR = Path(__file__).parent / ".trajectories"


class ProcessRewardModel:
    """LLM-as-Judge: bewertet Agent-Trajectories.

    Jede Trajectory bekommt einen Score (0-10):
    - 0-3: Failure (Skill-Evolution Trigger)
    - 4-6: Partial success (kein Trigger)
    - 7-10: Success (positives Trainingsbeispiel)
    """

    PRM_PROMPT = """You are a Process Reward Model. Score this agent trajectory.

## Trajectory
User request: {user_request}
Agent response: {agent_response}
Tool calls: {tool_calls}
Success: {success}

## Scoring Criteria
- Did the agent understand the request correctly? (0-2 points)
- Were the tool calls appropriate and efficient? (0-3 points)
- Was the final response helpful and accurate? (0-3 points)
- Was the reasoning sound? (0-2 points)

## Output (JSON only)
{{"score": <0-10>, "reasoning": "<brief explanation>", "failure_category": "<null or: wrong_tool|incomplete|hallucination|timeout|misunderstanding>"}}"""

    def __init__(self) -> None:
        self.enabled = os.environ.get("AGENT_PRM_ENABLED", "false").lower() == "true"

    async def score(
        self,
        user_request: str,
        agent_response: str,
        tool_calls: list[dict],
        success: bool,
    ) -> dict[str, Any]:
        """Bewertet eine Trajectory und gibt Score + Reasoning zurueck."""
        if not self.enabled:
            return {"score": -1, "reasoning": "PRM disabled", "failure_category": None}

        try:
            from agent.llm_helper import extract_json, llm_call

            prompt = self.PRM_PROMPT.format(
                user_request=user_request,
                agent_response=agent_response[:2000],
                tool_calls=json.dumps(tool_calls[:5], default=str),
                success=success,
            )
            text = await llm_call(prompt, max_tokens=512)
            return extract_json(text)

        except Exception as e:
            logger.warning("PRM scoring failed: %s", e)
            return {"score": -1, "reasoning": str(e), "failure_category": None}


class LoRATrainer:
    """LoRA Fine-Tuning Infrastruktur (deaktiviert, Grundlage gelegt).

    Drei moegliche Backends:
    1. OpenAI Fine-Tuning API (einfachster Pfad)
    2. Self-Hosted: Unsloth auf Modal/RunPod
    3. Anthropic: Kein Public API (Stand 03/2026)

    Training wird nur in Idle-Windows getriggert (OMLS Pattern).
    """

    def __init__(self) -> None:
        self.enabled = os.environ.get("AGENT_RL_ENABLED", "false").lower() == "true"
        self.backend = os.environ.get("AGENT_RL_BACKEND", "openai")  # openai | unsloth | disabled
        self.min_samples = int(os.environ.get("AGENT_RL_MIN_SAMPLES", "50"))
        self.training_data_dir = TRAJECTORIES_DIR / "training"
        self.training_data_dir.mkdir(parents=True, exist_ok=True)

    def collect_training_sample(
        self,
        trajectory_path: Path,
        prm_score: dict[str, Any],
    ) -> None:
        """Sammelt eine bewertete Trajectory als Trainingsbeispiel.

        Score >= 7: Positives Beispiel (Agent hat gut reagiert)
        Score <= 3: Negatives Beispiel + Skill-Evolution Trigger
        """
        if not self.enabled:
            return

        score = prm_score.get("score", -1)
        if score < 0:
            return  # PRM Scoring fehlgeschlagen

        sample = {
            "trajectory": str(trajectory_path),
            "score": score,
            "reasoning": prm_score.get("reasoning", ""),
            "failure_category": prm_score.get("failure_category"),
            "collected_at": datetime.now().isoformat(),
            "label": "positive" if score >= 7 else "negative" if score <= 3 else "neutral",
        }

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = self.training_data_dir / f"sample_{ts}_{score}.json"
        out.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug("Collected training sample: score=%d label=%s", score, sample["label"])

    def ready_to_train(self) -> bool:
        """Prueft ob genug Samples fuer ein Training vorhanden sind."""
        if not self.enabled:
            return False
        samples = list(self.training_data_dir.glob("sample_*.json"))
        return len(samples) >= self.min_samples

    async def train(self) -> dict[str, Any]:
        """Startet LoRA Training (nur wenn enabled + genug Samples).

        Returns: Training-Status Dict.
        """
        if not self.enabled:
            return {"status": "disabled"}

        if not self.ready_to_train():
            samples = list(self.training_data_dir.glob("sample_*.json"))
            return {"status": "insufficient_data", "samples": len(samples), "required": self.min_samples}

        if self.backend == "openai":
            return await self._train_openai()
        elif self.backend == "unsloth":
            return await self._train_unsloth()
        else:
            return {"status": "unknown_backend", "backend": self.backend}

    async def _train_openai(self) -> dict[str, Any]:
        """OpenAI Fine-Tuning API.

        1. Training-Samples → JSONL Format (OpenAI Fine-Tuning)
        2. Upload als Training-File
        3. Create Fine-Tuning Job
        4. Poll bis fertig
        5. Neues Model-ID zurueckgeben
        """
        # TODO: Implementierung wenn OpenAI Fine-Tuning aktiviert wird
        logger.info("OpenAI LoRA training: not yet implemented")
        return {"status": "not_implemented", "backend": "openai"}

    async def _train_unsloth(self) -> dict[str, Any]:
        """Self-Hosted LoRA via Unsloth auf Cloud-GPU.

        1. Training-Samples → Unsloth Format
        2. Cloud-VM starten (Modal/RunPod)
        3. Unsloth Training ausfuehren
        4. LoRA Adapter downloaden
        5. Adapter in vLLM/Ollama laden
        """
        # TODO: Implementierung wenn Self-Hosted Training aktiviert wird
        logger.info("Unsloth LoRA training: not yet implemented")
        return {"status": "not_implemented", "backend": "unsloth"}


class IdleWindowDetector:
    """OMLS — Opportunistic Meta-Learning Scheduler (MetaClaw Pattern).

    Erkennt Idle-Windows fuer Training:
    - Keyboard/Mouse inaktiv >30min
    - Nachtzeit (konfigurierbar)
    - Kein aktiver Chat-Thread

    Fuer Web-App: basiert auf letzter API-Aktivitaet statt Keyboard.
    """

    def __init__(self) -> None:
        self.idle_threshold_min = int(os.environ.get("AGENT_IDLE_THRESHOLD_MIN", "30"))
        self._last_activity: datetime | None = None

    def record_activity(self) -> None:
        """Aufgerufen bei jeder User-Interaktion."""
        self._last_activity = datetime.now()

    def is_idle(self) -> bool:
        """Prueft ob der User als inaktiv gilt."""
        if self._last_activity is None:
            return True  # Noch nie aktiv gewesen
        delta = (datetime.now() - self._last_activity).total_seconds() / 60
        return delta >= self.idle_threshold_min
