"""Meta-Harness scenario runner and trace gates.

Feature 016 turns harness evaluation from single prompts into repeatable
simulated-user scenarios with deterministic trace assertions. The implementation
is intentionally Python-only: it can run against the in-process agent loop and
does not require the frontend or Go Gateway.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from meta_harness.scorer import composite_fitness, score_session

META_HARNESS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "meta_harness"
RUNNER_VARIANTS = ("dispatcher", "langgraph", "simple")
logger = logging.getLogger(__name__)


def _provider_label(model: str) -> str:
    parts = [part for part in str(model or "").split("/") if part]
    if not parts:
        return "litellm"
    if parts[0] == "openrouter":
        return "openrouter"
    if parts[0] in {"anthropic", "openai", "google", "deepseek", "groq", "mistral"}:
        return parts[0]
    return "litellm"


def _env_flag_enabled(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _harness_env_api_key(model: str) -> str | None:
    """Resolve a local service credential for in-process Meta-Harness runs.

    The live FastAPI path continues to use normal user credentials. This fallback
    exists only for the Python Meta-Harness CLI so simulated users can keep their
    own memory banks without every harness user needing a DB credential row.
    """
    if not _env_flag_enabled("META_HARNESS_ALLOW_ENV_CREDENTIALS", default=True):
        return None
    provider = _provider_label(model)
    env_by_provider = {
        "openrouter": ("META_HARNESS_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
        "openai": ("META_HARNESS_OPENAI_API_KEY", "OPENAI_API_KEY"),
        "anthropic": ("META_HARNESS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
        "google": ("META_HARNESS_GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "deepseek": ("META_HARNESS_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"),
        "groq": ("META_HARNESS_GROQ_API_KEY", "GROQ_API_KEY"),
        "mistral": ("META_HARNESS_MISTRAL_API_KEY", "MISTRAL_API_KEY"),
        "litellm": ("META_HARNESS_LITELLM_API_KEY", "LITELLM_MASTER_KEY"),
    }
    for env_name in env_by_provider.get(provider, ()):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def _default_agent_model() -> str:
    return (
        os.environ.get("AGENT_DEFAULT_MODEL", "").strip()
        or os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "").strip()
    )


def _turn_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.environ.get("META_HARNESS_TURN_TIMEOUT_S", "90.0")))
    except ValueError:
        return 90.0


def _normalize_runner_variant(value: str | None) -> str:
    variant = (value or "dispatcher").strip().lower()
    if variant not in RUNNER_VARIANTS:
        raise ValueError(
            f"unknown runner_variant: {value!r}; expected one of {RUNNER_VARIANTS}"
        )
    return variant


@dataclass(frozen=True)
class ScenarioTurn:
    """One simulated user turn."""

    user: str

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> ScenarioTurn:
        return cls(user=str(raw.get("user") or raw.get("message") or ""))


@dataclass(frozen=True)
class TraceExpectations:
    """Deterministic assertions over audit events."""

    required_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    required_skills: tuple[str, ...] = ()
    required_memory_routes: tuple[str, ...] = ()
    required_memory_providers: tuple[str, ...] = ()
    forbidden_memory_routes: tuple[str, ...] = ()
    forbidden_memory_providers: tuple[str, ...] = ()
    required_response_terms: tuple[str, ...] = ()
    forbidden_response_terms: tuple[str, ...] = ()
    required_memory_evidence_terms: tuple[str, ...] = ()
    required_memory_metadata_keys: tuple[str, ...] = ()
    required_event_metadata_keys: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    forbidden_event_metadata_keys: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    required_event_metadata_values: dict[str, dict[str, str]] = field(
        default_factory=dict
    )
    forbidden_event_metadata_values: dict[str, dict[str, str]] = field(
        default_factory=dict
    )
    required_runtime_event_names: tuple[str, ...] = ()
    required_runtime_event_metadata_keys: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    forbidden_runtime_event_metadata_keys: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    required_runtime_event_metadata_values: dict[str, dict[str, str]] = field(
        default_factory=dict
    )
    forbidden_runtime_event_metadata_values: dict[str, dict[str, str]] = field(
        default_factory=dict
    )
    required_stream_parts: tuple[str, ...] = ()
    required_stream_rich_renderers: tuple[str, ...] = ()
    required_stream_artifact_files: tuple[str, ...] = ()
    required_route_decisions: tuple[str, ...] = ()
    required_runner_variants: tuple[str, ...] = ()
    required_delegation_decisions: tuple[str, ...] = ()
    allowed_tool_groups: tuple[str, ...] = ()
    max_tool_disclosure_level: int | None = None
    max_spawn_depth: int | None = None
    max_repeated_tool_failures_per_tool: int | None = None
    max_provider_retry_events: int | None = None
    expected_memory: bool = False
    min_tool_success_rate: float | None = None
    allow_tool_failures: bool = False

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> TraceExpectations:
        raw = raw or {}
        required_event_metadata_keys = {
            str(action): tuple(str(key) for key in keys)
            for action, keys in (raw.get("required_event_metadata_keys") or {}).items()
        }
        forbidden_event_metadata_keys = {
            str(action): tuple(str(key) for key in keys)
            for action, keys in (raw.get("forbidden_event_metadata_keys") or {}).items()
        }
        required_event_metadata_values = _metadata_value_expectations(
            raw.get("required_event_metadata_values") or {}
        )
        forbidden_event_metadata_values = _metadata_value_expectations(
            raw.get("forbidden_event_metadata_values") or {}
        )
        required_runtime_event_metadata_keys = {
            str(name): tuple(str(key) for key in keys)
            for name, keys in (
                raw.get("required_runtime_event_metadata_keys") or {}
            ).items()
        }
        forbidden_runtime_event_metadata_keys = {
            str(name): tuple(str(key) for key in keys)
            for name, keys in (
                raw.get("forbidden_runtime_event_metadata_keys") or {}
            ).items()
        }
        required_runtime_event_metadata_values = _metadata_value_expectations(
            raw.get("required_runtime_event_metadata_values") or {}
        )
        forbidden_runtime_event_metadata_values = _metadata_value_expectations(
            raw.get("forbidden_runtime_event_metadata_values") or {}
        )
        return cls(
            required_actions=tuple(str(x) for x in raw.get("required_actions", [])),
            forbidden_actions=tuple(str(x) for x in raw.get("forbidden_actions", [])),
            required_tools=tuple(str(x) for x in raw.get("required_tools", [])),
            forbidden_tools=tuple(str(x) for x in raw.get("forbidden_tools", [])),
            required_skills=tuple(str(x) for x in raw.get("required_skills", [])),
            required_memory_routes=tuple(
                str(x) for x in raw.get("required_memory_routes", [])
            ),
            required_memory_providers=tuple(
                str(x) for x in raw.get("required_memory_providers", [])
            ),
            forbidden_memory_routes=tuple(
                str(x) for x in raw.get("forbidden_memory_routes", [])
            ),
            forbidden_memory_providers=tuple(
                str(x) for x in raw.get("forbidden_memory_providers", [])
            ),
            required_response_terms=tuple(
                str(x) for x in raw.get("required_response_terms", [])
            ),
            forbidden_response_terms=tuple(
                str(x) for x in raw.get("forbidden_response_terms", [])
            ),
            required_memory_evidence_terms=tuple(
                str(x) for x in raw.get("required_memory_evidence_terms", [])
            ),
            required_memory_metadata_keys=tuple(
                str(x) for x in raw.get("required_memory_metadata_keys", [])
            ),
            required_event_metadata_keys=required_event_metadata_keys,
            forbidden_event_metadata_keys=forbidden_event_metadata_keys,
            required_event_metadata_values=required_event_metadata_values,
            forbidden_event_metadata_values=forbidden_event_metadata_values,
            required_runtime_event_names=tuple(
                str(x) for x in raw.get("required_runtime_event_names", [])
            ),
            required_runtime_event_metadata_keys=required_runtime_event_metadata_keys,
            forbidden_runtime_event_metadata_keys=forbidden_runtime_event_metadata_keys,
            required_runtime_event_metadata_values=(
                required_runtime_event_metadata_values
            ),
            forbidden_runtime_event_metadata_values=(
                forbidden_runtime_event_metadata_values
            ),
            required_stream_parts=tuple(
                str(x) for x in raw.get("required_stream_parts", [])
            ),
            required_stream_rich_renderers=tuple(
                str(x) for x in raw.get("required_stream_rich_renderers", [])
            ),
            required_stream_artifact_files=tuple(
                str(x) for x in raw.get("required_stream_artifact_files", [])
            ),
            required_route_decisions=tuple(
                str(x) for x in raw.get("required_route_decisions", [])
            ),
            required_runner_variants=tuple(
                str(x) for x in raw.get("required_runner_variants", [])
            ),
            required_delegation_decisions=tuple(
                str(x) for x in raw.get("required_delegation_decisions", [])
            ),
            allowed_tool_groups=tuple(
                str(x) for x in raw.get("allowed_tool_groups", [])
            ),
            max_tool_disclosure_level=raw.get("max_tool_disclosure_level"),
            max_spawn_depth=raw.get("max_spawn_depth"),
            max_repeated_tool_failures_per_tool=raw.get(
                "max_repeated_tool_failures_per_tool"
            ),
            max_provider_retry_events=raw.get("max_provider_retry_events"),
            expected_memory=bool(raw.get("expected_memory", False)),
            min_tool_success_rate=raw.get("min_tool_success_rate"),
            allow_tool_failures=bool(raw.get("allow_tool_failures", False)),
        )

    @classmethod
    def from_legacy_query(cls, raw: dict[str, Any]) -> TraceExpectations:
        return cls(
            required_tools=tuple(str(x) for x in raw.get("expected_tools", [])),
            forbidden_tools=tuple(str(x) for x in raw.get("forbidden_tools", [])),
            required_skills=tuple(str(x) for x in raw.get("expected_skills", [])),
            expected_memory=bool(raw.get("expected_memory", False)),
            allow_tool_failures=bool(raw.get("allow_tool_failures", False)),
        )


@dataclass(frozen=True)
class Scenario:
    """A multi-turn task instance for the Meta-Harness search set."""

    id: str
    category: str
    turns: tuple[ScenarioTurn, ...]
    expectations: TraceExpectations = field(default_factory=TraceExpectations)
    judge: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    consent_allow_session_tools: tuple[str, ...] = ()
    enable_tools: bool = True
    runner_variant: str = "dispatcher"

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> Scenario:
        if raw.get("turns"):
            turns = tuple(ScenarioTurn.from_mapping(t) for t in raw["turns"])
        else:
            turns = (ScenarioTurn(user=str(raw.get("message") or "")),)
        expectations = (
            TraceExpectations.from_mapping(raw.get("expected_trace"))
            if raw.get("expected_trace")
            else TraceExpectations.from_legacy_query(raw)
        )
        metadata = dict(raw.get("metadata") or {})
        runner_variant = _normalize_runner_variant(
            str(raw.get("runner_variant") or metadata.get("runner_variant") or "")
        )
        return cls(
            id=str(raw.get("id") or f"scenario-{uuid.uuid4().hex[:8]}"),
            category=str(raw.get("category") or "uncategorized"),
            turns=turns,
            expectations=expectations,
            judge=dict(raw.get("judge") or {}),
            metadata=metadata,
            consent_allow_session_tools=tuple(
                str(x)
                for x in (raw.get("consent") or {}).get("allow_session_tools", [])
            ),
            enable_tools=bool(raw.get("enable_tools", True)),
            runner_variant=runner_variant,
        )


@dataclass(frozen=True)
class TraceGateVerdict:
    """Trace assertion result for one scenario run."""

    passed: bool
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    observed_actions: tuple[str, ...]
    observed_tools: tuple[str, ...]
    observed_skills: tuple[str, ...]
    tool_success_rate: float | None = None
    observed_memory_routes: tuple[str, ...] = ()
    observed_memory_providers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StreamGateVerdict:
    """UI-stream assertion result for one scenario run."""

    passed: bool
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    observed_parts: tuple[str, ...]
    observed_tools: tuple[str, ...]
    observed_rich_renderers: tuple[str, ...] = ()
    observed_artifact_files: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioRunResult:
    """Result artifact for one executed scenario."""

    run_id: str
    candidate_id: str
    scenario_id: str
    thread_id: str
    user_id: str
    category: str
    turns: int
    transcript: tuple[dict[str, str], ...]
    sse_chunks: tuple[str, ...]
    trace_events: tuple[dict[str, Any], ...]
    score: dict[str, Any]
    trace_verdict: TraceGateVerdict
    stream_verdict: StreamGateVerdict | None = None
    artifact_dir: str | None = None
    runner_variant: str = "dispatcher"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["trace_verdict"] = self.trace_verdict.as_dict()
        if self.stream_verdict is not None:
            data["stream_verdict"] = self.stream_verdict.as_dict()
        return data


def _event_action(event: dict[str, Any]) -> str:
    return str(event.get("action") or "")


def _event_tool(event: dict[str, Any]) -> str:
    return str(event.get("toolName") or event.get("tool_name") or "")


def _event_metadata(event: dict[str, Any]) -> dict[str, Any]:
    meta = event.get("metadata") or {}
    if isinstance(meta, str):
        try:
            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return meta if isinstance(meta, dict) else {}


def _event_input(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("input") or {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _event_output(event: dict[str, Any]) -> Any:
    value = event.get("output")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _tool_unavailable_reason(tool_name: str, output: Any) -> str:
    """Detect soft-failed tool payloads that were marked successful in transport."""
    if isinstance(output, str):
        normalized = output.casefold()
        if "not available" in normalized or "unavailable" in normalized:
            return f"tool unavailable: {tool_name}"
        return ""
    if not isinstance(output, dict):
        return ""
    message = str(output.get("message") or output.get("error") or "").casefold()
    if "not available" in message or "unavailable" in message:
        return f"tool unavailable: {tool_name}"
    if tool_name in {"memory_add", "save_memory"} and output.get("stored") is False:
        return f"tool unavailable: {tool_name} stored=false"
    return ""


def _normalized_memory_add_key(event: dict[str, Any]) -> tuple[str, str] | None:
    if _event_action(event) != "tool_call" or _event_tool(event) != "memory_add":
        return None
    payload = _event_input(event)
    content = " ".join(str(payload.get("content") or "").split()).casefold()
    if not content:
        return None
    fact_type = str(payload.get("fact_type") or "experience").strip().casefold()
    return content, fact_type


def _duplicate_memory_add_warnings(events: list[dict[str, Any]]) -> list[str]:
    counts: dict[tuple[str, str], int] = {}
    for event in events:
        key = _normalized_memory_add_key(event)
        if key is None:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [
        "duplicate memory_add content observed: "
        f"fact_type={fact_type or 'experience'} count={count}"
        for (_content, fact_type), count in sorted(counts.items())
        if count > 1
    ]


def _registered_tool_names() -> set[str]:
    try:
        from agent.tools.registry import ToolRegistry

        return {tool.name for tool in ToolRegistry.load().all()}
    except Exception:  # noqa: BLE001
        return set()


def _registered_tool_catalog() -> dict[str, Any]:
    try:
        from agent.tools.catalog import builtin_tool_catalog
        from agent.tools.registry import ToolRegistry

        return {entry.name: entry for entry in builtin_tool_catalog(ToolRegistry.load().all())}
    except Exception:  # noqa: BLE001
        return {}


def _observed_skill_ids(events: list[dict[str, Any]]) -> set[str]:
    skills: set[str] = set()
    for event in events:
        meta = _event_metadata(event)
        for key in ("skill_ids", "source_skills"):
            values = meta.get(key) or []
            if isinstance(values, str):
                values = [values]
            for value in values:
                if value:
                    skills.add(str(value))
        for value in meta.get("skill_names") or []:
            if value:
                skills.add(str(value))
    return skills


def _observed_memory_metadata(events: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    routes: set[str] = set()
    providers: set[str] = set()
    for event in events:
        if _event_action(event) not in {"memory_recall", "memory_retain"}:
            continue
        meta = _event_metadata(event)
        for key in ("route", "fusion_route"):
            value = meta.get(key)
            if value:
                routes.add(str(value))
        for value in str(meta.get("providers") or "").split(","):
            if value.strip():
                providers.add(value.strip())
        for key in ("provider", "memory_provider", "engine"):
            value = meta.get(key)
            if value:
                providers.add(str(value))
    return routes, providers


def _observed_route_metadata(
    events: list[dict[str, Any]],
) -> tuple[set[str], set[str], set[str], int | None]:
    decisions: set[str] = set()
    runners: set[str] = set()
    delegations: set[str] = set()
    max_spawn_depth: int | None = None
    for event in events:
        if _event_action(event) != "route_decision":
            continue
        meta = _event_metadata(event)
        if meta.get("decision"):
            decisions.add(str(meta["decision"]))
        if meta.get("runner"):
            runners.add(str(meta["runner"]))
        if meta.get("delegation_decision"):
            delegations.add(str(meta["delegation_decision"]))
        try:
            depth = int(meta.get("spawn_depth"))
        except (TypeError, ValueError):
            continue
        max_spawn_depth = (
            depth if max_spawn_depth is None else max(max_spawn_depth, depth)
        )
    return decisions, runners, delegations, max_spawn_depth


def _normalized_gate_text(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _memory_event_blob(events: list[dict[str, Any]]) -> str:
    memory_events = []
    for event in events:
        action = _event_action(event)
        tool = _event_tool(event)
        if action in {"memory_recall", "memory_retain"} or tool in {
            "memory_add",
            "memory_search",
        }:
            memory_events.append(event)
    return _normalized_gate_text(json.dumps(memory_events, default=str, sort_keys=True))


def _metadata_contains_key(metadata: dict[str, Any], key: str) -> bool:
    if not key:
        return False
    current: Any = metadata
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


_MISSING_METADATA_VALUE = object()


def _metadata_value(metadata: dict[str, Any], key: str) -> Any:
    if not key:
        return _MISSING_METADATA_VALUE
    current: Any = metadata
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING_METADATA_VALUE
        current = current[part]
    return current


def _metadata_value_matches(actual: Any, expected: str) -> bool:
    normalized_expected = _normalized_gate_text(expected)
    if isinstance(actual, bool):
        return str(actual).casefold() == normalized_expected
    if isinstance(actual, dict):
        return normalized_expected in _normalized_gate_text(
            json.dumps(actual, default=str, sort_keys=True)
        )
    if isinstance(actual, (list, tuple, set)):
        return any(_metadata_value_matches(item, expected) for item in actual)
    return _normalized_gate_text(actual) == normalized_expected


def _metadata_value_expectations(raw: dict[str, Any]) -> dict[str, dict[str, str]]:
    expectations: dict[str, dict[str, str]] = {}
    for event_name, values in raw.items():
        if not isinstance(values, dict):
            continue
        expectations[str(event_name)] = {
            str(key): str(value) for key, value in values.items()
        }
    return expectations


def _runtime_events_from_trace_events(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    runtime_events: list[dict[str, Any]] = []
    for event in events:
        for value in (
            event.get("runtime_events"),
            event.get("runtimeEvents"),
            _event_metadata(event).get("runtime_events"),
            _event_metadata(event).get("runtimeEvents"),
        ):
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    continue
            if isinstance(value, dict):
                runtime_events.append(value)
            elif isinstance(value, list):
                runtime_events.extend(item for item in value if isinstance(item, dict))
    return runtime_events


def _runtime_event_name(event: dict[str, Any]) -> str:
    return str(event.get("name") or event.get("event") or event.get("type") or "")


def _runtime_event_metadata(event: dict[str, Any]) -> dict[str, Any]:
    metadata = event.get("metadata")
    if metadata is None:
        metadata = event.get("data")
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return metadata if isinstance(metadata, dict) else {}


def _memory_metadata_keys(events: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for event in events:
        if _event_action(event) not in {"memory_recall", "memory_retain"}:
            continue
        meta = _event_metadata(event)
        for key in meta:
            keys.add(str(key))
    return keys


def evaluate_trace_gates(
    events: list[dict[str, Any]],
    expectations: TraceExpectations,
    *,
    response_text: str = "",
) -> TraceGateVerdict:
    """Evaluate deterministic trace expectations over audit events."""
    actions = [_event_action(event) for event in events if _event_action(event)]
    action_set = set(actions)
    tools = [
        _event_tool(event)
        for event in events
        if _event_tool(event)
        and _event_action(event) in {"tool_call", "tool_result", "consent_request"}
    ]
    executable_tools = [
        _event_tool(event)
        for event in events
        if _event_tool(event) and _event_action(event) in {"tool_call", "tool_result"}
    ]
    tool_set = set(tools)
    executable_tool_set = set(executable_tools)
    skills = _observed_skill_ids(events)
    memory_routes, memory_providers = _observed_memory_metadata(events)
    (
        route_decisions,
        runner_variants,
        delegation_decisions,
        observed_max_spawn_depth,
    ) = _observed_route_metadata(events)
    registered_tools = _registered_tool_names()
    registered_tool_catalog = _registered_tool_catalog()

    failures: list[str] = []
    warnings: list[str] = []
    warnings.extend(_duplicate_memory_add_warnings(events))

    normalized_response = _normalized_gate_text(response_text)
    memory_blob = _memory_event_blob(events)
    memory_metadata_keys = _memory_metadata_keys(events)
    runtime_events = _runtime_events_from_trace_events(events)
    runtime_event_names = {
        name for name in (_runtime_event_name(event) for event in runtime_events) if name
    }

    for action in expectations.required_actions:
        if action not in action_set:
            failures.append(f"missing required action: {action}")
    for action in expectations.forbidden_actions:
        if action in action_set:
            failures.append(f"forbidden action observed: {action}")

    for tool in expectations.required_tools:
        if registered_tools and tool not in registered_tools:
            warnings.append(f"expected tool is not registered: {tool}")
        if tool not in executable_tool_set:
            failures.append(f"missing required tool: {tool}")
    for tool in expectations.forbidden_tools:
        if tool in tool_set:
            failures.append(f"forbidden tool observed: {tool}")
    if expectations.allowed_tool_groups:
        allowed_groups = set(expectations.allowed_tool_groups)
        for tool in sorted(tool_set):
            entry = registered_tool_catalog.get(tool)
            if entry is not None and entry.group not in allowed_groups:
                failures.append(
                    f"tool group not allowed: {tool} group={entry.group}"
                )
    if expectations.max_tool_disclosure_level is not None:
        max_level = expectations.max_tool_disclosure_level
        for tool in sorted(tool_set):
            entry = registered_tool_catalog.get(tool)
            if entry is not None and entry.progressive_disclosure_level > max_level:
                failures.append(
                    "tool disclosure level above threshold: "
                    f"{tool} level={entry.progressive_disclosure_level} > {max_level}"
                )

    for skill in expectations.required_skills:
        # Accept either "tier:name" or bare skill name in audit metadata.
        if skill not in skills and not any(s.endswith(f":{skill}") for s in skills):
            failures.append(f"missing required skill: {skill}")

    if expectations.expected_memory:
        memory_seen = bool(
            {"memory_recall", "memory_retain"} & action_set
            or {"memory_search", "memory_add", "save_memory", "load_memory"} & tool_set
        )
        if not memory_seen:
            failures.append("missing expected memory activity")

    for route in expectations.required_memory_routes:
        if route not in memory_routes:
            failures.append(f"missing required memory route: {route}")
    for provider in expectations.required_memory_providers:
        if provider not in memory_providers:
            failures.append(f"missing required memory provider: {provider}")
    for route in expectations.forbidden_memory_routes:
        if route in memory_routes:
            failures.append(f"forbidden memory route observed: {route}")
    for provider in expectations.forbidden_memory_providers:
        if provider in memory_providers:
            failures.append(f"forbidden memory provider observed: {provider}")

    for term in expectations.required_response_terms:
        if _normalized_gate_text(term) not in normalized_response:
            failures.append(f"missing required response term: {term}")
    for term in expectations.forbidden_response_terms:
        if _normalized_gate_text(term) in normalized_response:
            failures.append(f"forbidden response term observed: {term}")
    for term in expectations.required_memory_evidence_terms:
        if _normalized_gate_text(term) not in memory_blob:
            failures.append(f"missing required memory evidence term: {term}")
    for key in expectations.required_memory_metadata_keys:
        if key not in memory_metadata_keys and not any(
            _metadata_contains_key(_event_metadata(event), key)
            for event in events
            if _event_action(event) in {"memory_recall", "memory_retain"}
        ):
            failures.append(f"missing required memory metadata key: {key}")
    for action, keys in expectations.required_event_metadata_keys.items():
        matching_events = [event for event in events if _event_action(event) == action]
        if not matching_events:
            failures.append(f"missing action for metadata gate: {action}")
            continue
        for key in keys:
            if not any(
                _metadata_contains_key(_event_metadata(event), key)
                for event in matching_events
            ):
                failures.append(
                    f"missing required metadata key for {action}: {key}"
                )
    for action, keys in expectations.forbidden_event_metadata_keys.items():
        matching_events = [event for event in events if _event_action(event) == action]
        for key in keys:
            if any(
                _metadata_contains_key(_event_metadata(event), key)
                for event in matching_events
            ):
                failures.append(f"forbidden metadata key for {action}: {key}")
    for action, values in expectations.required_event_metadata_values.items():
        matching_events = [event for event in events if _event_action(event) == action]
        if not matching_events:
            failures.append(f"missing action for metadata value gate: {action}")
            continue
        for key, expected in values.items():
            if not any(
                _metadata_value_matches(_metadata_value(_event_metadata(event), key), expected)
                for event in matching_events
            ):
                failures.append(
                    f"missing required metadata value for {action}: {key}={expected}"
                )
    for action, values in expectations.forbidden_event_metadata_values.items():
        matching_events = (
            events
            if action == "*"
            else [event for event in events if _event_action(event) == action]
        )
        for key, forbidden in values.items():
            if any(
                _metadata_value_matches(
                    _metadata_value(_event_metadata(event), key),
                    forbidden,
                )
                for event in matching_events
            ):
                failures.append(
                    f"forbidden metadata value for {action}: {key}={forbidden}"
                )
    for name in expectations.required_runtime_event_names:
        if name not in runtime_event_names:
            failures.append(f"missing required runtime event: {name}")
    for name, keys in expectations.required_runtime_event_metadata_keys.items():
        matching_events = [
            event for event in runtime_events if _runtime_event_name(event) == name
        ]
        if not matching_events:
            failures.append(f"missing runtime event for metadata gate: {name}")
            continue
        for key in keys:
            if not any(
                _metadata_contains_key(_runtime_event_metadata(event), key)
                for event in matching_events
            ):
                failures.append(
                    f"missing required runtime metadata key for {name}: {key}"
                )
    for name, keys in expectations.forbidden_runtime_event_metadata_keys.items():
        matching_events = (
            runtime_events
            if name == "*"
            else [event for event in runtime_events if _runtime_event_name(event) == name]
        )
        for key in keys:
            if any(
                _metadata_contains_key(_runtime_event_metadata(event), key)
                for event in matching_events
            ):
                failures.append(
                    f"forbidden runtime metadata key for {name}: {key}"
                )
    for name, values in expectations.required_runtime_event_metadata_values.items():
        matching_events = [
            event for event in runtime_events if _runtime_event_name(event) == name
        ]
        if not matching_events:
            failures.append(f"missing runtime event for metadata value gate: {name}")
            continue
        for key, expected in values.items():
            if not any(
                _metadata_value_matches(
                    _metadata_value(_runtime_event_metadata(event), key),
                    expected,
                )
                for event in matching_events
            ):
                failures.append(
                    "missing required runtime metadata value for "
                    f"{name}: {key}={expected}"
                )
    for name, values in expectations.forbidden_runtime_event_metadata_values.items():
        matching_events = (
            runtime_events
            if name == "*"
            else [event for event in runtime_events if _runtime_event_name(event) == name]
        )
        for key, forbidden in values.items():
            if any(
                _metadata_value_matches(
                    _metadata_value(_runtime_event_metadata(event), key),
                    forbidden,
                )
                for event in matching_events
            ):
                failures.append(
                    "forbidden runtime metadata value for "
                    f"{name}: {key}={forbidden}"
                )
    for decision in expectations.required_route_decisions:
        if decision not in route_decisions:
            failures.append(f"missing required route decision: {decision}")
    for runner in expectations.required_runner_variants:
        if runner not in runner_variants:
            failures.append(f"missing required runner variant: {runner}")
    for delegation in expectations.required_delegation_decisions:
        if delegation not in delegation_decisions:
            failures.append(f"missing required delegation decision: {delegation}")
    if expectations.max_spawn_depth is not None:
        if observed_max_spawn_depth is None:
            failures.append("missing route spawn depth")
        elif observed_max_spawn_depth > expectations.max_spawn_depth:
            failures.append(
                "spawn depth above threshold: "
                f"{observed_max_spawn_depth} > {expectations.max_spawn_depth}"
            )

    if expectations.max_provider_retry_events is not None:
        retry_events = [
            event
            for event in events
            if _event_action(event) in {"provider_retry", "llm_retry"}
            or bool(_event_metadata(event).get("provider_retry"))
        ]
        if len(retry_events) > expectations.max_provider_retry_events:
            failures.append(
                "provider retry events above threshold: "
                f"{len(retry_events)} > {expectations.max_provider_retry_events}"
            )

    tool_results = [event for event in events if _event_action(event) == "tool_result"]
    tool_success_rate: float | None = None
    if tool_results:
        for event in tool_results:
            tool_name = _event_tool(event) or "<unknown>"
            unavailable_reason = _tool_unavailable_reason(
                tool_name,
                _event_output(event),
            )
            if unavailable_reason:
                failures.append(unavailable_reason)
        if expectations.max_repeated_tool_failures_per_tool is not None:
            failed_counts: dict[str, int] = {}
            for event in tool_results:
                if event.get("success") is not False:
                    continue
                tool_name = _event_tool(event) or "<unknown>"
                failed_counts[tool_name] = failed_counts.get(tool_name, 0) + 1
            for tool_name, count in sorted(failed_counts.items()):
                if count > expectations.max_repeated_tool_failures_per_tool:
                    failures.append(
                        "repeated tool failures above threshold: "
                        f"{tool_name} count={count} > "
                        f"{expectations.max_repeated_tool_failures_per_tool}"
                    )
        successes = sum(1 for event in tool_results if event.get("success") is True)
        tool_success_rate = round(successes / len(tool_results), 3)
        if not expectations.allow_tool_failures:
            failed_tools = [
                _event_tool(event) or "<unknown>"
                for event in tool_results
                if event.get("success") is False
            ]
            if failed_tools:
                failures.append(
                    "tool failures observed: " + ", ".join(sorted(set(failed_tools)))
                )
    if (
        expectations.min_tool_success_rate is not None
        and tool_success_rate is None
    ):
        failures.append("missing tool_result events for tool success rate threshold")
    elif (
        expectations.min_tool_success_rate is not None
        and tool_success_rate is not None
        and tool_success_rate < expectations.min_tool_success_rate
    ):
        failures.append(
            "tool success rate below threshold: "
            f"{tool_success_rate} < {expectations.min_tool_success_rate}"
        )

    return TraceGateVerdict(
        passed=not failures,
        failures=tuple(failures),
        warnings=tuple(warnings),
        observed_actions=tuple(sorted(action_set)),
        observed_tools=tuple(sorted(tool_set)),
        observed_skills=tuple(sorted(skills)),
        observed_memory_routes=tuple(sorted(memory_routes)),
        observed_memory_providers=tuple(sorted(memory_providers)),
        tool_success_rate=tool_success_rate,
    )


def evaluate_stream_gates(
    chunks: list[str],
    expectations: TraceExpectations,
) -> StreamGateVerdict:
    """Evaluate what the Agent Chat UI can render from SSE data parts."""
    payloads = [
        payload
        for payload in (_parse_sse_payload(chunk) for chunk in chunks)
        if payload is not None
    ]
    observed_parts = {
        str(payload.get("type"))
        for payload in payloads
        if payload.get("type")
    }
    tool_outputs = [
        payload
        for payload in payloads
        if payload.get("type") == "tool-output-available"
    ]
    tool_starts = [
        payload
        for payload in payloads
        if str(payload.get("type") or "").startswith("tool-input")
    ]
    tool_name_by_call_id = {
        str(payload.get("toolCallId")): str(payload.get("toolName") or "")
        for payload in tool_starts
        if payload.get("toolCallId") and payload.get("toolName")
    }
    observed_tools = {
        str(payload.get("toolName") or "")
        for payload in [*tool_starts, *tool_outputs]
        if payload.get("toolName")
    }
    rich_renderers = {
        tool
        for tool in observed_tools
        if tool
        in {
            "file_analyze",
            "get_chart_state",
            "get_portfolio_summary",
            "render_a2ui_surface",
            "sandbox_execute",
        }
    }
    artifact_files: set[str] = set()
    failures: list[str] = []
    warnings: list[str] = []

    for payload in tool_outputs:
        tool_name = str(payload.get("toolName") or "") or tool_name_by_call_id.get(
            str(payload.get("toolCallId") or ""),
            "",
        )
        output = payload.get("output")
        unavailable_reason = _tool_unavailable_reason(tool_name, output)
        if unavailable_reason:
            failures.append(f"stream {unavailable_reason}")
        if isinstance(output, dict):
            for item in output.get("files") or []:
                if isinstance(item, dict) and item.get("name"):
                    artifact_files.add(str(item["name"]))

    for tool in expectations.required_tools:
        if tool not in observed_tools:
            failures.append(f"missing stream tool part: {tool}")

    for part in expectations.required_stream_parts:
        if part not in observed_parts:
            failures.append(f"missing stream part: {part}")
    for renderer in expectations.required_stream_rich_renderers:
        if renderer not in rich_renderers:
            failures.append(f"missing stream rich renderer: {renderer}")
    for artifact_file in expectations.required_stream_artifact_files:
        if artifact_file not in artifact_files:
            failures.append(f"missing stream artifact file: {artifact_file}")

    if expectations.required_tools and "tool-output-available" not in observed_parts:
        failures.append("missing stream tool-output-available part")
    if "finish" not in observed_parts:
        failures.append("missing stream finish part")
    if "text-delta" not in observed_parts:
        warnings.append("missing stream text-delta part")

    return StreamGateVerdict(
        passed=not failures,
        failures=tuple(failures),
        warnings=tuple(warnings),
        observed_parts=tuple(sorted(observed_parts)),
        observed_tools=tuple(sorted(observed_tools)),
        observed_rich_renderers=tuple(sorted(rich_renderers)),
        observed_artifact_files=tuple(sorted(artifact_files)),
    )


def _parse_sse_payload(chunk: str) -> dict[str, Any] | None:
    if not chunk.startswith("data:"):
        return None
    raw = chunk.removeprefix("data:").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def assistant_text_from_sse(chunks: list[str]) -> str:
    """Extract assistant text deltas from Matrix Agent SSE chunks."""
    parts: list[str] = []
    for chunk in chunks:
        payload = _parse_sse_payload(chunk)
        if payload and payload.get("type") == "text-delta":
            parts.append(str(payload.get("delta") or ""))
    return "".join(parts)


def sse_finished(chunks: list[str]) -> bool:
    """Return True if Matrix Agent SSE emitted a terminal finish packet."""
    return any(
        bool(payload and payload.get("type") == "finish")
        for payload in (_parse_sse_payload(chunk) for chunk in chunks)
    )


async def _default_agent_runner(
    *,
    thread_id: str,
    user_id: str,
    model: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    enable_tools: bool,
    consent_allow_session_tools: tuple[str, ...] = (),
    run_id: str = "",
    scenario_id: str = "",
    runner_variant: str = "dispatcher",
) -> list[str]:
    from agent.context import AgentExecutionContext
    from agent.tools.registry import ToolRegistry

    del consent_allow_session_tools, run_id, scenario_id
    registry = ToolRegistry.load() if enable_tools else ToolRegistry()
    ctx = AgentExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        model=model,
        system_prompt=system_prompt,
        tools=tuple(registry.all()),
        api_key=_harness_env_api_key(model),
    )
    chunks: list[str] = []
    async for chunk in _stream_agent_loop_for_variant(
        _normalize_runner_variant(runner_variant),
        ctx,
        messages,
    ):
        chunks.append(chunk)
    return chunks


AgentRunner = Callable[..., Awaitable[list[str]]]


async def _stream_agent_loop_for_variant(
    runner_variant: str,
    ctx: Any,
    messages: list[dict[str, Any]],
):
    """Stream one agent loop using the requested runtime shape."""
    if runner_variant == "dispatcher":
        from agent.runners.dispatcher import run_agent_loop_with_variant

        async for chunk in run_agent_loop_with_variant(ctx, messages):
            yield chunk
        return
    if runner_variant == "simple":
        from agent.runners.simple import run_simple_agent_loop

        async for chunk in run_simple_agent_loop(ctx, messages):
            yield chunk
        return

    from agent.graph.runner import run_agent_loop

    async for chunk in run_agent_loop(ctx, messages):
        yield chunk


def _meta_harness_service_headers(
    *,
    user_id: str,
    model: str = "",
    run_id: str,
    scenario_id: str,
    consent_allow_session_tools: tuple[str, ...] = (),
) -> dict[str, str]:
    headers = {
        "accept": "text/event-stream",
        "x-auth-user": user_id,
        "x-user-role": "admin",
    }
    if consent_allow_session_tools:
        headers["x-meta-harness-run-id"] = run_id
        headers["x-meta-harness-scenario-id"] = scenario_id
        headers["x-meta-harness-consent-allow-tools"] = ",".join(
            consent_allow_session_tools
        )
    if run_id:
        headers["x-meta-harness-run-id"] = run_id
        headers["x-meta-harness-scenario-id"] = scenario_id
        env_api_key = _harness_env_api_key(model)
        if env_api_key:
            headers["x-meta-harness-api-key"] = env_api_key
    return headers


def _agent_chat_endpoint_url(agent_url: str) -> tuple[str, bool]:
    """Return the concrete chat endpoint and whether it is a frontend BFF route."""
    clean_url = agent_url.rstrip("/")
    if clean_url.endswith("/api/agent/chat"):
        return clean_url, True
    if clean_url.endswith("/api/v1/agent/chat"):
        return clean_url, False
    return f"{clean_url}/api/v1/agent/chat", False


def service_agent_runner(agent_url: str) -> AgentRunner:
    """Create a runner that drives the live FastAPI agent chat endpoint."""
    chat_url, is_frontend_bff = _agent_chat_endpoint_url(agent_url)

    async def _runner(
        *,
        thread_id: str,
        user_id: str,
        model: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        enable_tools: bool,
        consent_allow_session_tools: tuple[str, ...] = (),
        run_id: str = "",
        scenario_id: str = "",
        runner_variant: str = "dispatcher",
    ) -> list[str]:
        import httpx

        del enable_tools, runner_variant
        current_user_message = next(
            (
                str(message.get("content") or "")
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )
        payload: dict[str, Any] = {
            "message": current_user_message,
            "threadId": thread_id,
        }
        if model:
            payload["model"] = model
        if system_prompt:
            payload["context"] = system_prompt
        if run_id and not is_frontend_bff:
            payload["metaHarnessRunId"] = run_id
            payload["metaHarnessScenarioId"] = scenario_id
            env_api_key = _harness_env_api_key(model)
            if env_api_key:
                payload["metaHarnessApiKey"] = env_api_key

        chunks: list[str] = []
        headers = _meta_harness_service_headers(
            user_id=user_id,
            model=model,
            run_id=run_id,
            scenario_id=scenario_id,
            consent_allow_session_tools=consent_allow_session_tools,
        )
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                chat_url,
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        chunks.append(f"{line}\n\n")
        return chunks

    return _runner


async def run_scenario(
    scenario: Scenario,
    *,
    run_id: str | None = None,
    candidate_id: str = "baseline",
    user_id: str = "anonymous",
    thread_id: str | None = None,
    model: str = "",
    system_prompt_override: str = "",
    runner: AgentRunner | None = None,
    runner_variant: str = "",
    write_artifacts: bool = True,
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> ScenarioRunResult:
    """Run one scenario against the Python agent and evaluate trace gates."""
    run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    thread_id = thread_id or f"mh-{scenario.id}-{uuid.uuid4().hex[:8]}"
    model = model or _default_agent_model()
    runner = runner or _default_agent_runner
    effective_runner_variant = _normalize_runner_variant(
        runner_variant or scenario.runner_variant
    )

    if scenario.consent_allow_session_tools:
        from agent.consent import record_consent_decision

        for tool_name in scenario.consent_allow_session_tools:
            await record_consent_decision(
                thread_id=thread_id,
                tool_name=tool_name,
                user_decision="allow_session",
                allow_session_cache=True,
            )

    messages: list[dict[str, Any]] = []
    transcript: list[dict[str, str]] = []
    all_sse: list[str] = []
    timeout_errors: list[str] = []
    runner_errors: list[str] = []
    for turn in scenario.turns:
        turn_timed_out = False
        turn_failed = False
        messages.append({"role": "user", "content": turn.user})
        transcript.append({"role": "user", "content": turn.user})
        timeout_s = _turn_timeout_seconds()
        try:
            chunks = await asyncio.wait_for(
                runner(
                    thread_id=thread_id,
                    user_id=user_id,
                    model=model,
                    system_prompt=system_prompt_override,
                    messages=messages,
                    enable_tools=scenario.enable_tools,
                    consent_allow_session_tools=scenario.consent_allow_session_tools,
                    run_id=run_id,
                    scenario_id=scenario.id,
                    runner_variant=effective_runner_variant,
                ),
                timeout=timeout_s,
            )
        except TimeoutError:
            message = (
                f"turn timed out after {timeout_s:.1f}s "
                f"(scenario={scenario.id}, runner={effective_runner_variant})"
            )
            logger.warning("Meta-Harness %s", message)
            timeout_errors.append(message)
            turn_timed_out = True
            chunks = []
        except Exception as exc:  # noqa: BLE001
            message = (
                f"runner error {type(exc).__name__}: {exc} "
                f"(scenario={scenario.id}, runner={effective_runner_variant})"
            )
            logger.warning("Meta-Harness %s", message)
            runner_errors.append(message)
            turn_failed = True
            chunks = []
        all_sse.extend(chunks)
        assistant_text = assistant_text_from_sse(chunks)
        if assistant_text:
            messages.append({"role": "assistant", "content": assistant_text})
            transcript.append({"role": "assistant", "content": assistant_text})
        elif timeout_errors:
            transcript.append(
                {"role": "assistant", "content": f"[meta-harness timeout] {timeout_errors[-1]}"}
            )
        elif runner_errors:
            transcript.append(
                {"role": "assistant", "content": f"[meta-harness runner error] {runner_errors[-1]}"}
            )
        if turn_timed_out or turn_failed:
            break

    events = await _query_trace_events(thread_id)
    score = await score_session(thread_id, eval_id=run_id)
    if sse_finished(all_sse) and not score.get("completed"):
        score["completed"] = True
        score["completion_source"] = "sse_finish"
        score["fitness_score"] = composite_fitness(score)
    if timeout_errors:
        score["completed"] = False
        score["harness_timeout"] = True
        score["timeout_errors"] = timeout_errors
        score["fitness_score"] = composite_fitness(score)
    if runner_errors:
        score["completed"] = False
        score["harness_runner_error"] = True
        score["runner_errors"] = runner_errors
        score["fitness_score"] = composite_fitness(score)
    response_text = "\n".join(
        item["content"] for item in transcript if item.get("role") == "assistant"
    )
    verdict = evaluate_trace_gates(
        events,
        scenario.expectations,
        response_text=response_text,
    )
    stream_verdict = evaluate_stream_gates(all_sse, scenario.expectations)
    if timeout_errors:
        verdict = replace(
            verdict,
            passed=False,
            failures=tuple([*verdict.failures, "harness timeout"]),
        )
        stream_verdict = replace(
            stream_verdict,
            passed=False,
            failures=tuple([*stream_verdict.failures, "harness timeout"]),
        )
    if runner_errors:
        verdict = replace(
            verdict,
            passed=False,
            failures=tuple([*verdict.failures, "harness runner error"]),
        )
        stream_verdict = replace(
            stream_verdict,
            passed=False,
            failures=tuple([*stream_verdict.failures, "harness runner error"]),
        )
    score["trace_gates"] = verdict.as_dict()
    score["stream_gates"] = stream_verdict.as_dict()

    result = ScenarioRunResult(
        run_id=run_id,
        candidate_id=candidate_id,
        scenario_id=scenario.id,
        thread_id=thread_id,
        user_id=user_id,
        category=scenario.category,
        turns=len(scenario.turns),
        transcript=tuple(transcript),
        sse_chunks=tuple(all_sse),
        trace_events=tuple(events),
        score=score,
        trace_verdict=verdict,
        stream_verdict=stream_verdict,
        runner_variant=effective_runner_variant,
    )
    if write_artifacts:
        artifact_dir = write_scenario_artifacts(result, scenario, data_dir=data_dir)
        result = replace(result, artifact_dir=str(artifact_dir))
    return result


async def _query_trace_events(
    thread_id: str,
    *,
    limit: int = 1000,
    attempts: int = 8,
    delay_seconds: float = 0.35,
) -> list[dict[str, Any]]:
    """Fetch audit events, allowing live-service writes to settle."""
    from agent.audit.store import get_audit_store

    store = get_audit_store()
    events: list[dict[str, Any]] = []
    for attempt in range(max(1, attempts)):
        events = await store.query(thread_id=thread_id, limit=limit)
        if events:
            return events
        if attempt < attempts - 1:
            await asyncio.sleep(delay_seconds)
    return events


def load_scenarios(path: Path) -> list[Scenario]:
    """Load scenario fixtures from a JSON file.

    Accepts either {"scenarios": [...]} or the legacy {"queries": [...]} shape.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_items = data.get("scenarios") or data.get("queries") or []
    return [Scenario.from_mapping(item) for item in raw_items]


