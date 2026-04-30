from __future__ import annotations

import json

from meta_harness.skill_lifecycle_contract import run_skill_lifecycle_contract_scenarios


def test_skill_lifecycle_contract_writes_artifacts(tmp_path):
    result = run_skill_lifecycle_contract_scenarios(
        run_id="run-skill-lifecycle",
        data_dir=tmp_path,
    )

    assert result["passed"] is True
    assert result["scenario_count"] == 3
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "skill-lifecycle-audit-trace-shape" in scenario_ids
    assert "skill-lifecycle-usage-sidecar-shape" in scenario_ids
    assert "skill-lifecycle-reload-control-policy" in scenario_ids

    artifact = (
        tmp_path
        / "runs"
        / "run-skill-lifecycle"
        / "skill_lifecycle_contract.json"
    )
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 3
