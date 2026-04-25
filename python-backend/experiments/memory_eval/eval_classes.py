"""Memory eval class taxonomy and per-class summaries."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from experiments.memory_eval.metrics import summarize_eval_run

MemoryEvalClass = Literal["verbatim", "derived", "cross_session", "forgetting"]

EVAL_CLASSES: tuple[MemoryEvalClass, ...] = (
    "verbatim",
    "derived",
    "cross_session",
    "forgetting",
)

_ALIASES = {
    "raw": "verbatim",
    "quote": "verbatim",
    "exact": "verbatim",
    "summary": "derived",
    "inference": "derived",
    "multi_session": "cross_session",
    "cross-session": "cross_session",
    "deletion": "forgetting",
    "pii_delete": "forgetting",
    "privacy": "forgetting",
}


def normalize_eval_class(value: str | None) -> MemoryEvalClass:
    text = str(value or "").strip().lower().replace("-", "_")
    text = _ALIASES.get(text, text)
    if text in EVAL_CLASSES:
        return text  # type: ignore[return-value]
    return "derived"


def classify_eval_item(item: dict[str, Any]) -> MemoryEvalClass:
    explicit = item.get("eval_class") or item.get("class") or item.get("category")
    if explicit:
        return normalize_eval_class(str(explicit))

    expected_refs = list(item.get("expected_refs") or item.get("expected_ids") or [])
    if len(expected_refs) > 1:
        return "cross_session"
    if item.get("must_forget") or item.get("deletion_expected"):
        return "forgetting"

    fact_types = {str(v or "").strip().lower() for v in list(item.get("fact_types") or [])}
    if fact_types & {"observation", "opinion", "mental_model", "summary"}:
        return "derived"

    expected_substring = str(item.get("expected_substring") or "")
    if expected_substring and item.get("requires_exact_quote", False):
        return "verbatim"
    return "derived"


def summarize_by_eval_class(run: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[MemoryEvalClass, list[dict[str, Any]]] = defaultdict(list)
    for item in list(run.get("items") or []):
        grouped[classify_eval_item(item)].append(item)

    out: dict[str, Any] = {}
    for eval_class in EVAL_CLASSES:
        items = grouped.get(eval_class, [])
        out[eval_class] = summarize_eval_run({**run, "items": items})
    return out
