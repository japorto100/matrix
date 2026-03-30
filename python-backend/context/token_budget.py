# Token Budget Manager — Phase 10b.2
# Ref: CONTEXT_ENGINEERING.md Sek. 5

from __future__ import annotations

from typing import Any

# CE Sek. 5.1 — Budget pro Modell-Klasse
BUDGET_TABLE = {
    "small": {
        "total": 6000,
        "system": 400,
        "kg_slice": 600,
        "episodic": 300,
        "vector_rag": 500,
        "current_input": 3500,
        "reserve": 700,
    },
    "medium": {
        "total": 20000,
        "system": 500,
        "kg_slice": 1500,
        "episodic": 800,
        "vector_rag": 2000,
        "current_input": 12000,
        "reserve": 3200,
    },
    "large": {
        "total": 40000,
        "system": 500,
        "kg_slice": 3000,
        "episodic": 2000,
        "vector_rag": 5000,
        "current_input": 25000,
        "reserve": 4500,
    },
}


def _estimate_tokens(text: str | list | dict) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    if isinstance(text, str):
        return max(1, len(text) // 4)
    if isinstance(text, list):
        return sum(_estimate_tokens(t) for t in text)
    if isinstance(text, dict):
        return _estimate_tokens(str(text))
    return 0


def allocate_budget(
    model_class: str = "medium",
    available_context: dict[str, Any] | None = None,
) -> dict[str, int]:
    """
    Allocate token budget per slot. CE Sek. 5.2.
    Returns allocation dict: system, kg_slice, episodic, vector_rag, current_input, reserve.
    """
    available_context = available_context or {}
    base = BUDGET_TABLE.get(model_class, BUDGET_TABLE["medium"]).copy()
    allocation: dict[str, int] = {}
    remaining = base["total"]

    allocation["system"] = base["system"]
    remaining -= base["system"]

    slots = ["kg_slice", "episodic", "vector_rag", "current_input"]
    for slot in slots:
        content = available_context.get(slot)
        if content:
            actual = _estimate_tokens(content)
            used = min(actual, base[slot])
            allocation[slot] = used
            remaining -= used
        else:
            allocation[slot] = 0

    allocation["reserve"] = max(0, remaining)
    return allocation


class TokenBudgetManager:
    """
    Manages token budget per session. Phase 10b.2.
    Prioritizes slots when overflow: current_input > kg > episodic > vector.
    """

    def __init__(self, model_class: str = "medium"):
        self.model_class = model_class
        self._allocation: dict[str, int] = {}

    def allocate(self, available_context: dict[str, Any] | None = None) -> dict[str, int]:
        self._allocation = allocate_budget(self.model_class, available_context)
        return self._allocation

    def fits(self, slot: str, content: str | list | dict) -> bool:
        """Check if content fits in slot budget."""
        budget = self._allocation.get(slot, 0)
        return _estimate_tokens(content) <= budget

    def truncate_to_fit(
        self,
        slot: str,
        content: str,
        *,
        suffix: str = "...",
    ) -> str:
        """Truncate content to fit slot budget. Simple char-based truncation."""
        budget = self._allocation.get(slot, 500)
        max_chars = budget * 4  # ~4 chars per token
        if len(content) <= max_chars:
            return content
        return content[: max_chars - len(suffix)] + suffix
