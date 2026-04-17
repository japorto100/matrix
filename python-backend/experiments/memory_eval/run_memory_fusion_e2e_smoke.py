"""Run a real Postgres-backed end-to-end smoke for memory_fusion semantics.

This is intentionally small and assertion-heavy:
- no fake engines
- no benchmark corpus indirection
- focused on retain/reject/recall/list/get_document behaviour
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_fusion.fusion_engine import FusionMemoryEngine  # noqa: E402


def _raw_chat_turn() -> dict[str, Any]:
    source_ref = "e2e-raw-chat.jsonl#0"
    return {
        "content": (
            "The user said they prefer calmer breakout execution on Brent. "
            "The exact archive token was smoke-raw-001."
        ),
        "context": f"source_ref:{source_ref}",
        "fact_type": "experience",
        "artifact_type": "chat_turn",
        "source_type": "user_input",
        "tags": ["e2e-smoke", "chat-turn", "brent"],
        "document_id": source_ref,
        "metadata": {
            "source_file": "e2e-raw-chat.jsonl",
            "source_ref": source_ref,
            "chunk_id": "0",
            "chunk_index": "0",
            "user_id": "e2e-smoke",
            "wing": "e2e-smoke",
            "room": "chat",
        },
    }


def _grounded_preference() -> dict[str, Any]:
    source_ref = "e2e-derived-pref.jsonl#0"
    return {
        "content": "Observed preference: the user prefers calm breakout execution on Brent.",
        "context": f"source_ref:{source_ref}",
        "fact_type": "opinion",
        "artifact_type": "preference",
        "source_type": "system_observation",
        "tags": ["e2e-smoke", "preference", "brent"],
        "document_id": source_ref,
        "metadata": {
            "source_file": "e2e-derived-pref.jsonl",
            "source_ref": source_ref,
            "provenance_ref": source_ref,
            "chunk_id": "0",
            "chunk_index": "0",
            "user_id": "e2e-smoke",
            "wing": "e2e-smoke",
            "room": "preferences",
        },
    }


def _ungrounded_preference() -> dict[str, Any]:
    return {
        "content": "Observed preference without any evidence backlink.",
        "fact_type": "opinion",
        "artifact_type": "preference",
        "source_type": "system_observation",
        "tags": ["e2e-smoke", "preference"],
        "metadata": {
            "source_file": "e2e-derived-ungrounded.jsonl",
            "user_id": "e2e-smoke",
        },
    }


def _kb_artifact() -> dict[str, Any]:
    return {
        "content": "Saved PDF about market structure.",
        "artifact_type": "pdf",
        "source_type": "external_document",
        "tags": ["e2e-smoke", "pdf"],
        "metadata": {
            "source_file": "market-structure.pdf",
            "source_ref": "market-structure.pdf#0",
        },
    }


def _world_artifact() -> dict[str, Any]:
    return {
        "content": "External world claim from a market report.",
        "fact_type": "world",
        "artifact_type": "world_claim",
        "source_type": "world_evidence",
        "tags": ["e2e-smoke", "world-claim"],
        "metadata": {
            "source_file": "market-report.jsonl",
            "source_ref": "market-report.jsonl#0",
        },
    }


async def _expect_retain_failure(
    engine: FusionMemoryEngine,
    *,
    bank_id: str,
    item: dict[str, Any],
    request_context: Any,
    expected_fragment: str,
) -> str:
    try:
        await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[item],
            request_context=request_context,
            document_tags=["e2e-smoke"],
        )
    except ValueError as exc:
        message = str(exc)
        if expected_fragment not in message:
            raise AssertionError(f"Expected failure containing {expected_fragment!r}, got {message!r}") from exc
        return message
    raise AssertionError(f"Expected retain failure containing {expected_fragment!r}")


def _first_text(results: list[Any]) -> str:
    if not results:
        raise AssertionError("Expected at least one result")
    return str(results[0].text)


async def run_smoke(
    output_path: Path,
    *,
    db_url: str | None,
    bank_id: str | None,
    cleanup: bool,
) -> None:
    from hindsight_api.models import RequestContext

    run_bank_id = bank_id or f"memory_fusion_e2e_smoke_{int(time.time())}"
    engine = await FusionMemoryEngine.create(db_url=db_url)
    request_context = RequestContext()

    accepted_contents = [_raw_chat_turn(), _grounded_preference()]
    rejected: dict[str, str] = {}

    report: dict[str, Any] = {
        "name": "memory_fusion_postgres_e2e_smoke",
        "bank_id": run_bank_id,
        "db_url_supplied": bool(db_url),
        "writes": {},
        "reads": {},
        "cleanup": {"requested": cleanup, "performed": False},
    }

    try:
        retain_result = await engine.retain_batch_async(
            bank_id=run_bank_id,
            contents=accepted_contents,
            request_context=request_context,
            document_tags=["e2e-smoke"],
        )
        report["writes"]["accepted_result"] = retain_result

        rejected["ungrounded_derived"] = await _expect_retain_failure(
            engine,
            bank_id=run_bank_id,
            item=_ungrounded_preference(),
            request_context=request_context,
            expected_fragment="Derived memory items require evidence backlinks",
        )
        rejected["personal_kb"] = await _expect_retain_failure(
            engine,
            bank_id=run_bank_id,
            item=_kb_artifact(),
            request_context=request_context,
            expected_fragment="bridge_personal_kb",
        )
        rejected["world_model"] = await _expect_retain_failure(
            engine,
            bank_id=run_bank_id,
            item=_world_artifact(),
            request_context=request_context,
            expected_fragment="bridge_world",
        )
        report["writes"]["rejected"] = rejected

        units = await engine.list_memory_units(
            bank_id=run_bank_id,
            request_context=request_context,
            route="summary",
        )
        if units["total"] < 1:
            raise AssertionError("Expected at least one memory unit in summary route")
        if any(str(item.get("metadata", {}).get("derived_without_evidence") or "").lower() == "true" for item in units["items"]):
            raise AssertionError("list_memory_units surfaced an ungrounded derived item")

        docs = await engine.list_documents(
            bank_id=run_bank_id,
            request_context=request_context,
            route="fusion",
        )
        if docs["total"] < 1:
            raise AssertionError("Expected at least one document in fusion route")

        raw_doc_id = str(_raw_chat_turn()["document_id"])
        raw_doc = await engine.get_document(raw_doc_id, run_bank_id, request_context=request_context)
        if raw_doc is None:
            raise AssertionError("Expected raw document to be fetchable")
        if not raw_doc.get("route_documents"):
            raise AssertionError("Expected route_documents in get_document result")
        if "smoke-raw-001" not in str(raw_doc.get("original_text") or ""):
            raise AssertionError("Expected original_text in get_document result to preserve the raw quote")
        route_documents = dict(raw_doc.get("route_documents") or {})
        summary_route_doc = dict(route_documents.get("summary") or {})
        verbatim_route_doc = dict(route_documents.get("verbatim") or {})
        if summary_route_doc.get("memory_layer") != "personal_raw":
            raise AssertionError("Summary route document did not preserve personal_raw metadata")
        if verbatim_route_doc.get("memory_layer") != "personal_raw":
            raise AssertionError("Verbatim route document did not preserve personal_raw metadata")

        preference_doc_id = str(_grounded_preference()["document_id"])
        preference_doc = await engine.get_document(preference_doc_id, run_bank_id, request_context=request_context)
        if preference_doc is None:
            raise AssertionError("Expected grounded preference document to be fetchable")
        preference_summary_doc = dict((preference_doc.get("route_documents") or {}).get("summary") or {})
        if preference_summary_doc.get("memory_layer") != "personal_derived":
            raise AssertionError("Preference summary document did not preserve personal_derived metadata")
        if str(preference_summary_doc.get("document_metadata", {}).get("grounding_status") or "") != "grounded_derived":
            raise AssertionError("Preference summary document did not preserve grounded derived status")

        fusion_quote = await engine.recall(
            bank_id=run_bank_id,
            query="What is the exact quote for the archive token?",
            fact_type=["experience"],
            n_results=5,
            request_context=request_context,
            route="fusion",
        )
        summary_pref = await engine.recall_async(
            bank_id=run_bank_id,
            query="What preference does the user have on Brent?",
            request_context=request_context,
            route="summary",
            fact_type=["opinion", "observation"],
        )
        verbatim_quote = await engine.recall_async(
            bank_id=run_bank_id,
            query="What is the exact quote for the archive token?",
            request_context=request_context,
            route="verbatim",
            fact_type=["experience"],
            include_chunks=True,
        )

        report["reads"] = {
            "fusion_quote_result_count": len(fusion_quote),
            "fusion_quote_top_ref": fusion_quote[0].ref if fusion_quote else None,
            "fusion_quote_top_memory_layer": fusion_quote[0].metadata.get("memory_layer") if fusion_quote else None,
            "summary_recall_result_count": len(summary_pref.results),
            "summary_preference_top_text": summary_pref.results[0].text if summary_pref.results else None,
            "summary_preference_top_memory_layer": summary_pref.results[0].metadata.get("memory_layer") if summary_pref.results else None,
            "summary_preference_grounding_status": summary_pref.results[0].metadata.get("grounding_status") if summary_pref.results else None,
            "verbatim_recall_result_count": len(verbatim_quote.results),
            "verbatim_quote_top_text": verbatim_quote.results[0].text if verbatim_quote.results else None,
            "verbatim_chunk_count": len(verbatim_quote.chunks),
            "list_memory_units_total": units["total"],
            "list_documents_total": docs["total"],
            "document_routes_present": list(raw_doc.get("routes_present") or []),
            "raw_document_original_text_preserved": "smoke-raw-001" in str(raw_doc.get("original_text") or ""),
            "preference_document_routes_present": list(preference_doc.get("routes_present") or []),
            "preference_summary_memory_layer": preference_summary_doc.get("memory_layer"),
            "preference_summary_grounding_status": preference_summary_doc.get("document_metadata", {}).get("grounding_status"),
        }
    finally:
        if cleanup:
            try:
                await engine.delete_bank(run_bank_id, request_context=request_context)
                report["cleanup"]["performed"] = True
            except Exception as exc:  # noqa: BLE001
                report["cleanup"]["error"] = str(exc)

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--db-url")
    parser.add_argument("--bank-id")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the test bank after the smoke completes",
    )
    args = parser.parse_args()
    asyncio.run(
        run_smoke(
            Path(args.out),
            db_url=args.db_url,
            bank_id=args.bank_id,
            cleanup=args.cleanup,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
