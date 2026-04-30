"""Unified catalog metadata for builtin agent tools.

This layer is intentionally separate from ``ToolRegistry`` execution so policy,
UI and Meta-Harness can inspect normal tools without changing how tools run.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from math import log
from typing import Any, Literal

from agent.tools.base import TradingTool

ToolRisk = Literal["low", "medium", "high", "critical"]
ApprovalMode = Literal["auto", "inform", "confirm", "deny"]
ToolSource = Literal["builtin", "mcp", "skill", "a2a"]

_HIGH_RISK_PATTERNS = (
    re.compile(r"\bdelete\b", re.I),
    re.compile(r"\bcancel\b", re.I),
    re.compile(r"\boverwrite\b", re.I),
    re.compile(r"\bsandbox\b", re.I),
    re.compile(r"\bbrowser\b", re.I),
    re.compile(r"\bfile\b", re.I),
)
_MEMORY_PATTERNS = (re.compile(r"\bmemory\b", re.I), re.compile(r"\bremember\b", re.I))
_UI_PATTERNS = (
    re.compile(r"\bcanvas\b", re.I),
    re.compile(r"\bchart\b", re.I),
    re.compile(r"\ba2ui\b", re.I),
    re.compile(r"\bsurface\b", re.I),
)


@dataclass(frozen=True)
class ToolCatalogEntry:
    id: str
    name: str
    source: ToolSource
    group: str
    summary: str
    description_hash: str
    input_schema_hash: str
    risk: ToolRisk
    approval: ApprovalMode
    progressive_disclosure_level: int
    enabled: bool = True
    policy_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["policy_reasons"] = list(self.policy_reasons)
        return payload


def catalog_entry_for_tool(tool: TradingTool) -> ToolCatalogEntry:
    definition = tool.definition()
    name = str(definition.get("name") or tool.name)
    description = str(definition.get("description") or "")
    schema = definition.get("input_schema") or {}
    group = _tool_group(name, description)
    risk, reasons = _tool_risk(name, description, group)
    approval = _approval_mode(name, risk, group)
    return ToolCatalogEntry(
        id=f"builtin:{name}",
        name=name,
        source="builtin",
        group=group,
        summary=_tool_summary(description),
        description_hash=_stable_hash(description),
        input_schema_hash=_stable_hash(schema),
        risk=risk,
        approval=approval,
        progressive_disclosure_level=_disclosure_level(risk, group),
        enabled=True,
        policy_reasons=tuple(reasons),
    )


def builtin_tool_catalog(tools: list[TradingTool]) -> list[ToolCatalogEntry]:
    return sorted((catalog_entry_for_tool(tool) for tool in tools), key=lambda e: e.name)


def visible_tool_summaries(
    entries: list[ToolCatalogEntry],
    *,
    allowed_groups: set[str] | None = None,
    allowed_tools: set[str] | None = None,
    max_level: int = 2,
) -> list[dict[str, Any]]:
    """Return short progressive-disclosure records safe for prompt/UI use."""

    visible: list[dict[str, Any]] = []
    for entry in entries:
        if allowed_groups is not None and entry.group not in allowed_groups:
            continue
        if allowed_tools is not None and entry.name not in allowed_tools:
            continue
        if entry.progressive_disclosure_level > max_level:
            continue
        visible.append(
            {
                "name": entry.name,
                "group": entry.group,
                "summary": entry.summary,
                "risk": entry.risk,
                "approval": entry.approval,
            }
        )
    return visible


def search_tool_catalog(
    entries: list[ToolCatalogEntry],
    query: str,
    *,
    limit: int = 5,
    allowed_groups: set[str] | None = None,
    allowed_tools: set[str] | None = None,
    max_level: int = 2,
) -> list[dict[str, Any]]:
    """Search visible tools without exposing full schemas to the model."""

    q_tokens = _search_tokens(query)
    candidates = [
        entry
        for entry in entries
        if entry.enabled
        and entry.progressive_disclosure_level <= max_level
        and (allowed_groups is None or entry.group in allowed_groups)
        and (allowed_tools is None or entry.name in allowed_tools)
    ]
    if not candidates:
        return []
    if not q_tokens:
        return [
            _search_result(entry, score=0.0, matched_terms=())
            for entry in candidates[: max(0, limit)]
        ]

    docs = {
        entry.name: _search_tokens(
            " ".join(
                (
                    entry.name,
                    entry.group,
                    entry.summary,
                    entry.risk,
                    entry.approval,
                    " ".join(entry.policy_reasons),
                )
            )
        )
        for entry in candidates
    }
    document_count = len(docs)
    doc_freq: dict[str, int] = {}
    for tokens in docs.values():
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1

    ranked: list[tuple[float, ToolCatalogEntry, tuple[str, ...]]] = []
    for entry in candidates:
        tokens = docs[entry.name]
        if not tokens:
            continue
        matched = tuple(sorted(set(q_tokens) & set(tokens)))
        if not matched:
            continue
        score = 0.0
        length_norm = 1 + (len(tokens) / 20)
        for term in q_tokens:
            tf = tokens.count(term)
            if not tf:
                continue
            idf = log((document_count + 1) / (doc_freq.get(term, 0) + 0.5)) + 1
            score += (tf / length_norm) * idf
        if entry.name.lower() in query.lower():
            score += 2.0
        ranked.append((score, entry, matched))

    ranked.sort(key=lambda item: (-item[0], item[1].progressive_disclosure_level, item[1].name))
    return [
        _search_result(entry, score=score, matched_terms=matched)
        for score, entry, matched in ranked[: max(0, limit)]
    ]


def _tool_group(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    if "memory" in text or "remember" in text:
        return "memory"
    if name == "retrieve_context" or "retrieval" in text or "retrieve" in text:
        return "retrieval"
    if "semantic" in text or "metric" in text or "provenance" in text:
        return "semantic"
    if "report" in text or "citation" in text or "renderer" in text:
        return "report"
    if "sandbox" in text or "browser" in text or "file" in text:
        return "code_execution"
    if "schedule" in text or "task" in text or "cron" in text:
        return "automation"
    if "canvas" in text or "chart" in text or "a2ui" in text or "surface" in text:
        return "ui"
    if "portfolio" in text or "geomap" in text:
        return "market"
    return "general"


def _tool_risk(name: str, description: str, group: str) -> tuple[ToolRisk, list[str]]:
    text = f"{name} {description}"
    reasons: list[str] = []
    if any(pattern.search(text) for pattern in _HIGH_RISK_PATTERNS):
        reasons.append("high-risk-action")
    if group == "code_execution":
        reasons.append("code-execution")
    if group == "automation" and any(word in name for word in ("cancel", "edit", "run_now")):
        reasons.append("automation-mutation")
    if group == "memory" and any(pattern.search(text) for pattern in _MEMORY_PATTERNS):
        reasons.append("memory-access")
    if group == "ui" and any(pattern.search(text) for pattern in _UI_PATTERNS):
        reasons.append("ui-state")

    if "code-execution" in reasons:
        return "critical", reasons
    if "high-risk-action" in reasons or "automation-mutation" in reasons:
        return "high", reasons
    if "memory-access" in reasons or "ui-state" in reasons:
        return "medium", reasons
    return "low", reasons


def _approval_mode(name: str, risk: ToolRisk, group: str) -> ApprovalMode:
    if risk == "critical":
        return "confirm"
    if risk == "high":
        return "confirm"
    if group == "memory" and name in {"memory_add", "save_memory"}:
        return "confirm"
    if risk == "medium":
        return "inform"
    return "auto"


def _disclosure_level(risk: ToolRisk, group: str) -> int:
    if risk in {"critical", "high"}:
        return 3
    if group in {"memory", "automation", "ui"}:
        return 2
    return 1


def _tool_summary(description: str) -> str:
    text = " ".join(str(description or "").split())
    if len(text) <= 180:
        return text
    return text[:177].rstrip() + "..."


def _search_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"[a-z0-9_]{2,}", str(text).lower()):
        tokens.append(raw)
        if "_" in raw:
            tokens.extend(part for part in raw.split("_") if len(part) >= 2)
    return [
        token
        for token in tokens
        if token not in {"the", "and", "for", "with", "tool", "tools", "use"}
    ]


def _search_result(
    entry: ToolCatalogEntry,
    *,
    score: float,
    matched_terms: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "name": entry.name,
        "group": entry.group,
        "summary": entry.summary,
        "risk": entry.risk,
        "approval": entry.approval,
        "progressive_disclosure_level": entry.progressive_disclosure_level,
        "score": round(score, 4),
        "matched_terms": list(matched_terms),
    }


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
