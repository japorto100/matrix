from __future__ import annotations

from context.merge import merge_fragments
from context.policy import (
    BRIDGE_PERSONAL_KB_LAYER,
    BRIDGE_WORLD_LAYER,
    PERSONAL_DERIVED_LAYER,
    PERSONAL_RAW_LAYER,
    WORLD_KG_LAYER,
    apply_context_policy,
    build_degradation_flags,
    derive_context_tier,
    normalize_context_layer,
)


def test_normalize_context_layer_maps_legacy_sources() -> None:
    assert normalize_context_layer({"source": "kg"}) == WORLD_KG_LAYER
    assert normalize_context_layer({"source": "episodic"}) == PERSONAL_RAW_LAYER
    assert normalize_context_layer({"source": "vector", "fact_type": "world"}) == BRIDGE_WORLD_LAYER


def test_apply_context_policy_filters_ungrounded_and_orders_layers() -> None:
    ordered, counts, flags = apply_context_policy(
        [
            {
                "id": "raw-1",
                "sourceLayer": PERSONAL_RAW_LAYER,
                "status": "available",
            },
            {
                "id": "derived-1",
                "sourceLayer": PERSONAL_DERIVED_LAYER,
                "groundingStatus": "grounded_derived",
                "status": "available",
                "provenanceRef": "session#1",
            },
            {
                "id": "derived-2",
                "sourceLayer": PERSONAL_DERIVED_LAYER,
                "groundingStatus": "ungrounded_derived",
                "status": "available",
                "provenanceRef": "session#2",
            },
            {
                "id": "world-1",
                "sourceLayer": BRIDGE_WORLD_LAYER,
                "status": "available",
                "provenanceRef": "feed#1",
            },
        ],
        consumer="llm_agent",
    )

    assert [block["id"] for block in ordered] == ["derived-1", "raw-1", "world-1"]
    assert counts == {
        PERSONAL_DERIVED_LAYER: 1,
        PERSONAL_RAW_LAYER: 1,
        BRIDGE_WORLD_LAYER: 1,
    }
    assert "NO_PERSONAL_KB" in flags
    assert "NO_PERSONAL_MEMORY" not in flags
    assert ordered[0]["contextTier"] == "L0"
    assert ordered[1]["contextTier"] == "L1"


def test_derive_context_tier_pushes_candidate_and_world_evidence_down() -> None:
    assert derive_context_tier(
        {
            "sourceLayer": PERSONAL_DERIVED_LAYER,
            "status": "candidate",
            "relevance": 0.99,
        }
    ) == "L3"
    assert derive_context_tier(
        {
            "sourceLayer": BRIDGE_WORLD_LAYER,
            "status": "available",
            "relevance": 0.6,
        }
    ) == "L2"


def test_merge_fragments_uses_canonical_layer_order() -> None:
    merged = merge_fragments(
        [
            {
                "id": "world-kg",
                "source": "kg",
                "relevance": 0.9,
                "status": "available",
                "provenanceRef": "kg#1",
                "metadata": {"symbols": ["BTC"]},
            },
            {
                "id": "personal-raw",
                "source": "episodic",
                "relevance": 0.8,
                "metadata": {"symbols": ["ETH"]},
            },
            {
                "id": "world-evidence",
                "source": "vector",
                "fact_type": "world",
                "relevance": 0.7,
                "status": "available",
                "provenanceRef": "feed#2",
                "metadata": {"symbols": ["SOL"]},
            },
            {
                "id": "kb-1",
                "artifact_type": "pdf",
                "relevance": 0.6,
                "status": "available",
                "provenanceRef": "kb#1",
                "metadata": {"symbols": ["AAPL"]},
            },
        ]
    )

    assert [item["id"] for item in merged] == ["world-kg", "personal-raw", "kb-1", "world-evidence"]
    assert merged[0]["sourceLayer"] == WORLD_KG_LAYER
    assert merged[1]["sourceLayer"] == PERSONAL_RAW_LAYER
    assert merged[2]["sourceLayer"] == BRIDGE_PERSONAL_KB_LAYER
    assert merged[3]["sourceLayer"] == BRIDGE_WORLD_LAYER


def test_build_degradation_flags_marks_missing_layers_and_world_conflicts() -> None:
    flags = build_degradation_flags(
        source_layer_counts={PERSONAL_RAW_LAYER: 1},
        context_blocks=[
            {
                "sourceLayer": BRIDGE_WORLD_LAYER,
                "status": "conflict",
                "provenanceRef": "feed#conflict",
            }
        ],
        kg_node_count=0,
    )

    assert "NO_PERSONAL_KB" in flags
    assert "NO_WORLD_EVIDENCE" in flags
    assert "NO_WORLD_KG" in flags
    assert "WORLD_CLAIM_CONFLICT" in flags
