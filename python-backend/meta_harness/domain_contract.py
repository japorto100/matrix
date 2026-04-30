"""Provider-free Meta-Harness domain contracts for python-backend.

The goal is to keep outer/inner-loop optimization concrete: every backend
domain that can be optimized must declare its fixed evaluator, protected
holdout, write scope, source artifacts and safety invariants before a candidate
can be promoted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

DEFAULT_RUN_ID = "run-domain-contract"

DomainKind = Literal[
    "agent_runtime",
    "matrix_transport",
    "subagent_delegation",
    "skills_lifecycle",
    "tool_gateway",
    "memory_context",
    "ingestion",
    "retrieval_rag",
    "kg_semantic",
]

CandidateKind = Literal[
    "config_overlay",
    "policy_overlay",
    "benchmark_candidate",
    "bounded_code_patch",
    "skill_lifecycle_candidate",
]

PYTHON_BACKEND_PREFIXES = (
    "python-backend/agent/",
    "python-backend/memory_fusion/",
    "python-backend/memory_engine/",
    "python-backend/retrieval/",
    "python-backend/kg_pipeline/",
    "python-backend/ingestion/",
    "python-backend/semantic_layer/",
)
META_HARNESS_PREFIX = "python-backend/meta_harness/"

REQUIRED_SPEC_FIELDS = (
    "domain_id",
    "domain_kind",
    "feature_owner",
    "code_scopes",
    "allowed_write_scopes",
    "frozen_evaluator",
    "search_split",
    "holdout_split",
    "budget",
    "metrics",
    "source_artifacts",
    "forbidden_edits",
    "candidate_kinds",
)

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_id",
    "domain_id",
    "candidate_kind",
    "write_scopes",
    "source_artifacts",
    "metric_targets",
    "budget",
)

FORBIDDEN_RUNTIME_EDITS = (
    "goldens_patch",
    "holdout_patch",
    "evaluator_patch",
    "test_only_success",
    "security_relaxation",
    "tool_policy_relaxation",
    "secret_persistence",
)


@dataclass(frozen=True)
class DomainSpec:
    """Frozen optimization contract for one backend domain."""

    domain_id: str
    domain_kind: DomainKind
    feature_owner: str
    code_scopes: tuple[str, ...]
    allowed_write_scopes: tuple[str, ...]
    frozen_evaluator: str
    search_split: str
    holdout_split: str
    budget: dict[str, Any]
    metrics: tuple[str, ...]
    source_artifacts: tuple[str, ...]
    forbidden_edits: tuple[str, ...] = FORBIDDEN_RUNTIME_EDITS
    candidate_kinds: tuple[CandidateKind, ...] = (
        "config_overlay",
        "policy_overlay",
        "benchmark_candidate",
        "bounded_code_patch",
    )
    hermes_lessons: tuple[str, ...] = ()
    sota_sources: tuple[str, ...] = ()
    live_verify_required: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "domain_kind": self.domain_kind,
            "feature_owner": self.feature_owner,
            "code_scopes": list(self.code_scopes),
            "allowed_write_scopes": list(self.allowed_write_scopes),
            "frozen_evaluator": self.frozen_evaluator,
            "search_split": self.search_split,
            "holdout_split": self.holdout_split,
            "budget": self.budget,
            "metrics": list(self.metrics),
            "source_artifacts": list(self.source_artifacts),
            "forbidden_edits": list(self.forbidden_edits),
            "candidate_kinds": list(self.candidate_kinds),
            "hermes_lessons": list(self.hermes_lessons),
            "sota_sources": list(self.sota_sources),
            "live_verify_required": self.live_verify_required,
        }


@dataclass(frozen=True)
class DomainCandidate:
    """Candidate envelope checked before an outer-loop promotion."""

    candidate_id: str
    domain_id: str
    candidate_kind: CandidateKind
    write_scopes: tuple[str, ...]
    source_artifacts: tuple[str, ...]
    metric_targets: dict[str, float]
    budget: dict[str, Any]
    changed_files: tuple[str, ...] = ()
    declared_forbidden_edits: tuple[str, ...] = field(default_factory=tuple)
    docs_only: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "domain_id": self.domain_id,
            "candidate_kind": self.candidate_kind,
            "write_scopes": list(self.write_scopes),
            "source_artifacts": list(self.source_artifacts),
            "metric_targets": self.metric_targets,
            "budget": self.budget,
            "changed_files": list(self.changed_files),
            "declared_forbidden_edits": list(self.declared_forbidden_edits),
            "docs_only": self.docs_only,
        }


def python_backend_domain_specs() -> tuple[DomainSpec, ...]:
    """Return the current frozen domain map for backend optimization."""

    return (
        DomainSpec(
            domain_id="agent-runtime-routing",
            domain_kind="agent_runtime",
            feature_owner="016/020",
            code_scopes=("python-backend/agent/",),
            allowed_write_scopes=(
                "python-backend/agent/routing/",
                "python-backend/agent/runners/",
                "python-backend/agent/graph/",
            ),
            frozen_evaluator="meta_harness routing-contract + scenario_runner parity",
            search_split="search/agent-routing-canaries",
            holdout_split="holdout/agent-routing-protected",
            budget={"provider_calls": 0, "max_tool_calls": 4, "max_spawn_depth": 0},
            metrics=("route_gate_pass_rate", "tool_success_rate", "latency_ms_avg"),
            source_artifacts=(
                "specs_sdd/features/016-meta-harness-agent-optimization/research.md",
                "specs_sdd/features/020-agent-harness-subagents-routing/research.md",
                "_ref/meta-harness/ONBOARDING.md",
                "_ref/hermes-agent/RELEASE_v0.11.0.md",
            ),
            hermes_lessons=(
                "transport/provider separation",
                "compression anti-thrashing",
                "provider reasoning leak scrub",
            ),
            sota_sources=(
                "https://arxiv.org/abs/2603.28052",
                "https://www.anthropic.com/engineering/building-effective-agents",
            ),
        ),
        DomainSpec(
            domain_id="matrix-transport-session-hygiene",
            domain_kind="matrix_transport",
            feature_owner="006/007/009/020/029/030",
            code_scopes=("python-backend/agent/",),
            allowed_write_scopes=(
                "python-backend/agent/routing/",
                "python-backend/agent/streaming.py",
                "python-backend/agent/control/",
            ),
            frozen_evaluator="matrix bridge/appservice trace gates + routing-contract",
            search_split="search/matrix-transport-session-canaries",
            holdout_split="holdout/matrix-transport-protected",
            budget={"provider_calls": 0, "max_reconnect_events": 2},
            metrics=(
                "echo_loop_block_rate",
                "mention_routing_accuracy",
                "approval_trace_pass_rate",
            ),
            source_artifacts=(
                "_ref/hermes-agent/gateway/platforms/matrix.py",
                "_ref/hermes-agent/tests/gateway/test_matrix.py",
                "_ref/hermes-agent/tests/e2e/matrix_xsign_bootstrap/README.md",
                "specs_sdd/features/006-appservice-nats-e2ee-bridges/research.md",
                "specs_sdd/features/030-matrix-widget-app-host/research.md",
            ),
            candidate_kinds=("policy_overlay", "bounded_code_patch"),
            hermes_lessons=(
                "Matrix transport fixes are signal classes, not CLI-agent product code",
                "pairing and echo-loop guards must be explicit",
                "mention and free-response room rules need trace metadata",
                "approval reactions must bind to session identity",
                "E2EE bootstrap belongs to bridge/appservice gates before widget promotion",
            ),
            live_verify_required=True,
        ),
        DomainSpec(
            domain_id="subagent-delegation-roles",
            domain_kind="subagent_delegation",
            feature_owner="009/020/029",
            code_scopes=("python-backend/agent/",),
            allowed_write_scopes=(
                "python-backend/agent/routing/",
                "python-backend/agent/a2a/",
                "python-backend/agent/graph/",
            ),
            frozen_evaluator="meta_harness routing-contract + agent ops trace gates",
            search_split="search/subagent-role-canaries",
            holdout_split="holdout/subagent-role-protected",
            budget={
                "provider_calls": 0,
                "max_concurrent_children": 3,
                "default_max_spawn_depth": 0,
            },
            metrics=("delegation_decision_accuracy", "trace_redaction_pass_rate"),
            source_artifacts=(
                "_ref/hermes-agent/tools/delegate_tool.py",
                "_ref/hermes-agent/website/docs/user-guide/features/delegation.md",
                "_ref/hermes-agent/skills/software-development/subagent-driven-development/SKILL.md",
                "specs_sdd/features/020-agent-harness-subagents-routing/research.md",
            ),
            hermes_lessons=(
                "fresh child context only receives explicit goal/context",
                "leaf delegates cannot clarify, write shared memory or send messages",
                "orchestrator role is opt-in and depth-bounded",
                "interrupts propagate to children",
            ),
            sota_sources=(
                "https://google.github.io/adk-docs/agents/multi-agents/",
                "https://openai.github.io/openai-agents-python/handoffs/",
                "https://reference.langchain.com/python/langgraph-swarm",
            ),
        ),
        DomainSpec(
            domain_id="skills-lifecycle-curator",
            domain_kind="skills_lifecycle",
            feature_owner="015/016/023",
            code_scopes=("python-backend/agent/skills/",),
            allowed_write_scopes=(
                "python-backend/agent/skills/",
                "python-backend/agent/security/",
            ),
            frozen_evaluator="skill finder/loader/security tests + domain-contract",
            search_split="search/skill-trigger-quality",
            holdout_split="holdout/skill-compliance-protected",
            budget={"provider_calls": 0, "max_refinement_iterations": 3},
            metrics=(
                "skill_trigger_precision",
                "skill_usage_coverage",
                "unsafe_skill_block_rate",
            ),
            source_artifacts=(
                "specs_sdd/features/015-scheduler-skills-planning-automation/research.md",
                "_ref/hermes-agent/agent/curator.py",
                "_ref/hermes-agent/tools/skill_usage.py",
                "https://agentskills-workshop.github.io/",
            ),
            candidate_kinds=(
                "config_overlay",
                "policy_overlay",
                "skill_lifecycle_candidate",
                "bounded_code_patch",
            ),
            hermes_lessons=(
                "agent-created skills need usage sidecars",
                "pinned skills block curator and skill_manage writes",
                "curator writes per-run reports",
                "bundled/hub skills are never mutated by curator",
            ),
            sota_sources=(
                "https://agentskills-workshop.github.io/",
                "https://aiagentmemory.org/articles/ai-agent-procedural-memory/",
            ),
        ),
        DomainSpec(
            domain_id="tool-gateway-policy",
            domain_kind="tool_gateway",
            feature_owner="013/016/024/029",
            code_scopes=("python-backend/agent/tools/", "python-backend/agent/mcp/"),
            allowed_write_scopes=(
                "python-backend/agent/tools/",
                "python-backend/agent/mcp/",
                "python-backend/agent/control/tools.py",
            ),
            frozen_evaluator="mcp-catalog-policy + normal tool trace gates",
            search_split="search/tool-policy-canaries",
            holdout_split="holdout/tool-policy-protected",
            budget={"provider_calls": 0, "max_tool_disclosure_level": 2},
            metrics=("policy_block_rate", "tool_output_compaction_pass_rate"),
            source_artifacts=(
                "_ref/hermes-agent/tools/approval.py",
                "_ref/hermes-agent/tools/schema_sanitizer.py",
                "_ref/hermes-agent/tools/tool_output_limits.py",
                "_ref/hermes-agent/plugins/observability/langfuse/README.md",
                "specs_sdd/features/024-mcp-gateway-tool-catalog-policy/research.md",
            ),
            hermes_lessons=(
                "pre_tool_call hooks may veto but must be audited",
                "observability plugins fail open",
                "schema sanitizer protects local backends",
                "tool outputs need explicit caps before model re-entry",
            ),
            sota_sources=("https://arxiv.org/abs/2603.23802",),
        ),
        DomainSpec(
            domain_id="memory-context-fusion",
            domain_kind="memory_context",
            feature_owner="012/016/023",
            code_scopes=("python-backend/memory_fusion/", "python-backend/memory_engine/"),
            allowed_write_scopes=(
                "python-backend/memory_fusion/",
                "python-backend/memory_engine/",
            ),
            frozen_evaluator="memory-smoke + knowledge-contract",
            search_split="search/memory-context-canaries",
            holdout_split="holdout/memory-context-protected",
            budget={"provider_calls": 0, "max_context_items": 12},
            metrics=("memory_recall_precision", "evidence_preservation_rate"),
            source_artifacts=(
                "specs_sdd/features/012-memory-context-world-personal-kb/research.md",
                "_ref/hermes-agent/agent/memory_manager.py",
                "_ref/hermes-agent/agent/context_compressor.py",
            ),
            hermes_lessons=(
                "session switch must flush queued retains",
                "stale memory prefetch must be dropped",
                "compression summary is reference-only, not instruction",
            ),
        ),
        DomainSpec(
            domain_id="source-ingestion-parser",
            domain_kind="ingestion",
            feature_owner="021/023",
            code_scopes=("python-backend/ingestion/",),
            allowed_write_scopes=("python-backend/ingestion/",),
            frozen_evaluator="pdf-extraction-benchmark + pdf-extraction-sweep",
            search_split="search/pdf-extraction-fixtures",
            holdout_split="holdout/source-grounding-protected",
            budget={"provider_calls": 0, "max_parser_profiles": 5},
            metrics=("token_recall", "phrase_coverage", "latency_ms"),
            source_artifacts=(
                "specs_sdd/features/021-ingestion-paperwatcher-researchwatcher/research.md",
                "_ref/autoresearch/README.md",
            ),
            hermes_lessons=("plugin manifests should make optional heavy deps explicit",),
        ),
        DomainSpec(
            domain_id="hybrid-rag-retrieval",
            domain_kind="retrieval_rag",
            feature_owner="019/022/023",
            code_scopes=("python-backend/retrieval/",),
            allowed_write_scopes=("python-backend/retrieval/",),
            frozen_evaluator="rag-benchmark + inner-loop rag",
            search_split="search/rag-canaries",
            holdout_split="holdout/rag-protected",
            budget={"provider_calls": 0, "top_k": 5, "token_budget": 1600},
            metrics=("pass_rate", "recall@5", "ndcg@5", "latency_ms_avg"),
            source_artifacts=(
                "specs_sdd/features/019-hybrid-rag-retrieval/research.md",
                "specs_sdd/features/022-rag-kg-benchmark-lab/research.md",
                "https://arxiv.org/abs/2604.09666",
            ),
            sota_sources=("https://arxiv.org/abs/2604.09666",),
        ),
        DomainSpec(
            domain_id="kg-semantic-provenance",
            domain_kind="kg_semantic",
            feature_owner="017/025",
            code_scopes=("python-backend/kg_pipeline/", "python-backend/semantic_layer/"),
            allowed_write_scopes=(
                "python-backend/kg_pipeline/",
                "python-backend/semantic_layer/",
                "python-backend/memory_engine/global_kg.py",
            ),
            frozen_evaluator="knowledge-contract + semantic catalog tests",
            search_split="search/kg-semantic-canaries",
            holdout_split="holdout/kg-semantic-protected",
            budget={"provider_calls": 0, "max_claims_per_artifact": 25},
            metrics=("claim_evidence_coverage", "semantic_fail_closed_rate"),
            source_artifacts=(
                "specs_sdd/features/017-knowledge-graph-bitemporal-claims/research.md",
                "specs_sdd/features/025-semantic-layer-metrics-claims/research.md",
                "main_docs/root/Z_Semantik_layer and so on.md",
            ),
            hermes_lessons=("provider-specific reasoning traces must not leak into KG evidence",),
        ),
    )


def run_domain_contract_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run deterministic backend-domain contract scenarios."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    specs = {spec.domain_id: spec for spec in python_backend_domain_specs()}
    scenarios = [
        _domain_specs_validate(specs),
        _python_backend_scope_coverage(specs),
        _runtime_docs_only_candidate_rejected(specs),
        _meta_harness_self_edit_rejected(specs),
        _holdout_and_evaluator_are_frozen(specs),
        _subagent_role_contract_is_bounded(specs),
        _skills_curator_contract_is_operational(specs),
        _tool_plugin_observability_contract_is_fail_open(specs),
        _hermes_update_signals_are_mapped(specs),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "domain_contract",
        "feature_id": "015/016/020/023/024",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "domains": [spec.as_dict() for spec in specs.values()],
        "scenarios": scenarios,
    }
    _write_json(run_dir / "domain_contract.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "domain_contract",
            "feature_id": "015/016/020/023/024",
            "frontend_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    _write_candidate_artifacts(run_dir, summary)
    return {**summary, "artifact_path": str(run_dir / "domain_contract.json")}


def validate_domain_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate one domain-spec payload."""

    failures = [
        f"missing-domain-field:{key}"
        for key in REQUIRED_SPEC_FIELDS
        if spec.get(key) in (None, "", (), [])
    ]
    if spec.get("domain_kind") not in DomainKind.__args__:
        failures.append(f"invalid-domain-kind:{spec.get('domain_kind')}")

    code_scopes = _as_str_list(spec.get("code_scopes"))
    write_scopes = _as_str_list(spec.get("allowed_write_scopes"))
    if not code_scopes or not all(_is_python_backend_runtime_scope(p) for p in code_scopes):
        failures.append("domain-code-scope-not-python-backend-runtime")
    if not write_scopes or not all(_is_python_backend_runtime_scope(p) for p in write_scopes):
        failures.append("domain-write-scope-not-python-backend-runtime")
    if any(p.startswith(META_HARNESS_PREFIX) for p in write_scopes):
        failures.append("domain-write-scope-mutates-meta-harness")

    if spec.get("search_split") == spec.get("holdout_split"):
        failures.append("search-holdout-not-separated")
    evaluator = str(spec.get("frozen_evaluator") or "")
    if not evaluator or "mutable" in evaluator.lower():
        failures.append("frozen-evaluator-not-declared")

    budget = spec.get("budget")
    if not isinstance(budget, dict):
        failures.append("invalid-domain-budget")
    elif budget.get("provider_calls", 0) is None:
        failures.append("provider-call-budget-missing")

    if not _as_str_list(spec.get("metrics")):
        failures.append("domain-metrics-missing")
    if not _as_str_list(spec.get("source_artifacts")):
        failures.append("domain-source-artifacts-missing")
    if not set(_as_str_list(spec.get("forbidden_edits"))).issuperset(
        {"goldens_patch", "holdout_patch", "evaluator_patch"}
    ):
        failures.append("domain-forbidden-edits-incomplete")
    return {"passed": not failures, "failures": failures}


