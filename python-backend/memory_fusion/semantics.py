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

ATTRIBUTION_CONTRACT = "memory_fusion/v1"

STATUS_AVAILABLE = "available"
STATUS_CANDIDATE = "candidate"
STATUS_GROUNDED = "grounded"
STATUS_CONTESTED = "contested"
STATUS_STALE = "stale"
PROMOTION_NOT_APPLICABLE = "not_applicable"

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


def semantic_metadata_from_tags(tags: list[Any] | None) -> dict[str, str]:
    extracted: dict[str, str] = {}
    for raw_tag in list(tags or []):
        tag = _text(raw_tag)
        if ":" not in tag:
            continue
        prefix, value = tag.split(":", 1)
        key = prefix.strip().lower()
        raw_value = value.strip()
        normalized_value = raw_value.lower()
        if key in {
            "artifact_type",
            "source_type",
            "memory_layer",
            "evidence_kind",
            "guardrail",
            "status",
            "promotion_status",
            "actor_role",
            "attribution_contract",
        } and normalized_value:
            extracted["guardrail_reason" if key == "guardrail" else key] = normalized_value
        if key in {"source_ref", "provenance_ref", "idempotency_key", "audit_event_id"} and raw_value:
            extracted.setdefault(key, raw_value)
        if key == "source_ref" and raw_value:
            extracted.setdefault("provenance_ref", raw_value)
        if key == "source_confidence" and raw_value:
            extracted.setdefault("source_confidence", raw_value)
    return extracted


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


def _explicit_memory_layer(metadata: dict[str, Any]) -> str:
    return _text(metadata.get("memory_layer")).lower()


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
    explicit_layer = _explicit_memory_layer(metadata)
    if explicit_layer in {
        PERSONAL_RAW_LAYER,
        PERSONAL_DERIVED_LAYER,
        BRIDGE_PERSONAL_KB_LAYER,
        BRIDGE_WORLD_LAYER,
    }:
        artifact_type = _text(metadata.get("artifact_type")).lower()
        source_type = _text(metadata.get("source_type")).lower()
        normalized_fact_type = _normalize_fact_type(
            _text(fact_type or metadata.get("fact_type")).lower(),
            artifact_type,
        )
        evidence_kind = _text(metadata.get("evidence_kind")).lower()
        if not evidence_kind:
            if explicit_layer == PERSONAL_DERIVED_LAYER:
                evidence_kind = DERIVED_EVIDENCE
            elif explicit_layer == PERSONAL_RAW_LAYER:
                evidence_kind = PRIMARY_EVIDENCE
            else:
                evidence_kind = EXTERNAL_EVIDENCE
        allow_default_memory_write = explicit_layer in {PERSONAL_RAW_LAYER, PERSONAL_DERIVED_LAYER}
        requires_backlinks = explicit_layer == PERSONAL_DERIVED_LAYER
        guardrail_reason = _text(metadata.get("guardrail_reason")) or None
        if not guardrail_reason and explicit_layer == BRIDGE_PERSONAL_KB_LAYER:
            guardrail_reason = "personal_kb_default_target"
        if not guardrail_reason and explicit_layer == BRIDGE_WORLD_LAYER:
            guardrail_reason = "world_model_default_target"
        return MemorySemantics(
            artifact_type=artifact_type or "memory_item",
            source_type=source_type or "unknown",
            memory_layer=explicit_layer,
            fact_type=normalized_fact_type,
            evidence_kind=evidence_kind,
            allow_default_memory_write=allow_default_memory_write,
            requires_evidence_backlinks=requires_backlinks,
            guardrail_reason=guardrail_reason,
        )

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


def _safe_float(value: Any) -> float | None:
    text = _text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{max(0.0, min(1.0, value)):.2f}".rstrip("0").rstrip(".")


def _normalize_status(value: Any) -> str:
    normalized = _text(value).lower()
    if normalized in {"", "unknown"}:
        return ""
    aliases = {
        "available": STATUS_AVAILABLE,
        "recorded": STATUS_AVAILABLE,
        "stored": STATUS_AVAILABLE,
        "candidate": STATUS_CANDIDATE,
        "draft": STATUS_CANDIDATE,
        "pending": STATUS_CANDIDATE,
        "grounded": STATUS_GROUNDED,
        "verified": STATUS_GROUNDED,
        "approved": STATUS_GROUNDED,
        "conflict": STATUS_CONTESTED,
        "conflicting": STATUS_CONTESTED,
        "contested": STATUS_CONTESTED,
        "rejected": STATUS_CONTESTED,
        "stale": STATUS_STALE,
        "expired": STATUS_STALE,
    }
    return aliases.get(normalized, normalized)


