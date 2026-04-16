"""Run a larger synthetic long-context smoke for summary/verbatim/fusion.

Ziel:
- ca. 100k+ Kontext
- `summary` Route ueber echte Hindsight-Regeln/Strategien
- `verbatim` Route ueber raw/verbatim evidence
- `fusion` Route als best-of-both

Metriken:
- recall@k auf `source_ref`
- top1 hit rate
- evidence hit rate fuer Queries mit erwartetem exakten Substring
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import string
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_fusion.fusion_engine import FusionMemoryEngine  # noqa: E402


def _animals() -> list[str]:
    return [
        "otter",
        "falcon",
        "badger",
        "lynx",
        "ibis",
        "orca",
        "puma",
        "raven",
        "gecko",
        "yak",
    ]


def _filler(seed: int, words: int = 120) -> str:
    rng = random.Random(seed)
    vocab = [
        "market",
        "structure",
        "volatility",
        "energy",
        "macro",
        "inventory",
        "breakout",
        "timezone",
        "discipline",
        "execution",
        "positioning",
        "hedging",
    ]
    return " ".join(rng.choice(vocab) for _ in range(words)).capitalize() + "."


def build_long_context_fixture(session_count: int = 64) -> dict[str, Any]:
    items = []
    queries = []
    instruments = ["Brent", "WTI", "Gold", "EUR/USD"]
    styles = ["swing", "position", "mean-reversion", "breakout"]
    animals = _animals()

    for idx in range(session_count):
        instrument = instruments[idx % len(instruments)]
        style = styles[idx % len(styles)]
        token = f"{animals[idx % len(animals)]}-{idx:03d}-" + "".join(
            string.ascii_lowercase[(idx + j) % 26] for j in range(6)
        )
        source_ref = f"session-{idx:03d}.jsonl#0"
        text = " ".join(
            [
                f"Session {idx}: The user currently prefers {style} trading on {instrument} and wants calmer execution.",
                _filler(idx * 11 + 1, words=80),
                "The assistant discussed risk budgeting, fewer but higher conviction setups, and avoiding impulsive entries.",
                f"The archive token mentioned only in passing was {token} and it should remain verbatim evidence.",
                _filler(idx * 17 + 3, words=85),
                f"Closing note: for session {idx}, the priority remained {style} execution on {instrument}.",
            ]
        )
        items.append(
            {
                "source_ref": source_ref,
                "source_file": f"session-{idx:03d}.jsonl",
                "text": text,
                "fact_type": "experience",
                "artifact_type": "chat_turn",
                "source_type": "user_input",
                "tags": ["long-context", instrument.lower().replace("/", "-"), style],
            }
        )

        if idx < 8:
            queries.append(
                {
                    "query": f"What archive token was mentioned in session {idx}?",
                    "expected_refs": [source_ref],
                    "expected_substring": token,
                    "category": "verbatim",
                    "fact_types": ["experience"],
                    "expected_memory_layer": "personal_raw",
                }
            )
            queries.append(
                {
                    "query": f"What instrument and style did the user prefer in session {idx}?",
                    "expected_refs": [source_ref],
                    "expected_substring": f"{style} trading on {instrument}",
                    "category": "derived",
                    "fact_types": ["experience", "observation", "opinion"],
                }
            )

    for idx in range(6):
        instrument = instruments[idx % len(instruments)]
        old_style = styles[idx % len(styles)]
        new_style = styles[(idx + 1) % len(styles)]
        old_ref = f"profile-{idx:02d}-old.jsonl#0"
        new_ref = f"profile-{idx:02d}-new.jsonl#0"
        items.append(
            {
                "source_ref": old_ref,
                "source_file": f"profile-{idx:02d}-old.jsonl",
                "text": " ".join(
                    [
                        f"Profile {idx} historical note: the user used to prefer {old_style} trading on {instrument}.",
                        _filler(700 + idx * 9, words=70),
                        "This was the old state before a later correction.",
                    ]
                ),
                "fact_type": "opinion",
                "artifact_type": "preference",
                "source_type": "system_observation",
                "tags": ["long-context", "historical", instrument.lower().replace("/", "-"), old_style],
            }
        )
        items.append(
            {
                "source_ref": new_ref,
                "source_file": f"profile-{idx:02d}-new.jsonl",
                "text": " ".join(
                    [
                        f"Profile {idx} update: the latest true preference is calm {new_style} trading on {instrument}.",
                        "This newer note explicitly replaces the earlier historical preference.",
                        _filler(900 + idx * 13, words=80),
                    ]
                ),
                "fact_type": "opinion",
                "artifact_type": "preference",
                "source_type": "system_observation",
                "tags": ["long-context", "latest-preference", instrument.lower().replace("/", "-"), new_style],
            }
        )
        queries.append(
            {
                "query": f"What is the latest confirmed preference for profile {idx} on {instrument}?",
                "expected_refs": [new_ref],
                "expected_substring": f"latest true preference is calm {new_style} trading on {instrument}",
                "category": "forgetting",
                "fact_types": ["opinion", "observation"],
                "expected_memory_layer": "personal_derived",
            }
        )

    for idx in range(4):
        instrument = instruments[idx % len(instruments)]
        room = f"duplicate-cluster-{idx}"
        token_a = f"dupA-{idx:02d}-" + "".join(string.ascii_lowercase[(idx + j) % 26] for j in range(5))
        token_b = f"dupB-{idx:02d}-" + "".join(string.ascii_lowercase[(idx + j + 7) % 26] for j in range(5))
        ref_a = f"{room}-a.jsonl#0"
        ref_b = f"{room}-b.jsonl#0"
        common_prefix = f"Duplicate cluster {idx}: both notes discussed calm execution on {instrument} with very similar wording."
        items.append(
            {
                "source_ref": ref_a,
                "source_file": f"{room}-a.jsonl",
                "text": " ".join(
                    [
                        common_prefix,
                        f"The evidence token for the morning variant was {token_a}.",
                        _filler(1100 + idx * 19, words=75),
                    ]
                ),
                "fact_type": "experience",
                "artifact_type": "chat_turn",
                "source_type": "user_input",
                "tags": ["long-context", "near-duplicate", instrument.lower().replace("/", "-"), "morning"],
            }
        )
        items.append(
            {
                "source_ref": ref_b,
                "source_file": f"{room}-b.jsonl",
                "text": " ".join(
                    [
                        common_prefix,
                        f"The evidence token for the evening variant was {token_b}.",
                        _filler(1300 + idx * 23, words=75),
                    ]
                ),
                "fact_type": "experience",
                "artifact_type": "chat_turn",
                "source_type": "user_input",
                "tags": ["long-context", "near-duplicate", instrument.lower().replace("/", "-"), "evening"],
            }
        )
        queries.append(
            {
                "query": f"What evidence token belonged to the evening variant in duplicate cluster {idx}?",
                "expected_refs": [ref_b],
                "expected_substring": token_b,
                "category": "cross_session",
                "fact_types": ["experience"],
                "expected_memory_layer": "personal_raw",
            }
        )

    total_chars = sum(len(item["text"]) for item in items)
    return {
        "corpus_id": "synthetic-long-context",
        "bank_id": "user_eval_long_context",
        "user_id": "eval-long-context",
        "items": items,
        "queries": queries,
        "total_chars": total_chars,
    }


def _recall_at_k(expected_refs: list[str], retrieved_refs: list[str]) -> float:
    if not expected_refs:
        return 0.0
    exp = set(expected_refs)
    got = set(retrieved_refs)
    return len(exp & got) / len(exp)


def _top1_hit(expected_refs: list[str], retrieved_refs: list[str]) -> float:
    if not expected_refs or not retrieved_refs:
        return 0.0
    return 1.0 if retrieved_refs[0] in set(expected_refs) else 0.0


def _evidence_hit(expected_substring: str | None, retrieved_texts: list[str]) -> float:
    if not expected_substring:
        return 0.0
    if not retrieved_texts:
        return 0.0
    return 1.0 if expected_substring in retrieved_texts[0] else 0.0


async def _run_route(
    *,
    route: str,
    engine: FusionMemoryEngine,
    bank_id: str,
    query_items: list[dict[str, Any]],
) -> dict[str, Any]:
    from hindsight_api.models import RequestContext

    rows = []
    latencies: list[float] = []
    for item in query_items:
        start = time.perf_counter()
        fused = await engine.recall(
            bank_id=bank_id,
            query=item["query"],
            fact_type=list(item.get("fact_types") or ["experience", "observation", "opinion"]),
            n_results=10,
            request_context=RequestContext(),
            route=route,
        )
        refs = [hit.ref for hit in fused]
        layers = [str(hit.metadata.get("memory_layer") or "") for hit in fused[:5]]
        source_types = [str(hit.metadata.get("source_type") or "") for hit in fused[:5]]
        artifact_types = [str(hit.metadata.get("artifact_type") or "") for hit in fused[:5]]
        texts = [
            str(hit.metadata.get("verbatim_text") or hit.metadata.get("summary_text") or hit.text)
            for hit in fused[:5]
        ]

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        latencies.append(latency_ms)
        rows.append(
            {
                "query": item["query"],
                "category": item["category"],
                "expected_refs": item["expected_refs"],
                "expected_substring": item.get("expected_substring"),
                "retrieved_refs": refs,
                "retrieved_texts": texts,
                "retrieved_layers": layers,
                "retrieved_source_types": source_types,
                "retrieved_artifact_types": artifact_types,
                "latency_ms": latency_ms,
                "recall": _recall_at_k(item["expected_refs"], refs),
                "top1_hit": _top1_hit(item["expected_refs"], refs),
                "evidence_hit": _evidence_hit(item.get("expected_substring"), texts),
            }
        )

    summary: dict[str, Any] = {
        "route": route,
        "queries": len(rows),
        "mean_recall": round(mean(row["recall"] for row in rows), 4) if rows else 0.0,
        "top1_hit_rate": round(mean(row["top1_hit"] for row in rows), 4) if rows else 0.0,
        "evidence_hit_rate": round(mean(row["evidence_hit"] for row in rows), 4) if rows else 0.0,
        "mean_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
        "by_category": {},
        "items": rows,
    }
    for category in sorted({row["category"] for row in rows}):
        cat_rows = [row for row in rows if row["category"] == category]
        summary["by_category"][category] = {
            "queries": len(cat_rows),
            "mean_recall": round(mean(row["recall"] for row in cat_rows), 4),
            "top1_hit_rate": round(mean(row["top1_hit"] for row in cat_rows), 4),
            "evidence_hit_rate": round(mean(row["evidence_hit"] for row in cat_rows), 4),
        }
    return summary


def _build_retain_contents(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    contents = []
    for item in fixture["items"]:
        source_ref = str(item["source_ref"])
        contents.append(
            {
                "content": str(item["text"]),
                "context": f"source_ref:{source_ref}",
                "tags": list(item.get("tags") or []),
                "metadata": {
                    "source_file": str(item["source_file"]),
                    "source_ref": source_ref,
                    "chunk_id": source_ref.split("#", 1)[1] if "#" in source_ref else "0",
                    "chunk_index": "0",
                    "user_id": fixture["user_id"],
                    "artifact_type": str(item.get("artifact_type") or ""),
                    "source_type": str(item.get("source_type") or ""),
                },
                "document_id": source_ref,
                "fact_type": str(item.get("fact_type") or "experience"),
            }
        )
    return contents


async def run_smoke(
    output_path: Path,
    *,
    db_url: str | None,
    bank_id: str | None,
    skip_retain: bool,
    session_count: int,
    max_queries: int | None,
    routes: list[str] | None,
) -> None:
    fixture = build_long_context_fixture(session_count=session_count)
    run_bank_id = bank_id or f"{fixture['bank_id']}_{int(time.time())}"
    engine = await FusionMemoryEngine.create(db_url=db_url)

    from hindsight_api.models import RequestContext

    query_items = list(fixture["queries"])
    if max_queries is not None:
        query_items = query_items[:max_queries]

    selected_routes = routes or ["summary", "verbatim", "fusion"]

    if not skip_retain:
        await engine.retain_batch_async(
            bank_id=run_bank_id,
            contents=_build_retain_contents(fixture),
            request_context=RequestContext(),
            document_tags=["long-context-smoke"],
        )

    out = {
        "name": "memory_fusion_long_context_smoke",
        "corpus_id": fixture["corpus_id"],
        "bank_id": run_bank_id,
        "skip_retain": skip_retain,
        "total_chars": fixture["total_chars"],
        "items": len(fixture["items"]),
        "queries": len(query_items),
        "engine": {
            "summary_llm_provider": engine.summary_llm_provider,
            "verbatim_llm_provider": engine.verbatim_llm_provider,
            "summary_extraction_mode": engine.summary_extraction_mode,
            "verbatim_extraction_mode": engine.verbatim_extraction_mode,
            "summary_is_llm_backed": engine.summary_llm_provider != "none",
            "verbatim_is_llm_backed": engine.verbatim_llm_provider != "none",
        },
        "routes": {},
    }
    for route in selected_routes:
        out["routes"][route] = await _run_route(
            route=route,
            engine=engine,
            bank_id=run_bank_id,
            query_items=query_items,
        )
    output_path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--db-url")
    parser.add_argument("--bank-id", help="Reuse an existing bank instead of generating a new one")
    parser.add_argument(
        "--skip-retain",
        action="store_true",
        help="Skip ingest/embedding and run recall only against --bank-id",
    )
    parser.add_argument(
        "--session-count",
        type=int,
        default=64,
        help="Number of synthetic sessions for the generated corpus (default: 64)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        help="Only evaluate the first N queries (useful for fast smoke verification)",
    )
    parser.add_argument(
        "--routes",
        nargs="+",
        choices=["summary", "verbatim", "fusion"],
        help="Restrict evaluation to selected routes",
    )
    args = parser.parse_args()
    if args.skip_retain and not args.bank_id:
        raise SystemExit("--skip-retain requires --bank-id")
    asyncio.run(
        run_smoke(
            Path(args.out),
            db_url=args.db_url,
            bank_id=args.bank_id,
            skip_retain=args.skip_retain,
            session_count=args.session_count,
            max_queries=args.max_queries,
            routes=args.routes,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