def validate_domain_candidate(
    candidate: dict[str, Any],
    domain_specs: dict[str, DomainSpec] | None = None,
) -> dict[str, Any]:
    """Validate that a candidate is promotable inside its domain contract."""

    specs = domain_specs or {spec.domain_id: spec for spec in python_backend_domain_specs()}
    failures = [
        f"missing-domain-candidate-field:{key}"
        for key in REQUIRED_CANDIDATE_FIELDS
        if candidate.get(key) in (None, "", (), [])
    ]
    domain_id = str(candidate.get("domain_id") or "")
    spec = specs.get(domain_id)
    if spec is None:
        failures.append(f"unknown-domain:{domain_id}")
        allowed_write_scopes: tuple[str, ...] = ()
        candidate_kinds: tuple[str, ...] = ()
    else:
        allowed_write_scopes = spec.allowed_write_scopes
        candidate_kinds = spec.candidate_kinds

    candidate_kind = candidate.get("candidate_kind")
    if candidate_kind not in CandidateKind.__args__:
        failures.append(f"invalid-domain-candidate-kind:{candidate_kind}")
    elif candidate_kind not in candidate_kinds:
        failures.append(f"candidate-kind-not-allowed-for-domain:{candidate_kind}")

    write_scopes = _as_str_list(candidate.get("write_scopes"))
    if write_scopes and not all(
        _scope_is_allowed(scope, allowed_write_scopes) for scope in write_scopes
    ):
        failures.append("candidate-write-scope-outside-domain")
    if any(scope.startswith(META_HARNESS_PREFIX) for scope in write_scopes):
        failures.append("candidate-mutates-meta-harness")

    changed_files = _as_str_list(candidate.get("changed_files"))
    if changed_files and not all(
        _scope_is_allowed(path, allowed_write_scopes) for path in changed_files
    ):
        failures.append("candidate-changed-file-outside-domain")

    if candidate.get("docs_only") is True and spec is not None:
        runtime_domains = {"agent_runtime", "subagent_delegation", "skills_lifecycle", "tool_gateway"}
        if spec.domain_kind in runtime_domains:
            failures.append("runtime-domain-docs-only-candidate")

    forbidden = set(_as_str_list(candidate.get("declared_forbidden_edits")))
    if forbidden:
        failures.append(
            "candidate-declares-forbidden-edits:" + ",".join(sorted(forbidden))
        )

    budget = candidate.get("budget")
    if not isinstance(budget, dict):
        failures.append("invalid-domain-candidate-budget")
    elif spec is not None and int(budget.get("provider_calls", 0) or 0) > int(
        spec.budget.get("provider_calls", 0) or 0
    ):
        failures.append("candidate-provider-budget-exceeds-domain")

    if not isinstance(candidate.get("metric_targets"), dict) or not candidate.get(
        "metric_targets"
    ):
        failures.append("candidate-metric-targets-missing")
    return {"passed": not failures, "failures": failures}


