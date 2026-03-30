# Agent roles per AGENT_ARCHITECTURE.md Sek. 2
# Extractor, Verifier, Guard, Synthesizer

from enum import Enum


class AgentRole(str, Enum):
    """Four-role pattern for all KI workflows."""

    EXTRACTOR = "extractor"  # LLM: "Was steht im Text?"
    VERIFIER = "verifier"  # LLM + rules: "Stimmt das wirklich?"
    GUARD = "guard"  # Code-only: "Was sagen die Regeln?"
    SYNTHESIZER = "synthesizer"  # LLM: "Was bedeutet das fuer den User?"
