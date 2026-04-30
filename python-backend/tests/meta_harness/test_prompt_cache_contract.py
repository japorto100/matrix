from __future__ import annotations

import json

from meta_harness.prompt_cache_contract import run_prompt_cache_contract_scenarios


def test_prompt_cache_contract_writes_artifacts(tmp_path):
    result = run_prompt_cache_contract_scenarios(
        run_id="run-prompt-cache",
        data_dir=tmp_path,
    )

    assert result["passed"] is True
    assert result["scenario_count"] == 5
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "prompt-cache-stable-prompt-tool-order" in scenario_ids
    assert "prompt-cache-content-change-reason" in scenario_ids
    assert "prompt-cache-tool-schema-change-reason" in scenario_ids
    assert "prompt-cache-mcp-reload-impact-replayed" in scenario_ids
    assert "prompt-cache-usage-unknown-counters" in scenario_ids

    artifact = tmp_path / "runs" / "run-prompt-cache" / "prompt_cache_contract.json"
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 5
