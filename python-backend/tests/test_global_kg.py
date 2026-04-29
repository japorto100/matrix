from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from memory_engine.global_kg import (
    ClaimProposal,
    EntityRef,
    EvidenceRef,
    build_conflict_key,
    decay_score,
    normalize_entity_key,
)


def test_normalize_entity_key_is_stable() -> None:
    assert normalize_entity_key("  EU Sanctions / Russia ") == "eu:sanctions:russia"


def test_claim_proposal_builds_conflict_key_claim_id_and_projection_payload() -> None:
    subject = EntityRef.from_name("European Union", entity_type="institution")
    obj = EntityRef.from_name("Russia", entity_type="country")
    evidence = EvidenceRef(
        source_layer="world_evidence",
        source_ref="doc-1",
        source_uri="https://example.invalid/source",
        content_hash="abc",
        metadata={"citation_ref": "https://example.invalid/source#chunk=1"},
    )
    proposal = ClaimProposal(
        subject=subject,
        predicate="SANCTIONED_BY",
        object_entity=obj,
        valid_from=datetime(2026, 4, 1, tzinfo=UTC),
        lane="fast",
        confidence=0.72,
        evidence=(evidence,),
    )

    assert proposal.conflict_key == build_conflict_key(
        "european:union", "SANCTIONED_BY", "russia"
    )
    assert proposal.claim_id.startswith("claim_")
    assert proposal.claim_text == "European Union SANCTIONED_BY Russia"
    payload = proposal.projection_payload()
    assert payload["predicate"] == "SANCTIONED_BY"
    assert payload["subject"]["entity_id"].startswith("ent_")
    assert payload["object"]["canonical_key"] == "russia"
    assert payload["evidence_ids"] == [evidence.evidence_id]
    assert payload["evidence_refs"] == [
        {
            "evidence_id": evidence.evidence_id,
            "source_layer": "world_evidence",
            "source_ref": "doc-1",
            "source_uri": "https://example.invalid/source",
            "content_hash": "abc",
            "quote": None,
            "metadata": {"citation_ref": "https://example.invalid/source#chunk=1"},
        }
    ]


def test_claim_proposal_requires_object() -> None:
    with pytest.raises(ValueError, match="object_entity or object_value"):
        ClaimProposal(
            subject=EntityRef.from_name("Copper"),
            predicate="AFFECTS",
            valid_from=datetime.now(UTC),
        )


def test_decay_score_halves_after_half_life() -> None:
    now = datetime(2026, 4, 27, tzinfo=UTC)
    score = decay_score(
        1.0,
        now=now,
        last_accessed=now - timedelta(days=90),
        valid_to=None,
        access_half_life_days=90,
    )

    assert score == pytest.approx(0.5)


def test_decay_score_penalizes_expired_validity() -> None:
    now = datetime(2026, 4, 27, tzinfo=UTC)
    fresh = decay_score(1.0, now=now, valid_to=now + timedelta(days=1))
    expired = decay_score(
        1.0,
        now=now,
        valid_to=now - timedelta(days=90),
        valid_half_life_days=90,
    )

    assert fresh == pytest.approx(1.0)
    assert expired == pytest.approx(0.5)
