"""Evidence trace metadata helpers for memory_fusion."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_NON_REF_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _ref_part(value: Any, *, fallback: str) -> str:
    text = _text(value)
    if not text:
        return fallback
    return _NON_REF_RE.sub("-", text).strip("-")[:160] or fallback


def _source_file_ref(metadata: dict[str, Any]) -> str:
    source_file = _text(metadata.get("source_file"))
    if not source_file:
        return ""
    chunk = _text(metadata.get("chunk_id") or metadata.get("chunk_index") or "0")
    return f"{Path(source_file).name}#{chunk}"


def raw_evidence_ref(metadata: dict[str, Any]) -> str:
    """Return the best durable raw evidence reference available in metadata."""
    for key in (
        "raw_evidence_ref",
        "source_ref",
        "provenance_ref",
        "audit_event_id",
        "idempotency_key",
    ):
        value = metadata.get(key)
        if isinstance(value, (list, tuple, set)):
            for entry in value:
                if text := _text(entry):
                    return text
            continue
        if text := _text(value):
            return text

    document_id = _text(metadata.get("document_id"))
    chunk_id = _text(metadata.get("chunk_id"))
    if document_id and chunk_id and "#" not in document_id:
        return f"{document_id}#{chunk_id}"
    if document_id:
        return document_id
    return _source_file_ref(metadata)


def ensure_memory_trace_metadata(
    metadata: dict[str, Any],
    *,
    bank_id: str | None = None,
    route: str | None = None,
    action: str = "memory",
) -> dict[str, Any]:
    """Add provider-free trace fields without overwriting caller-provided IDs."""
    enriched = dict(metadata or {})
    evidence_ref = raw_evidence_ref(enriched)
    if evidence_ref:
        enriched.setdefault("raw_evidence_ref", evidence_ref)

    if "source_status" not in enriched:
        enriched["source_status"] = "durable" if evidence_ref else "unreferenced"

    if evidence_ref:
        bank_part = _ref_part(bank_id or enriched.get("bank_id"), fallback="bank")
        route_part = _ref_part(route or enriched.get("fusion_route"), fallback="route")
        ref_part = _ref_part(evidence_ref, fallback="evidence")
        enriched.setdefault("operation_log_id", f"memory-op:{action}:{bank_part}:{route_part}:{ref_part}")
        enriched.setdefault("diff_ref", f"memory-diff:{bank_part}:{route_part}:{ref_part}")
    return enriched
