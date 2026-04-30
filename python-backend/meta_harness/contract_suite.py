"""Provider-free cross-feature Meta-Harness contract suite."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meta_harness.domain_contract import run_domain_contract_scenarios
from meta_harness.knowledge_contract import run_knowledge_contract_scenarios
from meta_harness.matrix_widget_policy import run_matrix_widget_policy_scenarios
from meta_harness.mcp_catalog_policy import run_mcp_catalog_policy_scenarios
from meta_harness.prompt_cache_contract import run_prompt_cache_contract_scenarios
from meta_harness.report_grounding import run_report_grounding_scenarios
from meta_harness.routing_contract import run_routing_contract_scenarios
from meta_harness.skill_lifecycle_contract import run_skill_lifecycle_contract_scenarios

DEFAULT_RUN_ID = "run-contract-suite"

SuiteRunner = Callable[..., dict[str, Any]]


def run_contract_suite(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run stable provider-free contract lanes and write one aggregate artifact."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    lanes: tuple[tuple[str, str, SuiteRunner], ...] = (
        ("015/016/020/023/024", "domain_contract", run_domain_contract_scenarios),
        ("015", "skill_lifecycle_contract", run_skill_lifecycle_contract_scenarios),
        ("012/017/019/022/025", "knowledge_contract", run_knowledge_contract_scenarios),
        ("020", "routing_contract", run_routing_contract_scenarios),
        ("032", "prompt_cache_contract", run_prompt_cache_contract_scenarios),
        ("024", "mcp_catalog_policy", run_mcp_catalog_policy_scenarios),
        ("027", "report_grounding", run_report_grounding_scenarios),
        ("030", "matrix_widget_policy", run_matrix_widget_policy_scenarios),
    )
    results = []
    for feature_id, kind, runner in lanes:
        lane_run_id = f"{run_id}-{kind}"
        result = runner(run_id=lane_run_id, data_dir=data_root)
        results.append(
            {
                "feature_id": feature_id,
                "kind": kind,
                "run_id": lane_run_id,
                "passed": bool(result.get("passed")),
                "scenario_count": int(result.get("scenario_count") or 0),
                "passed_count": int(result.get("passed_count") or 0),
                "artifact_path": result.get("artifact_path"),
            }
        )

    summary = {
        "run_id": run_id,
        "kind": "contract_suite",
        "feature_id": "016",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": all(item["passed"] for item in results),
        "lane_count": len(results),
        "scenario_count": sum(item["scenario_count"] for item in results),
        "passed_count": sum(item["passed_count"] for item in results),
        "lanes": results,
    }
    _write_json(run_dir / "contract_suite.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "contract_suite",
            "feature_id": "016",
            "frontend_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    return {**summary, "artifact_path": str(run_dir / "contract_suite.json")}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
