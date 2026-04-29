"""Provider-free Meta-Harness scenarios for report grounding gates."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reports.contract import (
    Citation,
    ReportDataArtifact,
    ReportManifest,
    build_report_artifacts,
    compute_checksum,
    validate_report_manifest,
)

DEFAULT_RUN_ID = "run-report-grounding"


def run_report_grounding_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run deterministic Feature 027 citation/build scenarios and write artifacts."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    report_root = run_dir / "reports"
    run_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        _grounded_report_build_scenario(report_root),
        _missing_citation_failure_scenario(),
        _unsupported_marker_scenario(),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "report_grounding",
        "feature_id": "027",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
    _write_json(run_dir / "report_grounding.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "report_grounding",
            "feature_id": "027",
            "provider_calls_required": False,
            "frontend_required": False,
            "renderer": "markdown-fallback",
            "created_at": summary["created_at"],
        },
    )
    _write_candidate_artifacts(run_dir, summary)
    return {**summary, "artifact_path": str(run_dir / "report_grounding.json")}


def _grounded_report_build_scenario(report_root: Path) -> dict[str, Any]:
    source = (
        "# Risk Brief\n"
        "Revenue concentration is elevated for this fixture [S1]\n"
        "{{risk-table}}\n"
    )
    manifest = ReportManifest(
        report_id="grounded-risk-brief",
        title="Grounded Risk Brief",
        owner="meta-harness",
        input_sources=("source-a",),
        citations=(_citation(),),
        data_artifacts=(
            ReportDataArtifact(
                artifact_id="risk-table",
                kind="table",
                title="Risk Table",
                source_id="source-a",
                columns=("metric", "value"),
                rows=({"metric": "concentration", "value": "elevated"},),
            ),
        ),
        checksum=compute_checksum(source),
    )
    result = build_report_artifacts(
        source_markdown=source,
        manifest=manifest,
        output_dir=report_root,
    )
    failures: list[str] = []
    if not result.get("passed"):
        failures.extend(result.get("validation", {}).get("failures", []))
    artifacts = result.get("artifacts") or {}
    manifest_path = Path(str(artifacts.get("manifest") or ""))
    if not manifest_path.exists():
        failures.append("missing-built-manifest")
    if artifacts.get("data") and not Path(str(artifacts["data"])).exists():
        failures.append("missing-data-artifact")
    return {
        "id": "report-grounded-build",
        "passed": not failures,
        "failures": failures,
        "validation": result.get("validation", {}),
        "artifacts": artifacts,
    }


def _missing_citation_failure_scenario() -> dict[str, Any]:
    source = "# Risk Brief\nRevenue concentration is elevated."
    manifest = ReportManifest(
        report_id="missing-citation",
        title="Missing Citation",
        owner="meta-harness",
        input_sources=("source-a",),
        citations=(_citation(),),
        checksum=compute_checksum(source),
    )
    validation = validate_report_manifest(manifest, source_markdown=source)
    expected = {
        "citation-not-used:S1",
        "section-unsupported:Risk Brief:line-2",
    }
    failures = [
        f"missing-expected-failure:{item}"
        for item in sorted(expected)
        if item not in set(validation["failures"])
    ]
    if validation["passed"]:
        failures.append("missing citation scenario unexpectedly passed")
    return {
        "id": "report-missing-citation-blocked",
        "passed": not failures,
        "failures": failures,
        "validation": validation,
    }


def _unsupported_marker_scenario() -> dict[str, Any]:
    source = "# Risk Brief\nSpeculative stress path [UNSUPPORTED]\nEvidence [S1]"
    manifest = ReportManifest(
        report_id="unsupported-marker",
        title="Unsupported Marker",
        owner="meta-harness",
        input_sources=("source-a",),
        citations=(_citation(),),
        checksum=compute_checksum(source),
    )
    validation = validate_report_manifest(manifest, source_markdown=source)
    failures = list(validation["failures"])
    return {
        "id": "report-unsupported-marker-visible",
        "passed": not failures,
        "failures": failures,
        "validation": validation,
    }


def _write_candidate_artifacts(run_dir: Path, summary: dict[str, Any]) -> None:
    candidate_dir = run_dir / "candidates" / "report-grounding-static"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    aggregate = {
        "candidate_id": "report-grounding-static",
        "feature_id": "027",
        "completion_rate": 1.0 if summary["passed"] else 0.0,
        "tool_success_rate": summary["passed_count"] / max(1, summary["scenario_count"]),
        "scenarios_evaluated": summary["scenario_count"],
        "trace_gate_pass_rate": 1.0 if summary["passed"] else 0.0,
        "failed_scenarios": [
            {"scenario_id": item["id"], "failures": item["failures"]}
            for item in summary["scenarios"]
            if not item["passed"]
        ],
    }
    _write_json(candidate_dir / "aggregate.json", aggregate)
    _write_json(candidate_dir / "scenario_set.json", {"scenarios": summary["scenarios"]})
    _write_json(candidate_dir / "report_grounding.json", summary)


def _citation() -> Citation:
    return Citation(
        citation_id="S1",
        source_id="source-a",
        title="Source A",
        uri="https://example.invalid/source-a",
        excerpt="evidence",
    )


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
