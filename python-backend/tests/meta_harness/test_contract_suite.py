from __future__ import annotations

import json

from meta_harness.contract_suite import run_contract_suite


def test_contract_suite_runs_provider_free_lanes(tmp_path):
    result = run_contract_suite(run_id="run-suite", data_dir=tmp_path)

    assert result["passed"] is True
    assert result["lane_count"] == 8
    assert result["scenario_count"] == 49
    kinds = {lane["kind"] for lane in result["lanes"]}
    assert kinds == {
        "domain_contract",
        "skill_lifecycle_contract",
        "knowledge_contract",
        "routing_contract",
        "prompt_cache_contract",
        "mcp_catalog_policy",
        "report_grounding",
        "matrix_widget_policy",
    }
    artifact = tmp_path / "runs" / "run-suite" / "contract_suite.json"
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 49
