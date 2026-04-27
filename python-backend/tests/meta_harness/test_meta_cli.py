from __future__ import annotations

import json

import pytest

from meta_harness import meta_cli
from meta_harness.proposer import ENABLE_EXTERNAL_LLM_ENV


@pytest.mark.asyncio
async def test_cli_evaluate_protects_holdout_by_default(monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(["evaluate", "--split", "holdout"])

    result = await meta_cli._main_async(args)

    assert result["split"] == "holdout"
    assert "protected" in result["error"].lower()


@pytest.mark.asyncio
async def test_cli_propose_external_llm_disabled_by_default(monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    monkeypatch.delenv(ENABLE_EXTERNAL_LLM_ENV, raising=False)
    args = meta_cli.build_parser().parse_args(["propose", "--sessions", "2"])

    result = await meta_cli._main_async(args)

    assert result["external_llm_disabled"] is True
    assert result["sessions_requested"] == 2


@pytest.mark.asyncio
async def test_cli_decide_writes_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        [
            "decide",
            "--run-id",
            "run-1",
            "--candidate-id",
            "candidate-a",
            "--decision",
            "defer",
            "--rationale",
            "Needs more scenarios.",
            "--metrics-json",
            '{"trace_gate_pass_rate": 0.5}',
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["decision"] == "defer"
    assert (tmp_path / "candidate_decisions.jsonl").exists()


@pytest.mark.asyncio
async def test_cli_history_reads_decisions(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    (tmp_path / "candidate_decisions.jsonl").write_text(
        '{"run_id":"run-1","candidate_id":"c","decision":"keep"}\n',
        encoding="utf-8",
    )
    args = meta_cli.build_parser().parse_args(
        ["history", "--data-dir", str(tmp_path), "--limit", "10"]
    )

    result = await meta_cli._main_async(args)

    assert result["total"] == 1
    assert result["decisions"][0]["decision"] == "keep"


@pytest.mark.asyncio
async def test_cli_rag_benchmark_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "openrouter/test-model")
    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "2048")
    monkeypatch.setenv("EMBEDDER_PROVIDER", "openrouter")
    monkeypatch.setenv("EMBEDDER_MODEL", "openrouter/text-embedding-test")
    monkeypatch.setenv("EMBEDDER_DIMENSION", "1536")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-redacted")
    args = meta_cli.build_parser().parse_args(
        ["rag-benchmark", "--run-id", "run-rag", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["run_id"] == "run-rag"
    assert (tmp_path / "runs" / "run-rag" / "run.json").exists()
    assert result["artifacts"]["candidates"]
    candidate_dir = (
        tmp_path / "runs" / "run-rag" / "candidates" / "matrix-fused-vector-kg"
    )
    report = json.loads((candidate_dir / "retrieval_benchmark.json").read_text())
    verdicts = json.loads((candidate_dir / "verdicts.json").read_text())
    assert report["metadata_compatibility"]["passed"] is True
    assert verdicts["metadata_compatibility"]["passed"] is True
    assert report["candidate"]["metadata"]["source_corpus"]
    assert report["provider_config"]["agent_model"] == "openrouter/test-model"
    assert report["provider_config"]["agent_max_output_tokens"] == "2048"
    assert report["provider_config"]["embedding_provider"] == "openrouter"
    assert report["provider_config"]["embedding_dimension"] == "1536"
    assert report["provider_config"]["openrouter_api_key_present"] is True
    assert "sk-redacted" not in json.dumps(report)
    decision = json.loads((candidate_dir / "decision.json").read_text())
    assert decision["decision"] == "defer"
    assert "holdout" in decision["rationale"].lower()
    decisions_log = (tmp_path / "candidate_decisions.jsonl").read_text()
    assert "matrix-fused-vector-kg" in decisions_log


def test_rag_benchmark_verdict_fails_missing_candidate_metadata():
    from meta_harness.retrieval_benchmark import _candidate_verdicts

    verdict = _candidate_verdicts(
        {
            "candidate_id": "bad-candidate",
            "metadata": {"source_corpus": "corpus"},
            "results": [],
        }
    )

    assert verdict["passed"] is False
    assert "missing-candidate-metadata:parser_version" in verdict["failures"]


def test_inner_loop_candidate_validation_rejects_missing_fields():
    from meta_harness.inner_loop import validate_inner_loop_candidate

    validation = validate_inner_loop_candidate(
        {
            "candidate_id": "inner-a",
            "candidate_type": "benchmark_candidate",
            "parameters": {},
            "frozen_inputs": {},
            "budget": {},
        }
    )

    assert validation["passed"] is False
    assert "missing-candidate-field:feature_owner" in validation["failures"]
    assert "missing-candidate-field:search_space_version" in validation["failures"]


def test_inner_loop_provider_gate_blocks_without_quota(monkeypatch):
    from meta_harness.inner_loop import (
        ALLOW_PROVIDER_CALLS_ENV,
        MAX_PROVIDER_CALLS_ENV,
        provider_call_gate,
    )

    monkeypatch.delenv(ALLOW_PROVIDER_CALLS_ENV, raising=False)
    monkeypatch.setenv(MAX_PROVIDER_CALLS_ENV, "10")

    gate = provider_call_gate(1)

    assert gate["allowed"] is False
    assert ALLOW_PROVIDER_CALLS_ENV in gate["reason"]


def test_inner_loop_provider_gate_enforces_request_cap(monkeypatch):
    from meta_harness.inner_loop import (
        ALLOW_PROVIDER_CALLS_ENV,
        MAX_PROVIDER_CALLS_ENV,
        provider_call_gate,
    )

    monkeypatch.setenv(ALLOW_PROVIDER_CALLS_ENV, "true")
    monkeypatch.setenv(MAX_PROVIDER_CALLS_ENV, "2")

    gate = provider_call_gate(3)

    assert gate["allowed"] is False
    assert MAX_PROVIDER_CALLS_ENV in gate["reason"]


def test_inner_loop_protects_goldens_and_holdout_inputs():
    from meta_harness.inner_loop import protected_input_gate, validate_inner_loop_run

    run = {
        "run_id": "run-protected",
        "feature_owner": "023-auto-optimization-inner-loops",
        "scenario_set": "matrix-retrieval-canaries@2026-04-27",
        "train_split": "search/deterministic-fixture",
        "holdout_split": "holdout/protected",
        "frozen_evaluator": {
            "type": "retrieval_benchmark",
            "goldens_mutable": False,
        },
        "candidates": [
            {
                "candidate_id": "inner-bad",
                "feature_owner": "019-hybrid-rag-retrieval",
                "candidate_type": "benchmark_candidate",
                "search_space_version": "rag-retrieval-modes/v1",
                "parameters": {"holdout_score": 1.0},
                "frozen_inputs": {},
                "budget": {},
            }
        ],
    }

    gate = protected_input_gate(run)
    validation = validate_inner_loop_run(run)

    assert gate["passed"] is False
    assert "protected-input:inner-bad:parameters.holdout_score" in gate["failures"]
    assert validation["passed"] is False
    assert "protected-input:inner-bad:parameters.holdout_score" in validation["failures"]


@pytest.mark.asyncio
async def test_cli_inner_loop_writes_candidate_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        [
            "inner-loop",
            "--kind",
            "rag",
            "--run-id",
            "run-inner",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["run_id"] == "run-inner"
    assert result["validation"]["passed"] is True
    run_dir = tmp_path / "runs" / "run-inner"
    assert (run_dir / "inner_loop.json").exists()
    candidate = result["candidates"][0]
    candidate_dir = run_dir / "candidates" / candidate["candidate_id"]
    payload = json.loads((candidate_dir / "inner_loop_candidate.json").read_text())
    aggregate = json.loads((candidate_dir / "aggregate.json").read_text())
    assert payload["candidate_type"] == "benchmark_candidate"
    assert payload["budget"]["provider_calls"] == 0
    assert payload["frozen_inputs"]["source_run_id"] == "run-inner-retrieval"
    assert payload["frozen_inputs"]["split_summary"]
    assert aggregate["completion_rate"] == 1.0
    assert aggregate["tool_success_rate"] == 1.0
    run_manifest = json.loads((run_dir / "run.json").read_text())
    assert run_manifest["protected_inputs"]["passed"] is True
    assert (candidate_dir / "config.json").exists()


@pytest.mark.asyncio
async def test_cli_inner_loop_blocks_live_provider_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        [
            "inner-loop",
            "--kind",
            "rag",
            "--run-id",
            "run-inner-blocked",
            "--provider-calls-budget",
            "1",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["blocked"] is True
    assert result["provider_gate"]["allowed"] is False
    assert not (tmp_path / "runs" / "run-inner-blocked").exists()


@pytest.mark.asyncio
async def test_cli_pdf_extraction_benchmark_uses_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    captured = {}

    async def fake_run_pdf_extraction_benchmark(**kwargs):
        captured.update(kwargs)
        return {"run_id": kwargs["run_id"], "artifacts": {"candidate_id": "pdf"}}

    monkeypatch.setattr(
        "meta_harness.extraction_benchmark.run_pdf_extraction_benchmark",
        fake_run_pdf_extraction_benchmark,
    )
    pdf = tmp_path / "sample.pdf"
    truth = tmp_path / "sample.md"
    args = meta_cli.build_parser().parse_args(
        [
            "pdf-extraction-benchmark",
            "--run-id",
            "run-pdf",
            "--pdf-path",
            str(pdf),
            "--truth-path",
            str(truth),
            "--extractor",
            "markitdown",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["run_id"] == "run-pdf"
    assert captured["pdf_path"] == pdf
    assert captured["truth_path"] == truth
    assert captured["extractor_name"] == "markitdown"


def test_pdf_extraction_benchmark_records_requested_extractor(tmp_path):
    from meta_harness.extraction_benchmark import evaluate_pdf_extraction

    pdf = tmp_path / "sample.pdf"
    truth = tmp_path / "sample.md"
    pdf.write_bytes(b"%PDF")
    truth.write_text("truth", encoding="utf-8")

    report = evaluate_pdf_extraction(
        pdf_path=pdf,
        truth_path=truth,
        candidate_id="missing-extractor-candidate",
        extractor_name="missing-extractor",
    )

    assert report["passed"] is False
    assert report["extractor_requested"] == "missing-extractor"
    assert report["extractor"] == "missing-extractor"
    assert "Unknown extractor" in report["failures"][0]


@pytest.mark.asyncio
async def test_cli_memory_smoke_writes_provider_free_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        [
            "memory-smoke",
            "--run-id",
            "run-memory-smoke",
            "--candidate-id",
            "memory-smoke-candidate",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["provider_calls"] == 0
    candidate_dir = (
        tmp_path / "runs" / "run-memory-smoke" / "candidates" / "memory-smoke-candidate"
    )
    assert (candidate_dir / "verdicts.json").exists()
    aggregate = json.loads((candidate_dir / "aggregate.json").read_text())
    verdicts = json.loads((candidate_dir / "verdicts.json").read_text())
    assert aggregate["memory_utilization_rate"] == 1.0
    assert aggregate["tool_success_rate"] == 1.0
    assert verdicts["passed"] is True
    assert verdicts["observed_memory_providers"] == ["hindsight", "mempalace"]
