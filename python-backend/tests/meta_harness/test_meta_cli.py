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
async def test_cli_evaluate_protects_memory_holdout_by_default(monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["evaluate", "--split", "memory_holdout"]
    )

    result = await meta_cli._main_async(args)

    assert result["split"] == "memory_holdout"
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
async def test_cli_experience_packet_writes_outer_loop_packet(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "completion_rate": 1.0,
                "trace_gate_pass_rate": 1.0,
                "fitness_score": 0.8,
                "tool_success_rate": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/agent/runners/simple.py"}]}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text(
        json.dumps([{"action": "llm_response", "success": True}]),
        encoding="utf-8",
    )
    args = meta_cli.build_parser().parse_args(
        [
            "experience-packet",
            "--run-id",
            "run-exp",
            "--data-dir",
            str(tmp_path),
            "--limit",
            "5",
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["run_id"] == "run-exp"
    assert result["candidate_count"] == 1
    assert result["paper_readiness"]["paper_ready_candidates"] == 1
    assert (tmp_path / "runs" / "run-exp" / "experience_packet.json").exists()
    assert (candidate_dir / "candidate_manifest.json").exists()


@pytest.mark.asyncio
async def test_cli_pending_eval_and_promotion_check(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "aggregate.json").write_text(
        json.dumps({"completion_rate": 1.0, "trace_gate_pass_rate": 1.0}),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/agent/runners/simple.py"}]}),
        encoding="utf-8",
    )
    (candidate_dir / "safety.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text(
        json.dumps([{"action": "llm_response"}]),
        encoding="utf-8",
    )
    pending_args = meta_cli.build_parser().parse_args(
        [
            "pending-eval",
            "--run-id",
            "run-1",
            "--candidate-id",
            "candidate-a",
            "--candidate-type",
            "code_patch",
            "--domain-id",
            "agent-runtime-routing",
            "--write-scope",
            "python-backend/agent/runners/",
            "--evaluation",
            "search then holdout",
            "--data-dir",
            str(tmp_path),
        ]
    )
    check_args = meta_cli.build_parser().parse_args(
        [
            "promotion-check",
            "--run-id",
            "run-1",
            "--candidate-id",
            "candidate-a",
            "--data-dir",
            str(tmp_path),
        ]
    )

    pending = await meta_cli._main_async(pending_args)
    check = await meta_cli._main_async(check_args)

    assert pending["holdout_visible_to_proposer"] is False
    assert check["passed"] is False
    assert "missing-holdout-verdict" in check["failures"]


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


@pytest.mark.asyncio
async def test_cli_provider_smoke_blocks_mock_without_opt_in(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "mock/provider")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:8095")
    args = meta_cli.build_parser().parse_args(
        ["provider-smoke", "--run-id", "run-provider", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["blocked"] is True
    assert result["passed"] is False
    assert (
        "deterministic-fake-provider-not-allowed" in result["provider_gate"]["failures"]
    )
    assert (tmp_path / "runs" / "run-provider" / "provider_smoke.json").exists()


@pytest.mark.asyncio
async def test_cli_provider_smoke_records_metadata_without_chat_call(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "openrouter/test-model")
    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "1024")
    monkeypatch.setenv("EMBEDDER_PROVIDER", "openrouter-compatible")
    monkeypatch.setenv("EMBEDDER_MODEL", "embedding-test")
    monkeypatch.setenv("EMBEDDER_DIMENSION", "1536")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-redacted")
    args = meta_cli.build_parser().parse_args(
        ["provider-smoke", "--run-id", "run-provider", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["blocked"] is False
    assert result["chat_checked"] is False
    assert result["provider_snapshot"]["agent_model"] == "openrouter/test-model"
    assert result["provider_snapshot"]["chat_api_key_present"] is True
    assert result["provider_snapshot"]["embedding_dimension"] == "1536"
    assert "sk-redacted" not in json.dumps(result)


@pytest.mark.asyncio
async def test_cli_provider_smoke_chat_call_uses_configured_client(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "openrouter/test-model")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-redacted")

    class _Message:
        content = "ok"

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]
        model = "openrouter/test-model"

    class _Completions:
        async def create(self, **kwargs):
            assert kwargs["model"] == "openrouter/test-model"
            assert kwargs["max_tokens"] == 16
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr(
        "meta_harness.provider_smoke.get_litellm_client",
        lambda: _Client(),
    )
    args = meta_cli.build_parser().parse_args(
        [
            "provider-smoke",
            "--run-id",
            "run-provider-chat",
            "--data-dir",
            str(tmp_path),
            "--chat-call",
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["chat_checked"] is True
    assert result["chat"]["response_chars"] == 2


@pytest.mark.asyncio
async def test_cli_mcp_catalog_policy_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["mcp-catalog-policy", "--run-id", "run-mcp", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 3
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "mcp-benign-fixture-visible" in scenario_ids
    assert "mcp-poisoned-descriptor-blocked" in scenario_ids
    assert "mcp-descriptor-drift-reapproval" in scenario_ids
    artifact = tmp_path / "runs" / "run-mcp" / "mcp_catalog_policy.json"
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 3


@pytest.mark.asyncio
async def test_cli_matrix_widget_policy_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["matrix-widget-policy", "--run-id", "run-widget", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 3
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "matrix-widget-approved-state-event" in scenario_ids
    assert "matrix-widget-unsafe-url-blocked" in scenario_ids
    assert "matrix-widget-mcp-resource-policy" in scenario_ids
    artifact = tmp_path / "runs" / "run-widget" / "matrix_widget_policy.json"
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 3


@pytest.mark.asyncio
async def test_cli_report_grounding_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["report-grounding", "--run-id", "run-report", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 3
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "report-grounded-build" in scenario_ids
    assert "report-missing-citation-blocked" in scenario_ids
    assert "report-unsupported-marker-visible" in scenario_ids
    artifact = tmp_path / "runs" / "run-report" / "report_grounding.json"
    aggregate = (
        tmp_path
        / "runs"
        / "run-report"
        / "candidates"
        / "report-grounding-static"
        / "aggregate.json"
    )
    assert artifact.exists()
    assert aggregate.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 3


@pytest.mark.asyncio
async def test_cli_routing_contract_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["routing-contract", "--run-id", "run-routing", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 15
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "routing-no-tool-no-subagent" in scenario_ids
    assert "routing-domain-delegate-deferred" in scenario_ids
    artifact = tmp_path / "runs" / "run-routing" / "routing_contract.json"
    assert artifact.exists()


@pytest.mark.asyncio
async def test_cli_prompt_cache_contract_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        [
            "prompt-cache-contract",
            "--run-id",
            "run-prompt-cache",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 8
    artifact = tmp_path / "runs" / "run-prompt-cache" / "prompt_cache_contract.json"
    assert artifact.exists()


@pytest.mark.asyncio
async def test_cli_skill_lifecycle_contract_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        [
            "skill-lifecycle-contract",
            "--run-id",
            "run-skill-lifecycle",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 3
    artifact = (
        tmp_path
        / "runs"
        / "run-skill-lifecycle"
        / "skill_lifecycle_contract.json"
    )
    assert artifact.exists()


@pytest.mark.asyncio
async def test_cli_contract_suite_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["contract-suite", "--run-id", "run-suite", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["lane_count"] == 8
    assert result["scenario_count"] == 56
    artifact = tmp_path / "runs" / "run-suite" / "contract_suite.json"
    assert artifact.exists()


@pytest.mark.asyncio
async def test_cli_domain_contract_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["domain-contract", "--run-id", "run-domain", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 9
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "domain-hermes-update-signals-mapped" in scenario_ids
    assert "domain-subagent-role-contract-bounded" in scenario_ids
    assert "domain-skills-curator-contract-operational" in scenario_ids
    assert "domain-runtime-docs-only-candidate-rejected" in scenario_ids
    assert "domain-meta-harness-self-edit-rejected" in scenario_ids
    artifact = tmp_path / "runs" / "run-domain" / "domain_contract.json"
    aggregate = (
        tmp_path
        / "runs"
        / "run-domain"
        / "candidates"
        / "python-backend-domain-contract-static"
        / "aggregate.json"
    )
    assert artifact.exists()
    assert aggregate.exists()
    domains = {domain["domain_id"]: domain for domain in result["domains"]}
    assert "matrix-transport-session-hygiene" in domains
    assert domains["matrix-transport-session-hygiene"]["domain_kind"] == "matrix_transport"
    assert domains["matrix-transport-session-hygiene"]["live_verify_required"] is True
    assert (
        "Matrix transport fixes are signal classes, not CLI-agent product code"
        in domains["matrix-transport-session-hygiene"]["hermes_lessons"]
    )


@pytest.mark.asyncio
async def test_cli_knowledge_contract_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    args = meta_cli.build_parser().parse_args(
        ["knowledge-contract", "--run-id", "run-knowledge", "--data-dir", str(tmp_path)]
    )

    result = await meta_cli._main_async(args)

    assert result["passed"] is True
    assert result["scenario_count"] == 12
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "knowledge-memory-ground-truth-preserved" in scenario_ids
    assert "knowledge-rag-kg-semantic-context-grounded" in scenario_ids
    assert "knowledge-delegation-parent-memory-handoff" in scenario_ids
    assert "knowledge-compaction-tool-output-provenance" in scenario_ids
    assert "knowledge-lexical-candidate-without-provenance-blocked" in scenario_ids
    assert "knowledge-semantic-lookup-before-metric-answer" in scenario_ids
    artifact = tmp_path / "runs" / "run-knowledge" / "knowledge_contract.json"
    aggregate = (
        tmp_path
        / "runs"
        / "run-knowledge"
        / "candidates"
        / "knowledge-contract-static"
        / "aggregate.json"
    )
    assert artifact.exists()
    assert aggregate.exists()


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
    assert (
        "protected-input:inner-bad:parameters.holdout_score" in validation["failures"]
    )


def test_inner_loop_protects_tool_policy_security_relaxations():
    from meta_harness.inner_loop import protected_input_gate

    run = {
        "run_id": "run-policy-protected",
        "feature_owner": "023-auto-optimization-inner-loops",
        "scenario_set": "matrix-tool-policy-canaries",
        "train_split": "search/deterministic-fixture",
        "holdout_split": "holdout/protected",
        "frozen_evaluator": {"goldens_mutable": False},
        "candidates": [
            {
                "candidate_id": "inner-unsafe-tool-policy",
                "feature_owner": "024-mcp-gateway-tool-catalog-policy",
                "candidate_type": "benchmark_candidate",
                "search_space_version": "tool-policy/v1",
                "parameters": {"disable_tool_policy": True},
                "frozen_inputs": {"tool_policy_relaxations": ["allow_tokens"]},
                "budget": {},
            }
        ],
    }

    gate = protected_input_gate(run)

    assert gate["passed"] is False
    assert (
        "protected-input:inner-unsafe-tool-policy:parameters.disable_tool_policy"
        in gate["failures"]
    )
    assert (
        "protected-input:inner-unsafe-tool-policy:frozen_inputs.tool_policy_relaxations"
        in gate["failures"]
    )


def test_domain_contract_rejects_candidate_outside_scope():
    from meta_harness.domain_contract import (
        DomainCandidate,
        python_backend_domain_specs,
        validate_domain_candidate,
    )

    specs = {spec.domain_id: spec for spec in python_backend_domain_specs()}
    validation = validate_domain_candidate(
        DomainCandidate(
            candidate_id="bad-skill-candidate",
            domain_id="skills-lifecycle-curator",
            candidate_kind="skill_lifecycle_candidate",
            write_scopes=("python-backend/meta_harness/",),
            changed_files=("python-backend/meta_harness/domain_contract.py",),
            source_artifacts=("_ref/hermes-agent/agent/curator.py",),
            metric_targets={"skill_trigger_precision": 0.9},
            budget={"provider_calls": 0},
        ).as_dict(),
        specs,
    )

    assert validation["passed"] is False
    assert "candidate-mutates-meta-harness" in validation["failures"]
    assert "candidate-write-scope-outside-domain" in validation["failures"]


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
            "--k",
            "3",
            "--token-budget",
            "512",
            "--max-hits",
            "4",
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
    assert payload["budget"]["top_k"] == 3
    assert payload["budget"]["token_budget"] == 512
    assert payload["budget"]["max_hits"] == 4
    assert payload["parameters"]["top_k"] == 3
    assert payload["parameters"]["context_bubble"]["token_budget"] == 512
    assert payload["parameters"]["context_bubble"]["max_hits"] == 4
    assert payload["parameters"]["fusion"] in {"rrf", "single"}
    assert payload["parameters"]["security_invariants"][
        "tool_policy_can_only_tighten"
    ] is True
    assert payload["parameters"]["candidate_search_spaces"]["tool_policy"][
        "token_passthrough"
    ] == ["deny"]
    spaces = payload["parameters"]["candidate_search_spaces"]
    assert spaces["tool_policy"]["discovery_policy"] == [
        "regex_bm25_rrf_visible_descriptors"
    ]
    assert spaces["memory_context"]["evidence_trace_required"] == [
        "source_status",
        "raw_evidence_ref",
        "operation_log_id",
        "diff_ref",
    ]
    assert spaces["skills"]["trigger_threshold"] == ["current_bm25_dense_rrf"]
    assert spaces["skills"]["mutation_policy"] == ["recommend_only"]
    assert spaces["runner"]["variants"] == ["dispatcher", "langgraph", "simple"]
    assert spaces["runner"]["confirm_unavailable"] == ["fail_closed"]
    assert spaces["kg"]["projection_backend"] == ["off", "postgres", "nornicdb"]
    assert spaces["kg"]["semantic_term_ids_required"] is True
    assert "source_grounding" in payload["parameters"]["candidate_search_spaces"]
    assert "semantic_layer" in payload["parameters"]["candidate_search_spaces"]
    assert "visual_memory" in payload["parameters"]["candidate_search_spaces"]
    assert "report_grounding" in payload["parameters"]["candidate_search_spaces"]
    assert payload["frozen_inputs"]["source_run_id"] == "run-inner-retrieval"
    assert payload["frozen_inputs"]["split_summary"]
    assert "semantic_term_grounded" in payload["frozen_inputs"]["question_classes"]
    assert "visual-layout" in payload["frozen_inputs"]["canary_tags"]
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


@pytest.mark.asyncio
async def test_cli_pdf_extraction_sweep_uses_requested_extractors(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    captured = {}

    async def fake_run_pdf_extraction_sweep(**kwargs):
        captured.update(kwargs)
        return {
            "run_id": kwargs["run_id"],
            "artifacts": {"candidates": []},
            "skipped_extractors": [],
        }

    monkeypatch.setattr(
        "meta_harness.extraction_benchmark.run_pdf_extraction_sweep",
        fake_run_pdf_extraction_sweep,
    )
    pdf = tmp_path / "sample.pdf"
    truth = tmp_path / "sample.md"
    args = meta_cli.build_parser().parse_args(
        [
            "pdf-extraction-sweep",
            "--run-id",
            "run-pdf-sweep",
            "--pdf-path",
            str(pdf),
            "--truth-path",
            str(truth),
            "--extractors",
            "pymupdf4llm,docling",
            "--include-unavailable",
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["run_id"] == "run-pdf-sweep"
    assert captured["pdf_path"] == pdf
    assert captured["truth_path"] == truth
    assert captured["extractor_names"] == ("pymupdf4llm", "docling")
    assert captured["available_only"] is False


def test_pdf_extraction_benchmark_records_requested_extractor(tmp_path):
    from meta_harness.extraction_benchmark import (
        evaluate_pdf_extraction,
        parser_candidate_profiles,
    )

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
    assert report["parser_candidate_profile"]["status"] == "unknown_candidate"
    assert report["candidate_search_space"]["handoff_contract"][
        "citation_ref_required"
    ] is True
    profiles = {
        profile["extractor"]: profile for profile in parser_candidate_profiles()
    }
    assert profiles["pymupdf4llm"]["status"] == "baseline"
    assert profiles["docling"]["runtime"] == "remote_layout_worker"
    assert profiles["mineru"]["resource_class"] == "heavy"
    assert "Unknown extractor" in report["failures"][0]


def test_pdf_extraction_artifacts_include_parser_and_chunker_search_space(tmp_path):
    from meta_harness.extraction_benchmark import write_pdf_extraction_artifacts

    report = {
        "feature_id": "021",
        "candidate_id": "docling-candidate",
        "passed": False,
        "failures": ["not installed"],
        "token_recall": 0.0,
        "phrase_coverage": 0.0,
        "latency_ms": 0.0,
        "pdf_path": "/tmp/sample.pdf",
        "truth_path": "/tmp/sample.md",
        "required_phrases": {"Protokoll": False},
        "parser_candidate_profile": {
            "extractor": "docling",
            "status": "sota_candidate",
        },
        "candidate_search_space": {
            "chunker": {"chunkers": ["token", "hierarchy-aware"]},
            "handoff_contract": {"source_artifact_required": True},
        },
    }

    artifact = write_pdf_extraction_artifacts(
        report,
        run_id="run-pdf-search-space",
        data_dir=tmp_path,
    )
    scenario = json.loads(
        (tmp_path / "runs" / "run-pdf-search-space" / "candidates" / "docling-candidate" / "scenario_set.json").read_text()
    )

    assert artifact["candidate_id"] == "docling-candidate"
    assert scenario["scenarios"][0]["parser_candidate_profile"]["extractor"] == "docling"
    assert scenario["scenarios"][0]["candidate_search_space"]["chunker"]["chunkers"] == [
        "token",
        "hierarchy-aware",
    ]


@pytest.mark.asyncio
async def test_pdf_extraction_sweep_writes_multiple_candidate_artifacts(tmp_path):
    from meta_harness.extraction_benchmark import run_pdf_extraction_sweep

    pdf = tmp_path / "missing.pdf"
    truth = tmp_path / "missing.md"

    result = await run_pdf_extraction_sweep(
        pdf_path=pdf,
        truth_path=truth,
        run_id="run-pdf-sweep",
        extractor_names=("pymupdf4llm", "docling"),
        available_only=False,
        data_dir=tmp_path,
    )

    run_manifest = json.loads((tmp_path / "runs" / "run-pdf-sweep" / "run.json").read_text())
    candidates = result["artifacts"]["candidates"]

    assert run_manifest["kind"] == "pdf_extraction_sweep"
    assert run_manifest["selected_extractors"] == ["pymupdf4llm", "docling"]
    assert run_manifest["candidate_count"] == 2
    assert [candidate["candidate_id"] for candidate in candidates] == [
        "pymupdf4llm-pdf-extraction",
        "docling-pdf-extraction",
    ]
    assert (
        tmp_path
        / "runs"
        / "run-pdf-sweep"
        / "candidates"
        / "docling-pdf-extraction"
        / "extraction_benchmark.json"
    ).exists()


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