def _canonical_source_ref(metadata: dict[str, Any]) -> str:
    chunk_id = _text(metadata.get("chunk_id"))
    document_id = _text(metadata.get("document_id"))
    if explicit := _text(metadata.get("source_ref")):
        return explicit
    if provenance := _text(metadata.get("provenance_ref")):
        return provenance
    if document_id and chunk_id and "#" not in document_id:
        return f"{document_id}#{chunk_id}"
    return document_id


def _canonical_provenance_ref(metadata: dict[str, Any]) -> str:
    if provenance := _text(metadata.get("provenance_ref")):
        return provenance
    return _canonical_source_ref(metadata)


def _derive_actor_role(metadata: dict[str, Any], semantics: MemorySemantics) -> str:
    explicit = (
        _text(metadata.get("actor_role"))
        or _text(metadata.get("role"))
        or _text(metadata.get("agent_role"))
    ).lower()
    if explicit:
        return explicit
    source_type = semantics.source_type
    if source_type == "user_input":
        return "user"
    if source_type == "tool_output":
        return "tool"
    if source_type in {"agent_output", "system_observation"}:
        return "agent"
    if semantics.memory_layer in {BRIDGE_PERSONAL_KB_LAYER, BRIDGE_WORLD_LAYER}:
        return "external_source"
    return "system"


def _derive_source_confidence(metadata: dict[str, Any], semantics: MemorySemantics) -> float:
    explicit = _safe_float(metadata.get("source_confidence"))
    if explicit is not None:
        return explicit
    source_confidence_map = {
        "user_input": 1.0,
        "tool_output": 0.95,
        "external_document": 0.9,
        "world_evidence": 0.88,
        "agent_output": 0.8,
        "system_observation": 0.72,
    }
    return source_confidence_map.get(
        semantics.source_type,
        0.85 if semantics.memory_layer in {BRIDGE_PERSONAL_KB_LAYER, BRIDGE_WORLD_LAYER} else 0.8,
    )


def _derive_promotion_status(metadata: dict[str, Any], semantics: MemorySemantics) -> str:
    if semantics.memory_layer != PERSONAL_DERIVED_LAYER:
        return PROMOTION_NOT_APPLICABLE

    explicit = _normalize_status(metadata.get("promotion_status") or metadata.get("status"))
    if explicit in {STATUS_CANDIDATE, STATUS_GROUNDED, STATUS_CONTESTED, STATUS_STALE}:
        return explicit

    conflict_count = _safe_float(metadata.get("conflict_count"))
    if conflict_count is not None and conflict_count > 0:
        return STATUS_CONTESTED

    grounding_status = _text(metadata.get("grounding_status")).lower()
    if grounding_status == "ungrounded_derived":
        return STATUS_CANDIDATE

    freshness_score = _safe_float(metadata.get("freshness_score") or metadata.get("freshness"))
    if freshness_score is not None and freshness_score < 0.35:
        return STATUS_STALE

    if grounding_status == "grounded_derived":
        return STATUS_GROUNDED
    return STATUS_CANDIDATE


def metadata_tags(metadata: dict[str, Any] | None) -> list[str]:
    normalized = dict(metadata or {})
    tag_pairs = [
        ("status", _normalize_status(normalized.get("status"))),
        ("promotion_status", _normalize_status(normalized.get("promotion_status"))),
        ("source_ref", _text(normalized.get("source_ref"))),
        ("provenance_ref", _text(normalized.get("provenance_ref"))),
        ("source_confidence", _text(normalized.get("source_confidence"))),
        ("actor_role", _text(normalized.get("actor_role")).lower()),
        ("attribution_contract", _text(normalized.get("attribution_contract")).lower()),
        ("idempotency_key", _text(normalized.get("idempotency_key"))),
        ("audit_event_id", _text(normalized.get("audit_event_id"))),
    ]
    tags: list[str] = []
    for key, value in tag_pairs:
        if value:
            tags.append(f"{key}:{value}")
    return tags


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
    source_ref = _canonical_source_ref(enriched)
    provenance_ref = _canonical_provenance_ref(enriched)
    if source_ref:
        enriched["source_ref"] = source_ref
    if provenance_ref:
        enriched["provenance_ref"] = provenance_ref
    enriched["actor_role"] = _derive_actor_role(enriched, semantics)
    enriched["source_confidence"] = _format_float(_derive_source_confidence(enriched, semantics))
    enriched["attribution_contract"] = (
        _text(enriched.get("attribution_contract")).lower() or ATTRIBUTION_CONTRACT
    )
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
    promotion_status = _derive_promotion_status(enriched, semantics)
    enriched["promotion_status"] = promotion_status
    normalized_status = _normalize_status(enriched.get("status"))
    if semantics.memory_layer == PERSONAL_DERIVED_LAYER:
        enriched["status"] = promotion_status
    elif normalized_status:
        enriched["status"] = normalized_status
    elif (_safe_float(enriched.get("conflict_count")) or 0.0) > 0:
        enriched["status"] = STATUS_CONTESTED
    else:
        enriched["status"] = STATUS_AVAILABLE
    return enriched
