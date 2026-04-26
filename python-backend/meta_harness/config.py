"""Harness Config — serializable representation of the agent's harness (exec-17).

The Meta-Harness paper shows that automated optimization requires machine-readable
access to the harness "source code". For us, the harness is:
- System prompts per role
- Tool registry (which tools are available)
- Memory settings per role (recall tags, write-enabled)
- Consent config (rate limits, timeouts)
- Graph structure

This module serializes the current config to JSON and can load/compare variants.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HarnessConfig:
    """Serializable snapshot of the agent harness configuration."""

    version: str = ""
    roles: dict[str, dict[str, Any]] = field(default_factory=dict)
    tools: list[dict[str, str]] = field(default_factory=list)
    memory_config: dict[str, dict[str, Any]] = field(default_factory=dict)
    runtime_config: dict[str, Any] = field(default_factory=dict)
    consent_config: dict[str, Any] = field(default_factory=dict)
    graph_flow: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    @classmethod
    def from_json(cls, data: str) -> HarnessConfig:
        return cls(**json.loads(data))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> HarnessConfig:
        return cls.from_json(path.read_text(encoding="utf-8"))


def capture_current_config() -> HarnessConfig:
    """Capture a snapshot of the current live agent harness configuration."""
    config = HarnessConfig(
        graph_flow=(
            "START → memory_recall → llm_call → "
            "[approval_gate → tool_execute → increment]* → memory_retain → END"
        ),
    )

    # System prompts per role
    try:
        from agent.roles import TRADING_ROLE_PROMPTS

        config.roles = {
            r.value: {"system_prompt": p, "prompt_length": len(p)}
            for r, p in TRADING_ROLE_PROMPTS.items()
        }
    except Exception:
        pass

    # Tool registry
    try:
        from agent.tools.registry import ToolRegistry

        registry = ToolRegistry.load()
        config.tools = [
            {
                "name": t.definition()["name"],
                "description": t.definition().get("description", "")[:200],
            }
            for t in registry.all()
        ]
    except Exception:
        pass

    # Memory config per role
    try:
        from agent.roles import TRADING_ROLE_MEMORY

        config.memory_config = {r.value: c for r, c in TRADING_ROLE_MEMORY.items()}
    except Exception:
        pass

    config.runtime_config = {
        "memory": {
            "agent_memory_engine": os.environ.get("AGENT_MEMORY_ENGINE", "auto"),
            "embedding_provider": os.environ.get("MEMORY_EMBEDDING_PROVIDER", "openrouter"),
            "embedding_model": os.environ.get("MEMORY_EMBEDDING_MODEL", ""),
            "embedding_base_url": os.environ.get("MEMORY_EMBEDDING_BASE_URL", ""),
            "fusion_verbatim_backend": os.environ.get("MEMORY_FUSION_VERBATIM_BACKEND", "mempalace"),
            "hindsight_reranker_provider": os.environ.get("HINDSIGHT_API_RERANKER_PROVIDER", "rrf"),
            "bank_id_shape": "user_{user_id}",
            "pareto_hypotheses": [
                "embedding_model_dimension_quality_cost",
                "reranker_strategy_quality_latency_cost",
                "mempalace_trigger_policy_context_bloat",
            ],
        }
    }

    # Consent config
    try:
        from agent.consent.config import get_consent_config

        cc = get_consent_config()
        config.consent_config = {
            "max_iterations": cc.rate_limits.get_max_iterations(),
            "tool_timeout_sec": cc.rate_limits.get_tool_timeout(),
        }
    except Exception:
        pass

    return config
