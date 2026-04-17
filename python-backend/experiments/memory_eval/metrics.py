"""Shared metrics for memory eval runs."""

from __future__ import annotations

from statistics import mean
from typing import Any


def recall_at_k(expected_ids: list[str], retrieved_ids: list[str]) -> float:
    if not expected_ids:
        return 0.0
    exp = set(expected_ids)
    got = set(retrieved_ids)
    return len(exp & got) / len(exp)


def top1_hit(expected_ids: list[str], retrieved_ids: list[str]) -> float:
    if not expected_ids or not retrieved_ids:
        return 0.0
    return 1.0 if retrieved_ids[0] in set(expected_ids) else 0.0


def evidence_hit(expected_substring: str, retrieved_texts: list[str]) -> float:
    needle = str(expected_substring or "").strip().lower()
    if not needle:
        return 0.0
    return 1.0 if any(needle in str(text or "").lower() for text in retrieved_texts) else 0.0


def summarize_eval_run(run: dict[str, Any]) -> dict[str, Any]:
    items = list(run.get("items") or [])
    recalls: list[float] = []
    top1_hits: list[float] = []
    evidence_hits: list[float] = []
    latencies: list[float] = []
    costs: list[float] = []
    error_count = 0
    candidate_leaks = 0
    missing_provenance = 0
    verify_required = 0

    for item in items:
        expected_ids = list(item.get("expected_ids") or [])
        retrieved_ids = list(item.get("retrieved_ids") or [])
        retrieved_texts = list(item.get("retrieved_texts") or [])
        retrieved_statuses = [str(value or "").strip().lower() for value in list(item.get("retrieved_statuses") or [])]
        retrieved_provenance = [str(value or "").strip() for value in list(item.get("retrieved_provenance") or [])]
        expected_substring = str(item.get("expected_substring") or item.get("answer") or "")

        recalls.append(recall_at_k(expected_ids, retrieved_ids))
        top1_hits.append(top1_hit(expected_ids, retrieved_ids))
        evidence_hits.append(evidence_hit(expected_substring, retrieved_texts))
        if item.get("latency_ms") is not None:
            latencies.append(float(item["latency_ms"]))
        if item.get("token_cost") is not None:
            costs.append(float(item["token_cost"]))
        if item.get("error"):
            error_count += 1
        if any(status in {"candidate", "ungrounded_derived"} for status in retrieved_statuses):
            candidate_leaks += 1
        if retrieved_ids and not any(retrieved_provenance):
            missing_provenance += 1
        if item.get("needs_verification"):
            verify_required += 1

    query_count = len(items)
    task = {
        "queries": query_count,
        "mean_recall": round(mean(recalls), 4) if recalls else 0.0,
        "top1_hit_rate": round(mean(top1_hits), 4) if top1_hits else 0.0,
    }
    quality = {
        "evidence_hit_rate": round(mean(evidence_hits), 4) if evidence_hits else 0.0,
        "retrieval_coverage": round(sum(1 for value in recalls if value > 0) / query_count, 4) if query_count else 0.0,
    }
    efficiency = {
        "mean_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
        "total_token_cost": round(sum(costs), 6),
    }
    governance = {
        "error_rate": round(error_count / query_count, 4) if query_count else 0.0,
        "candidate_leak_rate": round(candidate_leaks / query_count, 4) if query_count else 0.0,
        "missing_provenance_rate": round(missing_provenance / query_count, 4) if query_count else 0.0,
        "verification_required_rate": round(verify_required / query_count, 4) if query_count else 0.0,
    }
    return {
        "queries": query_count,
        "task": task,
        "quality": quality,
        "efficiency": efficiency,
        "governance": governance,
        # backward compatibility
        "mean_recall": task["mean_recall"],
        "mean_latency_ms": efficiency["mean_latency_ms"],
        "total_token_cost": efficiency["total_token_cost"],
        "error_rate": governance["error_rate"],
    }
