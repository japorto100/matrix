from __future__ import annotations

import pytest

from memory_engine.global_kg import EvidenceRef
from memory_engine.kg_validation import (
    NoOpGraphMERTValidator,
    RuleBasedWisdomValidator,
    TripleValidationInput,
    supports_slow_lane_promotion,
)


def _evidence(ref: str = "doc-1") -> EvidenceRef:
    return EvidenceRef(source_layer="world_evidence", source_ref=ref)


@pytest.mark.asyncio
async def test_noop_graphmert_validator_skips_without_checkpoint() -> None:
    result = await NoOpGraphMERTValidator().validate(
        TripleValidationInput(
            subject_key="eu",
            predicate="SANCTIONED_BY",
            object_key="russia",
            evidence=(_evidence(),),
        )
    )

    assert result.decision == "skipped"
    assert result.reason == "no_graphmert_checkpoint_configured"
    assert supports_slow_lane_promotion(result) is False


@pytest.mark.asyncio
async def test_wisdom_validator_never_blocks_fast_lane_inline() -> None:
    result = await RuleBasedWisdomValidator().validate(
        TripleValidationInput(
            subject_key="eu",
            predicate="SANCTIONED_BY",
            object_key="russia",
            lane="fast",
            evidence=(_evidence(),),
        )
    )

    assert result.decision == "skipped"
    assert result.reason == "fast_lane_not_validated_inline"
    assert supports_slow_lane_promotion(result) is False


@pytest.mark.asyncio
async def test_wisdom_validator_rejects_missing_evidence() -> None:
    result = await RuleBasedWisdomValidator().validate(
        TripleValidationInput(
            subject_key="eu",
            predicate="SANCTIONED_BY",
            object_key="russia",
        )
    )

    assert result.decision == "reject"
    assert result.reason == "missing_evidence"
    assert supports_slow_lane_promotion(result) is False


@pytest.mark.asyncio
async def test_wisdom_validator_supports_evidence_backed_slow_lane_claim() -> None:
    result = await RuleBasedWisdomValidator().validate(
        TripleValidationInput(
            subject_key="eu",
            predicate="SANCTIONED_BY",
            object_key="russia",
            evidence=(_evidence("doc-1"), _evidence("doc-2")),
        )
    )

    assert result.decision == "support"
    assert result.score and result.score >= 0.65
    assert result.corroboration_count == 2
    assert supports_slow_lane_promotion(result) is True
    assert result.as_metadata()["validator_version"] == "rules:2026-04-27"


@pytest.mark.asyncio
async def test_wisdom_validator_rejects_self_relation_hard_negative() -> None:
    result = await RuleBasedWisdomValidator().validate(
        TripleValidationInput(
            subject_key="russia",
            predicate="SANCTIONED_BY",
            object_key="russia",
            evidence=(_evidence(),),
        )
    )

    assert result.decision == "reject"
    assert result.reason == "self_relation_hard_negative"
    assert supports_slow_lane_promotion(result) is False
