"""Unified catalog metadata for builtin agent tools.

This layer is intentionally separate from ``ToolRegistry`` execution so policy,
UI and Meta-Harness can inspect normal tools without changing how tools run.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
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


def _tool_group(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    if "memory" in text or "remember" in text:
        return "memory"
    if "semantic" in text or "metric" in text or "provenance" in text:
        return "semantic"
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


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
