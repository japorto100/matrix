from __future__ import annotations

import json

from meta_harness.routing_contract import run_routing_contract_scenarios


def test_routing_contract_scenarios_write_artifacts(tmp_path):
    result = run_routing_contract_scenarios(run_id="run-routing", data_dir=tmp_path)

    assert result["passed"] is True
    assert result["scenario_count"] == 9
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "routing-no-tool-no-subagent" in scenario_ids
    assert "routing-retrieval-beats-delegation" in scenario_ids
    assert "routing-domain-delegate-deferred" in scenario_ids
    assert "routing-tool-budget-exhaustion-fails" in scenario_ids
    assert "routing-provider-retry-loop-fails" in scenario_ids
    assert "routing-repeated-failed-tool-calls-fails" in scenario_ids
    assert "routing-forbidden-provider-secret-metadata-fails" in scenario_ids
    assert "routing-runtime-event-redaction-shape" in scenario_ids
    assert "routing-subagent-isolation-runtime" in scenario_ids

    artifact = tmp_path / "runs" / "run-routing" / "routing_contract.json"
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 9
