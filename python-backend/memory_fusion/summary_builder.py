"""Retain-item normalization for the summary/verbatim routes in memory_fusion."""

from __future__ import annotations

from typing import Any

from memory_fusion.evidence_trace import ensure_memory_trace_metadata
from memory_fusion.loci import derive_loci_metadata, loci_tags
from memory_fusion.semantics import (
    classify_item_semantics,
    enrich_metadata_with_semantics,
    metadata_tags,
)


def _stringify_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in dict(metadata or {}).items()
        if value is not None
    }


def build_summary_item(item: dict[str, Any], *, bank_id: str | None = None) -> dict[str, Any]:
    """Prepare one raw item for the summary route.

    Wichtig: keine lokale Pseudo-Summary mehr bauen. Die semantische
    Verdichtung passiert ueber echte Hindsight-Regeln/Strategien.
    """
    metadata = dict(item.get("metadata") or {})
    semantics = classify_item_semantics(item, metadata)
    preflight_metadata = enrich_metadata_with_semantics(metadata, item=item)
    if semantics.requires_evidence_backlinks and preflight_metadata.get("evidence_backlinks_present") != "true":
        raise ValueError("Derived memory items require evidence backlinks in memory_fusion")
    loci = derive_loci_metadata(
        {**item, "artifact_type": semantics.artifact_type, "source_type": semantics.source_type},
        _stringify_metadata({**metadata, **semantics.metadata_dict()}),
        bank_id=bank_id,
    )
    metadata = ensure_memory_trace_metadata(
        enrich_metadata_with_semantics({**metadata, **loci}, item=item),
        bank_id=bank_id,
        route="summary",
        action="retain",
    )
    return {
        **item,
        "context": f"summary:{loci['source_ref']}" if loci["source_ref"] else str(item.get("context") or "summary"),
        "tags": loci_tags(
            {"tags": list(item.get("tags") or []) + semantics.tags() + metadata_tags(metadata)},
            loci,
        ),
        "metadata": {
            **_stringify_metadata(metadata),
            "fusion_route": "summary",
        },
        "fact_type": semantics.fact_type,
    }


def build_verbatim_item(item: dict[str, Any], *, bank_id: str | None = None) -> dict[str, Any]:
    """Prepare one raw item for the verbatim route."""
    metadata = dict(item.get("metadata") or {})
    semantics = classify_item_semantics(item, metadata)
    preflight_metadata = enrich_metadata_with_semantics(metadata, item=item)
    if semantics.requires_evidence_backlinks and preflight_metadata.get("evidence_backlinks_present") != "true":
        raise ValueError("Derived memory items require evidence backlinks in memory_fusion")
    loci = derive_loci_metadata(
        {**item, "artifact_type": semantics.artifact_type, "source_type": semantics.source_type},
        _stringify_metadata({**metadata, **semantics.metadata_dict()}),
        bank_id=bank_id,
    )
    metadata = ensure_memory_trace_metadata(
        enrich_metadata_with_semantics({**metadata, **loci}, item=item),
        bank_id=bank_id,
        route="verbatim",
        action="retain",
    )
    return {
        **item,
        "tags": loci_tags(
            {"tags": list(item.get("tags") or []) + semantics.tags() + metadata_tags(metadata)},
            loci,
        ),
        "metadata": {
            **_stringify_metadata(metadata),
            "fusion_route": "verbatim",
        },
        "fact_type": semantics.fact_type,
    }
