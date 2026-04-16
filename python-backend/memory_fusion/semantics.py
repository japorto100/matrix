"""Semantic classification helpers for the personal memory fusion path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PERSONAL_RAW_LAYER = "personal_raw"
PERSONAL_DERIVED_LAYER = "personal_derived"
BRIDGE_PERSONAL_KB_LAYER = "bridge_personal_kb"
BRIDGE_WORLD_LAYER = "bridge_world"

PRIMARY_EVIDENCE = "primary"
SECONDARY_ARTIFACT = "secondary"
DERIVED_EVIDENCE = "derived"
EXTERNAL_EVIDENCE = "external"

RAW_ARTIFACT_TYPES = {"chat_turn", "tool_output", "scratch_note"}
DERIVED_ARTIFACT_TYPES = {"observation", "preference", "mental_model"}
KB_ARTIFACT_TYPES = {
    "saved_link",
    "webclip",
    "bookmark",
    "kb_note",
    "research_note",
    "pdf",
    "transcript",
    "video",
    "podcast",
    "youtube_transcript",
    "saved_file",
}
WORLD_ARTIFACT_TYPES = {
    "world_evidence",
    "global_news",
    "filing",
    "market_report",
    "market_claim",
    "world_claim",
}

KB_TAG_HINTS = {"webclip", "bookmark", "pdf", "transcript", "youtube", "podcast", "kb", "knowledgebase", "saved-link"}
WORLD_TAG_HINTS = {"world-evidence", "global", "filing", "market-report", "world-claim"}


@dataclass(frozen=True)
class MemorySemantics:
    artifact_type: str
    source_type: str
    memory_layer: str
    fact_type: str
    evidence_kind: str
    allow_default_memory_write: bool
    requires_evidence_backlinks: bool
    guardrail_reason: str | None = None

    def metadata_dict(self) -> dict[str, str]:
        out = {
            "artifact_type": self.artifact_type,
            "source_type": self.source_type,
            "memory_layer": self.memory_layer,
            "fact_type": self.fact_type,
            "evidence_kind": self.evidence_kind,
            "allow_default_memory_write": "true" if self.allow_default_memory_write else "false",
            "requires_evidence_backlinks": "true" if self.requires_evidence_backlinks else "false",
        }
        if self.guardrail_reason:
            out["guardrail_reason"] = self.guardrail_reason
        return out

    def tags(self) -> list[str]:
        tags = [
            f"artifact_type:{self.artifact_type}",
            f"source_type:{self.source_type}",
            f"memory_layer:{self.memory_layer}",
            f"evidence_kind:{self.evidence_kind}",
        ]
        if self.guardrail_reason:
            tags.append(f"guardrail:{self.guardrail_reason}")
        return tags


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tag_set(item: dict[str, Any], metadata: dict[str, Any]) -> set[str]:
    tags = set()
    for value in list(item.get("tags") or []):
        text = _text(value).lower()
        if text:
            tags.add(text)
    for value in list(metadata.get("tags") or []):
        text = _text(value).lower()
        if text:
            tags.add(text)
    return tags


def _explicit_artifact_type(item: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        _text(item.get("artifact_type"))
        or _text(metadata.get("artifact_type"))
        or ""
    ).lower()


def _explicit_source_type(item: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        _text(item.get("source_type"))
        or _text(metadata.get("source_type"))
        or ""
    ).lower()


def _explicit_fact_type(item: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        _text(item.get("fact_type"))
        or _text(metadata.get("fact_type"))
        or ""
    ).lower()


def _role(item: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        _text(item.get("role"))
        or _text(metadata.get("role"))
        or _text(metadata.get("agent_role"))
        or _text(metadata.get("actor_role"))
    ).lower()


def _normalize_fact_type(explicit_fact_type: str, artifact_type: str) -> str:
    if explicit_fact_type:
        return explicit_fact_type
    if artifact_type == "observation":
        return "observation"
    if artifact_type in {"preference", "mental_model"}:
        return "opinion"
    if artifact_type in WORLD_ARTIFACT_TYPES:
        return "world"
    return "experience"


def _guess_raw_artifact_type(explicit_source_type: str, role: str, tags: set[str]) -> str:
    if explicit_source_type == "tool_output" or "tool-output" in tags:
        return "tool_output"
    if "scratch" in tags or "session-note" in tags or "scratch-note" in tags:
        return "scratch_note"
    return "chat_turn"


def _guess_source_type(explicit_source_type: str, artifact_type: str, role: str, tags: set[str]) -> str:
    if explicit_source_type:
        return explicit_source_type
    if artifact_type == "tool_output" or "tool-output" in tags:
        return "tool_output"
    if artifact_type in DERIVED_ARTIFACT_TYPES:
        return "system_observation"
    if role in {"assistant", "agent", "system"}:
        return "agent_output"
    return "user_input"


def classify_item_semantics(item: dict[str, Any], metadata: dict[str, Any] | None = None) -> MemorySemantics:
    metadata = dict(metadata or {})
    explicit_artifact_type = _explicit_artifact_type(item, metadata)
    explicit_source_type = _explicit_source_type(item, metadata)
    explicit_fact_type = _explicit_fact_type(item, metadata)
    tags = _tag_set(item, metadata)
    role = _role(item, metadata)

    if explicit_artifact_type in KB_ARTIFACT_TYPES or tags & KB_TAG_HINTS:
        artifact_type = explicit_artifact_type or "saved_file"
        source_type = explicit_source_type or "external_document"
        return MemorySemantics(
            artifact_type=artifact_type,
            source_type=source_type,
            memory_layer=BRIDGE_PERSONAL_KB_LAYER,
            fact_type=_normalize_fact_type(explicit_fact_type, artifact_type),
            evidence_kind=EXTERNAL_EVIDENCE,
            allow_default_memory_write=False,
            requires_evidence_backlinks=False,
            guardrail_reason="personal_kb_default_target",
        )

    if explicit_artifact_type in DERIVED_ARTIFACT_TYPES or explicit_fact_type in {"observation", "opinion", "mental_model"} or {"preference", "preferences", "mental-model", "mental_model"} & tags:
        artifact_type = explicit_artifact_type or (
            "preference"
            if {"preference", "preferences"} & tags
            else "mental_model"
            if {"mental-model", "mental_model"} & tags
            else "observation"
        )
        source_type = _guess_source_type(explicit_source_type, artifact_type, role, tags)
        return MemorySemantics(
            artifact_type=artifact_type,
            source_type=source_type,
            memory_layer=PERSONAL_DERIVED_LAYER,
            fact_type=_normalize_fact_type(explicit_fact_type, artifact_type),
            evidence_kind=DERIVED_EVIDENCE,
            allow_default_memory_write=True,
            requires_evidence_backlinks=True,
        )

    if explicit_artifact_type in WORLD_ARTIFACT_TYPES or explicit_fact_type == "world" or tags & WORLD_TAG_HINTS:
        artifact_type = explicit_artifact_type or "world_evidence"
        source_type = explicit_source_type or "world_evidence"
        return MemorySemantics(
            artifact_type=artifact_type,
            source_type=source_type,
            memory_layer=BRIDGE_WORLD_LAYER,
            fact_type="world",
            evidence_kind=EXTERNAL_EVIDENCE,
            allow_default_memory_write=False,
            requires_evidence_backlinks=False,
            guardrail_reason="world_model_default_target",
        )

    artifact_type = explicit_artifact_type or _guess_raw_artifact_type(explicit_source_type, role, tags)
    source_type = _guess_source_type(explicit_source_type, artifact_type, role, tags)
    evidence_kind = SECONDARY_ARTIFACT if source_type == "agent_output" else PRIMARY_EVIDENCE
    return MemorySemantics(
        artifact_type=artifact_type,
        source_type=source_type,
        memory_layer=PERSONAL_RAW_LAYER,
        fact_type=_normalize_fact_type(explicit_fact_type, artifact_type),
        evidence_kind=evidence_kind,
        allow_default_memory_write=True,
        requires_evidence_backlinks=False,
    )


def classify_result_semantics(metadata: dict[str, Any] | None, *, fact_type: str | None = None) -> MemorySemantics:
    metadata = dict(metadata or {})
    item = {
        "artifact_type": metadata.get("artifact_type"),
        "source_type": metadata.get("source_type"),
        "fact_type": fact_type or metadata.get("fact_type"),
        "tags": list(metadata.get("tags") or []),
        "role": metadata.get("role") or metadata.get("agent_role"),
    }
    return classify_item_semantics(item, metadata)


def has_evidence_backlinks(metadata: dict[str, Any] | None) -> bool:
    metadata = dict(metadata or {})
    backlink_fields = (
        "provenance_ref",
        "source_ref",
        "source_fact_ids",
        "evidence_refs",
        "document_id",
        "chunk_id",
    )
    for field in backlink_fields:
        value = metadata.get(field)
        if isinstance(value, (list, tuple, set)):
            if any(_text(entry) for entry in value):
                return True
            continue
        if _text(value):
            return True
    return False


def enrich_metadata_with_semantics(
    metadata: dict[str, Any] | None,
    *,
    item: dict[str, Any] | None = None,
    fact_type: str | None = None,
) -> dict[str, Any]:
    metadata = dict(metadata or {})
    semantics = (
        classify_item_semantics(item or {}, metadata)
        if item is not None
        else classify_result_semantics(metadata, fact_type=fact_type)
    )
    enriched = {**metadata, **semantics.metadata_dict()}
    backlinks_present = has_evidence_backlinks(enriched)
    enriched["evidence_backlinks_present"] = "true" if backlinks_present else "false"
    if semantics.requires_evidence_backlinks and not backlinks_present:
        enriched["grounding_status"] = "ungrounded_derived"
        enriched["derived_without_evidence"] = "true"
    elif semantics.requires_evidence_backlinks:
        enriched["grounding_status"] = "grounded_derived"
        enriched["derived_without_evidence"] = "false"
    else:
        enriched["grounding_status"] = "not_applicable"
        enriched["derived_without_evidence"] = "false"
    return enriched
