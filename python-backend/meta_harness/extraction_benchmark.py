"""Meta-Harness artifact writer for PDF extraction against Markdown truth."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from meta_harness.config import capture_current_config
from meta_harness.proposer import META_HARNESS_DATA_DIR

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF_PATH = (
    ROOT
    / "_ref/Researchwatcher/layout-module/tests/test_assets/"
    "Small-pdf-with-text-formula-table-code-picture.pdf"
)
DEFAULT_TRUTH_PATH = DEFAULT_PDF_PATH.with_suffix(".md")
DEFAULT_REQUIRED_PHRASES = (
    "Protokoll",
    "Freie Fall",
    "Theoretische Grundlagen",
    "h(t)",
    "Messdaten",
    "Python-Simulation",
    "berechne_hoehe",
)


async def run_pdf_extraction_benchmark(
    *,
    pdf_path: Path = DEFAULT_PDF_PATH,
    truth_path: Path = DEFAULT_TRUTH_PATH,
    run_id: str | None = None,
    candidate_id: str = "pymupdf4llm-pdf-extraction",
    data_dir: Path = META_HARNESS_DATA_DIR,
    required_phrases: tuple[str, ...] = DEFAULT_REQUIRED_PHRASES,
) -> dict[str, Any]:
    """Run a real PDF extraction benchmark and write Meta-Harness artifacts."""

    run_id = run_id or f"run-pdf-extraction-{uuid.uuid4().hex[:12]}"
    report = evaluate_pdf_extraction(
        pdf_path=pdf_path,
        truth_path=truth_path,
        candidate_id=candidate_id,
        required_phrases=required_phrases,
    )
    artifact = write_pdf_extraction_artifacts(
        report,
        run_id=run_id,
        data_dir=data_dir,
    )
    return {"run_id": run_id, "report": report, "artifacts": artifact}


def evaluate_pdf_extraction(
    *,
    pdf_path: Path,
    truth_path: Path,
    candidate_id: str,
    required_phrases: tuple[str, ...] = DEFAULT_REQUIRED_PHRASES,
) -> dict[str, Any]:
    """Extract one PDF and compare the markdown output with a ground-truth MD."""

    pdf_path = pdf_path.resolve()
    truth_path = truth_path.resolve()
    started = perf_counter()
    if not pdf_path.exists():
        return _error_report(candidate_id, pdf_path, truth_path, f"missing PDF: {pdf_path}")
    if not truth_path.exists():
        return _error_report(
            candidate_id,
            pdf_path,
            truth_path,
            f"missing ground-truth markdown: {truth_path}",
        )

    try:
        from ingestion.extractors.pymupdf_ext import PyMuPDF4LLMExtractor

        extractor = PyMuPDF4LLMExtractor()
        if not extractor.is_available():
            return _error_report(
                candidate_id,
                pdf_path,
                truth_path,
                "pymupdf4llm extractor is not available",
            )
        extracted = extractor.extract(pdf_path)
    except Exception as exc:  # noqa: BLE001
        return _error_report(candidate_id, pdf_path, truth_path, str(exc))

    truth_md = truth_path.read_text(encoding="utf-8")
    extracted_md = extracted.content_md or ""
    token_recall = _token_recall(extracted_md, truth_md)
    phrase_results = {
        phrase: _contains_phrase(extracted_md, phrase) for phrase in required_phrases
    }
    phrase_coverage = round(
        sum(1 for present in phrase_results.values() if present)
        / max(len(phrase_results), 1),
        4,
    )
    passed = (
        token_recall >= 0.65
        and phrase_coverage >= 0.6
        and extracted.page_count > 0
        and bool(extracted_md.strip())
    )
    failures: list[str] = []
    if token_recall < 0.65:
        failures.append(f"token_recall < 0.65 ({token_recall})")
    if phrase_coverage < 0.6:
        failures.append(f"phrase_coverage < 0.6 ({phrase_coverage})")
    if extracted.page_count <= 0:
        failures.append("page_count <= 0")
    if not extracted_md.strip():
        failures.append("empty extracted markdown")

    latency_ms = round((perf_counter() - started) * 1000, 3)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "feature_id": "021",
        "benchmark_type": "pdf_extraction_ground_truth",
        "candidate_id": candidate_id,
        "pdf_path": str(pdf_path),
        "truth_path": str(truth_path),
        "passed": passed,
        "failures": failures,
        "token_recall": token_recall,
        "phrase_coverage": phrase_coverage,
        "required_phrases": phrase_results,
        "page_count": extracted.page_count,
        "section_count": extracted.section_count,
        "table_count": len(extracted.tables),
        "figure_count": len(extracted.figures),
        "formula_count": len(extracted.formulas),
        "has_code_fence": "```" in extracted_md,
        "extracted_chars": len(extracted_md),
        "truth_chars": len(truth_md),
        "latency_ms": latency_ms,
        "extractor": extracted.extractor,
    }


def write_pdf_extraction_artifacts(
    report: dict[str, Any],
    *,
    run_id: str,
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Write a PDF extraction benchmark as a candidate artifact directory."""

    candidate_id = str(report.get("candidate_id") or "pdf-extraction")
    run_dir = data_dir / "runs" / run_id
    candidate_dir = run_dir / "candidates" / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "created_at": datetime.now(UTC).isoformat(),
        "kind": "pdf_extraction_benchmark",
        "feature_id": report.get("feature_id", "021"),
        "stack": {
            "python_agent": True,
            "postgres_required": False,
            "frontend_required": False,
            "go_gateway_required": False,
        },
    }
    aggregate = _aggregate(run_id, report)
    verdicts = {
        "passed": bool(report.get("passed")),
        "failures": report.get("failures", []),
        "observed_actions": ["pdf_extraction_benchmark"],
        "observed_tools": [],
        "tool_success_rate": 1.0,
    }
    scenario_set = {
        "scenarios": [
            {
                "id": "researchwatcher-small-pdf-ground-truth",
                "pdf_path": report.get("pdf_path"),
                "truth_path": report.get("truth_path"),
                "required_phrases": list((report.get("required_phrases") or {}).keys()),
            }
        ]
    }
    _write_json(run_dir / "run.json", run_manifest)
    _write_json(candidate_dir / "extraction_benchmark.json", report)
    _write_json(candidate_dir / "aggregate.json", aggregate)
    _write_json(candidate_dir / "scores.json", aggregate)
    _write_json(candidate_dir / "verdicts.json", verdicts)
    _write_json(candidate_dir / "scenario_set.json", scenario_set)
    _write_json(candidate_dir / "config.json", _config_snapshot())
    _write_json(candidate_dir / "source_snapshot.json", _source_snapshot())
    return {
        "run_path": str(run_dir),
        "candidate_path": str(candidate_dir),
        "candidate_id": candidate_id,
        "fitness_score": aggregate["fitness_score"],
    }