def write_scenario_artifacts(
    result: ScenarioRunResult,
    scenario: Scenario,
    *,
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> Path:
    """Write a filesystem-queryable candidate artifact directory."""
    from meta_harness.config import capture_trace_source_config

    candidate_dir = (
        data_dir / "runs" / result.run_id / "candidates" / result.candidate_id
    )
    trace_source = capture_trace_source_config()
    trace_dir = candidate_dir / "traces" / result.scenario_id
    sse_dir = candidate_dir / "sse"
    result_dir = candidate_dir / "results"
    trace_dir.mkdir(parents=True, exist_ok=True)
    sse_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    run_manifest = {
        "run_id": result.run_id,
        "candidate_id": result.candidate_id,
        "created_at": datetime.now(UTC).isoformat(),
        "stack": {
            "python_agent": True,
            "frontend_required": False,
            "go_gateway_required": False,
            "memory_engine": os.environ.get("AGENT_MEMORY_ENGINE", "auto"),
            "litellm_base_url": os.environ.get("LITELLM_BASE_URL", ""),
            "agent_max_output_tokens": os.environ.get("AGENT_MAX_OUTPUT_TOKENS", ""),
            "trace_store": trace_source,
        },
    }
    (data_dir / "runs" / result.run_id / "run.json").write_text(
        json.dumps(run_manifest, indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "scenario_set.json").write_text(
        json.dumps({"scenarios": [asdict(scenario)]}, indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "config.json").write_text(
        json.dumps(_capture_config_snapshot(), indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps(_source_snapshot(), indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "scores.json").write_text(
        json.dumps(result.score, indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "verdicts.json").write_text(
        json.dumps(
            {
                **result.trace_verdict.as_dict(),
                "trace": result.trace_verdict.as_dict(),
                "stream": result.stream_verdict.as_dict()
                if result.stream_verdict is not None
                else None,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (trace_dir / f"{result.thread_id}.json").write_text(
        json.dumps(list(result.trace_events), indent=2, default=str),
        encoding="utf-8",
    )
    (sse_dir / f"{result.scenario_id}.jsonl").write_text(
        "".join(
            json.dumps({"chunk": chunk}, default=str) + "\n"
            for chunk in result.sse_chunks
        ),
        encoding="utf-8",
    )
    (candidate_dir / "result.json").write_text(
        json.dumps(result.as_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    (result_dir / f"{result.scenario_id}.json").write_text(
        json.dumps(result.as_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    try:
        from meta_harness.outer_loop import write_candidate_manifest

        write_candidate_manifest(candidate_dir)
    except Exception as exc:  # noqa: BLE001
        (candidate_dir / "candidate_manifest_error.json").write_text(
            json.dumps({"error": str(exc)}, indent=2, default=str),
            encoding="utf-8",
        )
    return candidate_dir


def _aggregate_results(results: list[ScenarioRunResult]) -> dict[str, Any]:
    n = len(results)
    completed = sum(1 for r in results if r.score.get("completed"))
    trace_passed = sum(1 for r in results if r.trace_verdict.passed)
    stream_passed = sum(
        1 for r in results if r.stream_verdict is None or r.stream_verdict.passed
    )
    total_tokens = sum(int(r.score.get("total_tokens") or 0) for r in results)
    total_cost = sum(float(r.score.get("cost_estimate_usd") or 0.0) for r in results)
    total_duration = sum(float(r.score.get("total_duration_ms") or 0.0) for r in results)
    avg_turns = sum(r.turns for r in results) / max(n, 1)
    fitness_values = [
        float(r.score.get("fitness_score"))
        for r in results
        if r.score.get("fitness_score") is not None
    ]
    tool_rates = [
        float(r.trace_verdict.tool_success_rate)
        for r in results
        if r.trace_verdict.tool_success_rate is not None
    ]
    memory_used = sum(1 for r in results if r.score.get("memory_utilization"))
    avg_tokens = total_tokens / max(n, 1)
    avg_cost = total_cost / max(n, 1)
    avg_duration = total_duration / max(n, 1)

    return {
        "run_id": results[0].run_id if results else "",
        "candidate_id": results[0].candidate_id if results else "",
        "scenarios_evaluated": n,
        "completion_rate": round(completed / max(n, 1), 4),
        "trace_gate_pass_rate": round(trace_passed / max(n, 1), 4),
        "stream_gate_pass_rate": round(stream_passed / max(n, 1), 4),
        "avg_turns": round(avg_turns, 3),
        "turn_efficiency": round(1.0 / max(avg_turns, 1.0), 4),
        "tool_success_rate": round(sum(tool_rates) / len(tool_rates), 4)
        if tool_rates
        else 1.0,
        "memory_utilization_rate": round(memory_used / max(n, 1), 4),
        "avg_fitness_score": round(sum(fitness_values) / len(fitness_values), 4)
        if fitness_values
        else 0.0,
        "fitness_score": round(sum(fitness_values) / len(fitness_values), 4)
        if fitness_values
        else 0.0,
        "total_tokens": total_tokens,
        "avg_tokens": round(avg_tokens, 1),
        "token_efficiency": round(1000.0 / max(avg_tokens, 1.0), 6),
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_usd": round(avg_cost, 6),
        "cost_efficiency": round(1.0 / (1.0 + max(avg_cost, 0.0)), 6),
        "total_duration_ms": round(total_duration, 1),
        "avg_duration_ms": round(avg_duration, 1),
        "latency_efficiency": round(1000.0 / max(avg_duration, 1.0), 6)
        if avg_duration > 0
        else 1.0,
        "failed_scenarios": [
            {
                "scenario_id": r.scenario_id,
                "failures": list(r.trace_verdict.failures),
                "stream_failures": list(r.stream_verdict.failures)
                if r.stream_verdict is not None
                else [],
                "observed_actions": list(r.trace_verdict.observed_actions),
                "observed_tools": list(r.trace_verdict.observed_tools),
                "observed_stream_tools": list(r.stream_verdict.observed_tools)
                if r.stream_verdict is not None
                else [],
                "observed_skills": list(r.trace_verdict.observed_skills),
            }
            for r in results
            if not r.trace_verdict.passed
            or (r.stream_verdict is not None and not r.stream_verdict.passed)
        ],
    }


def write_run_aggregate(
    results: list[ScenarioRunResult],
    *,
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Write candidate-level aggregate metrics for Pareto/frontier ranking."""
    aggregate = _aggregate_results(results)
    if not results:
        return aggregate
    candidate_dir = (
        data_dir / "runs" / results[0].run_id / "candidates" / results[0].candidate_id
    )
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "scores.json").write_text(
        json.dumps(aggregate, indent=2, default=str),
        encoding="utf-8",
    )
    (candidate_dir / "results.json").write_text(
        json.dumps([r.as_dict() for r in results], indent=2, default=str),
        encoding="utf-8",
    )
    return aggregate


def _capture_config_snapshot() -> dict[str, Any]:
    try:
        from meta_harness.config import capture_current_config

        return json.loads(capture_current_config().to_json())
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _source_snapshot() -> dict[str, Any]:
    """Small source fingerprint for proposer navigation and reproducibility."""
    root = Path(__file__).resolve().parents[2]
    paths = [
        "python-backend/agent/app.py",
        "python-backend/agent/runners/dispatcher.py",
        "python-backend/agent/runners/simple.py",
        "python-backend/agent/graph/runner.py",
        "python-backend/agent/graph/nodes/llm_node.py",
        "python-backend/agent/graph/nodes/tool_node.py",
        "python-backend/agent/graph/nodes/memory_node.py",
        "python-backend/agent/tools/registry.py",
        "python-backend/meta_harness/evaluator.py",
        "python-backend/meta_harness/scenario_runner.py",
    ]
    files = []
    for rel in paths:
        path = root / rel
        if not path.exists():
            continue
        data = path.read_bytes()
        files.append(
            {
                "path": rel,
                "sha256": sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return {"files": files}


async def run_scenario_file(
    path: Path,
    *,
    max_scenarios: int = 0,
    run_id: str | None = None,
    candidate_id: str = "baseline",
    user_id: str = "anonymous",
    model: str = "",
    system_prompt_override: str = "",
    agent_url: str = "",
    runner_variant: str = "",
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Run a JSON scenario file and aggregate trace verdicts."""
    scenarios = load_scenarios(path)
    if max_scenarios > 0:
        scenarios = scenarios[:max_scenarios]
    run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    runner = service_agent_runner(agent_url) if agent_url else None
    if runner_variant:
        _normalize_runner_variant(runner_variant)
    effective_model = model or _default_agent_model()
    results = [
        await run_scenario(
            scenario,
            run_id=run_id,
            candidate_id=candidate_id,
            user_id=user_id,
            model=effective_model,
            system_prompt_override=system_prompt_override,
            runner=runner,
            runner_variant=runner_variant,
            data_dir=data_dir,
        )
        for scenario in scenarios
    ]
    aggregate = write_run_aggregate(results, data_dir=data_dir)
    return {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "scenarios_evaluated": len(results),
        "trace_gate_pass_rate": aggregate["trace_gate_pass_rate"],
        "completion_rate": aggregate["completion_rate"],
        "fitness_score": aggregate["fitness_score"],
        "artifact_dir": str(data_dir / "runs" / run_id / "candidates" / candidate_id),
        "results": [r.as_dict() for r in results],
    }


async def run_runner_parity_file(
    path: Path,
    *,
    max_scenarios: int = 0,
    run_id: str | None = None,
    candidate_id_prefix: str = "runner-parity",
    user_id: str = "anonymous",
    model: str = "",
    system_prompt_override: str = "",
    data_dir: Path = META_HARNESS_DATA_DIR,
    variants: Sequence[str] = RUNNER_VARIANTS,
) -> dict[str, Any]:
    """Run the same scenarios across agent runner variants and compare gates."""

    run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    normalized_variants = tuple(_normalize_runner_variant(value) for value in variants)
    by_variant: dict[str, dict[str, Any]] = {}
    scenario_matrix: dict[str, dict[str, bool]] = {}
    for variant in normalized_variants:
        result = await run_scenario_file(
            path,
            max_scenarios=max_scenarios,
            run_id=run_id,
            candidate_id=f"{candidate_id_prefix}-{variant}",
            user_id=user_id,
            model=model,
            system_prompt_override=system_prompt_override,
            runner_variant=variant,
            data_dir=data_dir,
        )
        by_variant[variant] = {
            "candidate_id": result["candidate_id"],
            "trace_gate_pass_rate": result["trace_gate_pass_rate"],
            "completion_rate": result["completion_rate"],
            "fitness_score": result["fitness_score"],
            "artifact_dir": result["artifact_dir"],
        }
        for scenario_result in result["results"]:
            scenario_id = str(scenario_result["scenario_id"])
            verdict = scenario_result.get("trace_verdict") or {}
            scenario_matrix.setdefault(scenario_id, {})[variant] = bool(
                verdict.get("passed")
            )

    mismatches = {
        scenario_id: outcomes
        for scenario_id, outcomes in sorted(scenario_matrix.items())
        if len(set(outcomes.values())) > 1
    }
    all_variants_trace_passed = all(
        all(outcomes.values()) for outcomes in scenario_matrix.values()
    )
    return {
        "run_id": run_id,
        "variants": list(normalized_variants),
        "by_variant": by_variant,
        "scenario_matrix": scenario_matrix,
        "parity_passed": not mismatches and all_variants_trace_passed,
        "all_variants_trace_passed": all_variants_trace_passed,
        "mismatches": mismatches,
    }