def _domain_specs_validate(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    validations = {
        domain_id: validate_domain_spec(spec.as_dict())
        for domain_id, spec in specs.items()
    }
    failures = [
        f"{domain_id}:{failure}"
        for domain_id, validation in validations.items()
        for failure in validation["failures"]
    ]
    return _scenario_result(
        "domain-specs-validate",
        not failures,
        failures,
        {"validations": validations},
    )


def _python_backend_scope_coverage(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    required_prefixes = set(PYTHON_BACKEND_PREFIXES)
    covered: set[str] = set()
    for spec in specs.values():
        for prefix in required_prefixes:
            if any(scope.startswith(prefix) for scope in spec.code_scopes):
                covered.add(prefix)
    missing = sorted(required_prefixes - covered)
    failures = [f"missing-python-backend-domain:{prefix}" for prefix in missing]
    return _scenario_result(
        "domain-python-backend-scope-coverage",
        not failures,
        failures,
        {"covered_prefixes": sorted(covered), "required_prefixes": sorted(required_prefixes)},
    )


def _runtime_docs_only_candidate_rejected(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    validation = validate_domain_candidate(
        DomainCandidate(
            candidate_id="docs-only-agent-runtime",
            domain_id="agent-runtime-routing",
            candidate_kind="bounded_code_patch",
            write_scopes=("python-backend/agent/routing/",),
            changed_files=("specs_sdd/features/020-agent-harness-subagents-routing/research.md",),
            source_artifacts=("specs_sdd/features/020-agent-harness-subagents-routing/research.md",),
            metric_targets={"route_gate_pass_rate": 1.0},
            budget={"provider_calls": 0},
            docs_only=True,
        ).as_dict(),
        specs,
    )
    failures = []
    if validation["passed"] is True:
        failures.append("docs-only-runtime-candidate-not-rejected")
    if "runtime-domain-docs-only-candidate" not in validation["failures"]:
        failures.append("missing-docs-only-runtime-failure")
    return _scenario_result(
        "domain-runtime-docs-only-candidate-rejected",
        not failures,
        failures,
        {"validation": validation},
    )


def _meta_harness_self_edit_rejected(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    validation = validate_domain_candidate(
        DomainCandidate(
            candidate_id="self-edit-meta-harness",
            domain_id="hybrid-rag-retrieval",
            candidate_kind="bounded_code_patch",
            write_scopes=("python-backend/meta_harness/",),
            changed_files=("python-backend/meta_harness/evaluator.py",),
            source_artifacts=("_ref/meta-harness/ONBOARDING.md",),
            metric_targets={"pass_rate": 1.0},
            budget={"provider_calls": 0},
        ).as_dict(),
        specs,
    )
    failures = []
    if validation["passed"] is True:
        failures.append("meta-harness-self-edit-not-rejected")
    if "candidate-mutates-meta-harness" not in validation["failures"]:
        failures.append("missing-meta-harness-mutation-failure")
    return _scenario_result(
        "domain-meta-harness-self-edit-rejected",
        not failures,
        failures,
        {"validation": validation},
    )


def _holdout_and_evaluator_are_frozen(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    failures: list[str] = []
    for spec in specs.values():
        payload = spec.as_dict()
        if payload["search_split"] == payload["holdout_split"]:
            failures.append(f"{spec.domain_id}:split-collision")
        if not payload["frozen_evaluator"]:
            failures.append(f"{spec.domain_id}:missing-frozen-evaluator")
        if "evaluator_patch" not in payload["forbidden_edits"]:
            failures.append(f"{spec.domain_id}:evaluator-patch-not-forbidden")
    return _scenario_result(
        "domain-holdout-evaluator-frozen",
        not failures,
        failures,
        {"domain_count": len(specs)},
    )


def _subagent_role_contract_is_bounded(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    spec = specs["subagent-delegation-roles"]
    failures: list[str] = []
    budget = spec.budget
    lessons = set(spec.hermes_lessons)
    if int(budget.get("default_max_spawn_depth", 99)) != 0:
        failures.append("subagent-default-spawn-depth-not-zero")
    if int(budget.get("max_concurrent_children", 0)) > 3:
        failures.append("subagent-concurrency-above-safe-default")
    required_lessons = {
        "fresh child context only receives explicit goal/context",
        "leaf delegates cannot clarify, write shared memory or send messages",
        "orchestrator role is opt-in and depth-bounded",
    }
    for lesson in sorted(required_lessons - lessons):
        failures.append(f"missing-hermes-subagent-lesson:{lesson}")
    return _scenario_result(
        "domain-subagent-role-contract-bounded",
        not failures,
        failures,
        {"domain": spec.as_dict()},
    )


def _skills_curator_contract_is_operational(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    spec = specs["skills-lifecycle-curator"]
    lessons = set(spec.hermes_lessons)
    required_lessons = {
        "agent-created skills need usage sidecars",
        "pinned skills block curator and skill_manage writes",
        "curator writes per-run reports",
        "bundled/hub skills are never mutated by curator",
    }
    failures = [
        f"missing-hermes-skill-lesson:{lesson}"
        for lesson in sorted(required_lessons - lessons)
    ]
    if "skill_lifecycle_candidate" not in spec.candidate_kinds:
        failures.append("skill-lifecycle-candidate-kind-missing")
    if "unsafe_skill_block_rate" not in spec.metrics:
        failures.append("skill-security-metric-missing")
    return _scenario_result(
        "domain-skills-curator-contract-operational",
        not failures,
        failures,
        {"domain": spec.as_dict()},
    )


def _tool_plugin_observability_contract_is_fail_open(
    specs: dict[str, DomainSpec],
) -> dict[str, Any]:
    spec = specs["tool-gateway-policy"]
    lessons = set(spec.hermes_lessons)
    required_lessons = {
        "pre_tool_call hooks may veto but must be audited",
        "observability plugins fail open",
        "schema sanitizer protects local backends",
        "tool outputs need explicit caps before model re-entry",
    }
    failures = [
        f"missing-hermes-tool-lesson:{lesson}"
        for lesson in sorted(required_lessons - lessons)
    ]
    if "policy_block_rate" not in spec.metrics:
        failures.append("tool-policy-block-rate-metric-missing")
    return _scenario_result(
        "domain-tool-plugin-observability-fail-open",
        not failures,
        failures,
        {"domain": spec.as_dict()},
    )


def _hermes_update_signals_are_mapped(specs: dict[str, DomainSpec]) -> dict[str, Any]:
    mapped = {
        "curator": any("curator" in lesson for spec in specs.values() for lesson in spec.hermes_lessons),
        "delegation": any("delegate" in lesson or "orchestrator" in lesson for spec in specs.values() for lesson in spec.hermes_lessons),
        "provider_hardening": any("provider" in lesson for spec in specs.values() for lesson in spec.hermes_lessons),
        "matrix_transport_hygiene": any("Matrix transport" in lesson or "echo-loop" in lesson for spec in specs.values() for lesson in spec.hermes_lessons),
        "observability": any("observability" in lesson for spec in specs.values() for lesson in spec.hermes_lessons),
        "plugin_manifest": any("plugin" in lesson for spec in specs.values() for lesson in spec.hermes_lessons),
    }
    failures = [
        f"unmapped-hermes-update-signal:{signal}"
        for signal, ok in mapped.items()
        if not ok
    ]
    return _scenario_result(
        "domain-hermes-update-signals-mapped",
        not failures,
        failures,
        {"mapped": mapped},
    )


def _write_candidate_artifacts(run_dir: Path, summary: dict[str, Any]) -> None:
    candidate_dir = run_dir / "candidates" / "python-backend-domain-contract-static"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    aggregate = {
        "run_id": summary["run_id"],
        "candidate_id": "python-backend-domain-contract-static",
        "benchmark_type": "domain_contract",
        "feature_owner": summary["feature_id"],
        "scenarios_evaluated": summary["scenario_count"],
        "completion_rate": 1.0,
        "trace_gate_pass_rate": summary["passed_count"] / max(summary["scenario_count"], 1),
        "tool_success_rate": 1.0,
        "retrieval_pass_rate": 1.0,
        "avg_turns": 1.0,
        "avg_duration_ms": 0.0,
        "total_cost_usd": 0.0,
        "total_tokens": 0,
        "token_efficiency": 1000.0,
        "cost_efficiency": 1.0,
        "fitness_score": round(summary["passed_count"] / max(summary["scenario_count"], 1), 4),
    }
    verdicts = {
        "passed": summary["passed"],
        "scenario_count": summary["scenario_count"],
        "passed_count": summary["passed_count"],
        "failures": [
            failure
            for scenario in summary["scenarios"]
            for failure in scenario.get("failures", [])
        ],
        "observed_actions": ["domain_contract"],
        "observed_tools": [],
    }
    _write_json(candidate_dir / "aggregate.json", aggregate)
    _write_json(candidate_dir / "scores.json", aggregate)
    _write_json(candidate_dir / "verdicts.json", verdicts)
    _write_json(candidate_dir / "domain_contract.json", summary)


def _scenario_result(
    scenario_id: str,
    passed: bool,
    failures: list[str],
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": scenario_id,
        "passed": passed,
        "failures": failures,
        "details": details,
    }


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, tuple | list | set):
        return [str(item) for item in value if str(item)]
    return []


def _is_python_backend_runtime_scope(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PYTHON_BACKEND_PREFIXES)


def _scope_is_allowed(path: str, allowed_scopes: tuple[str, ...]) -> bool:
    return any(path.startswith(scope) for scope in allowed_scopes)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