def _aggregate(run_id: str, report: dict[str, Any]) -> dict[str, Any]:
    pass_rate = 1.0 if report.get("passed") else 0.0
    token_recall = _as_float(report.get("token_recall"))
    phrase_coverage = _as_float(report.get("phrase_coverage"))
    latency_ms = _as_float(report.get("latency_ms"))
    fitness = round((pass_rate * 0.4) + (token_recall * 0.35) + (phrase_coverage * 0.25), 4)
    return {
        "run_id": run_id,
        "candidate_id": report.get("candidate_id", ""),
        "benchmark_type": "pdf_extraction_ground_truth",
        "scenarios_evaluated": 1,
        "completion_rate": 1.0,
        "trace_gate_pass_rate": pass_rate,
        "tool_success_rate": 1.0,
        "memory_utilization_rate": 0.0,
        "fitness_score": fitness,
        "extraction_pass_rate": pass_rate,
        "token_recall": token_recall,
        "phrase_coverage": phrase_coverage,
        "avg_turns": 1.0,
        "turn_efficiency": 1.0,
        "total_tokens": 0,
        "avg_tokens": 0.0,
        "token_efficiency": 1000.0,
        "total_cost_usd": 0.0,
        "cost_efficiency": 1.0,
        "avg_duration_ms": latency_ms,
        "latency_efficiency": round(1000.0 / max(latency_ms, 1.0), 6)
        if latency_ms > 0
        else 1.0,
        "failed_scenarios": [
            {
                "scenario_id": "researchwatcher-small-pdf-ground-truth",
                "failures": report.get("failures", []),
            }
        ]
        if not report.get("passed")
        else [],
    }


def _error_report(
    candidate_id: str,
    pdf_path: Path,
    truth_path: Path,
    error: str,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "feature_id": "021",
        "benchmark_type": "pdf_extraction_ground_truth",
        "candidate_id": candidate_id,
        "pdf_path": str(pdf_path),
        "truth_path": str(truth_path),
        "passed": False,
        "failures": [error],
        "token_recall": 0.0,
        "phrase_coverage": 0.0,
        "required_phrases": {},
        "page_count": 0,
        "section_count": 0,
        "table_count": 0,
        "figure_count": 0,
        "formula_count": 0,
        "has_code_fence": False,
        "extracted_chars": 0,
        "truth_chars": 0,
        "latency_ms": 0.0,
        "extractor": "pymupdf4llm",
    }


def _token_recall(extracted: str, truth: str) -> float:
    extracted_tokens = set(_tokens(extracted))
    truth_tokens = set(_tokens(truth))
    if not truth_tokens:
        return 0.0
    return round(len(extracted_tokens & truth_tokens) / len(truth_tokens), 4)


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9_äöüÄÖÜß]+", text.lower()) if len(token) > 1]


def _contains_phrase(text: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(text)


def _normalize(text: str) -> str:
    return " ".join(_tokens(text))


def _config_snapshot() -> dict[str, Any]:
    try:
        return json.loads(capture_current_config().to_json())
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _source_snapshot() -> dict[str, Any]:
    paths = [
        "python-backend/ingestion/extractors/pymupdf_ext.py",
        "python-backend/meta_harness/extraction_benchmark.py",
        "python-backend/meta_harness/proposer.py",
        "_ref/Researchwatcher/layout-module/tests/test_assets/"
        "Small-pdf-with-text-formula-table-code-picture.pdf",
        "_ref/Researchwatcher/layout-module/tests/test_assets/"
        "Small-pdf-with-text-formula-table-code-picture.md",
    ]
    files = []
    for rel in paths:
        path = ROOT / rel
        if path.exists():
            files.append({"path": rel, "bytes": path.stat().st_size})
    return {"files": files}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
