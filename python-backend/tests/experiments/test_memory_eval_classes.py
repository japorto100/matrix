from __future__ import annotations

from experiments.memory_eval.eval_classes import (
    classify_eval_item,
    summarize_by_eval_class,
)


def test_classify_memory_eval_classes() -> None:
    assert classify_eval_item({"eval_class": "verbatim"}) == "verbatim"
    assert classify_eval_item({"category": "multi_session"}) == "cross_session"
    assert classify_eval_item({"must_forget": True}) == "forgetting"
    assert classify_eval_item({"fact_types": ["observation"]}) == "derived"


def test_summarize_by_eval_class_keeps_efficiency_and_governance() -> None:
    summary = summarize_by_eval_class(
        {
            "items": [
                {
                    "eval_class": "verbatim",
                    "expected_ids": ["a"],
                    "retrieved_ids": ["a"],
                    "retrieved_texts": ["exact answer"],
                    "expected_substring": "exact",
                    "latency_ms": 12,
                    "token_cost": 0.01,
                    "retrieved_provenance": ["source#1"],
                },
                {
                    "eval_class": "forgetting",
                    "expected_ids": ["deleted"],
                    "retrieved_ids": [],
                    "needs_verification": True,
                },
            ]
        }
    )

    assert summary["verbatim"]["task"]["mean_recall"] == 1.0
    assert summary["verbatim"]["efficiency"]["mean_latency_ms"] == 12
    assert summary["verbatim"]["efficiency"]["total_token_cost"] == 0.01
    assert summary["verbatim"]["governance"]["missing_provenance_rate"] == 0.0
    assert summary["forgetting"]["governance"]["verification_required_rate"] == 1.0
