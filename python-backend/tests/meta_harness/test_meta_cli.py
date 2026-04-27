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
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["run_id"] == "run-pdf"
    assert captured["pdf_path"] == pdf
    assert captured["truth_path"] == truth
