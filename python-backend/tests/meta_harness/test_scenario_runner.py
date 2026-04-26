from __future__ import annotations

import json
import os

import pytest

from agent.streaming import FinishPacket, TextDeltaPacket, TextStartPacket, sse
from meta_harness import evaluator, meta_cli, scenario_runner


def test_trace_gates_pass_with_required_tools_memory_and_skills(monkeypatch):
    monkeypatch.setattr(
        scenario_runner,
        "_registered_tool_names",
        lambda: {"memory_search", "get_chart_state"},
    )
    events = [
        {"action": "memory_recall", "success": True},
        {
            "action": "tool_result",
            "toolName": "memory_search",
            "success": True,
        },
        {
            "action": "skill_used",
            "metadata": {"skill_ids": ["global:memory-usage"]},
            "success": True,
        },
    ]

    verdict = scenario_runner.evaluate_trace_gates(
        events,
        scenario_runner.TraceExpectations(
            required_tools=("memory_search",),
            required_skills=("memory-usage",),
            expected_memory=True,
            min_tool_success_rate=1.0,
        ),
    )

    assert verdict.passed is True
    assert verdict.failures == ()
    assert verdict.observed_tools == ("memory_search",)


def test_trace_gates_fail_for_missing_and_forbidden_tool(monkeypatch):
    monkeypatch.setattr(
        scenario_runner,
        "_registered_tool_names",
        lambda: {"memory_search", "schedule_task"},
    )
    events = [
        {"action": "tool_result", "toolName": "schedule_task", "success": True},
    ]

    verdict = scenario_runner.evaluate_trace_gates(
        events,
        scenario_runner.TraceExpectations(
            required_tools=("memory_search",),
            forbidden_tools=("schedule_task",),
            expected_memory=True,
        ),
    )

    assert verdict.passed is False
    assert "missing required tool: memory_search" in verdict.failures
    assert "forbidden tool observed: schedule_task" in verdict.failures
    assert "missing expected memory activity" in verdict.failures


def test_trace_gates_do_not_count_consent_request_as_tool_success(monkeypatch):
    monkeypatch.setattr(
        scenario_runner,
        "_registered_tool_names",
        lambda: {"sandbox_execute"},
    )
    events = [
        {
            "action": "consent_request",
            "tool_name": "sandbox_execute",
            "success": True,
        },
    ]

    verdict = scenario_runner.evaluate_trace_gates(
        events,
        scenario_runner.TraceExpectations(
            required_tools=("sandbox_execute",),
            min_tool_success_rate=1.0,
        ),
    )

    assert verdict.passed is False
    assert "missing required tool: sandbox_execute" in verdict.failures
    assert "missing tool_result events for tool success rate threshold" in verdict.failures


def test_trace_gates_fail_on_observed_tool_errors_by_default(monkeypatch):
    monkeypatch.setattr(
        scenario_runner,
        "_registered_tool_names",
        lambda: {"sandbox_browser"},
    )
    events = [
        {
            "action": "tool_result",
            "toolName": "sandbox_browser",
            "success": False,
        },
    ]

    strict = scenario_runner.evaluate_trace_gates(
        events,
        scenario_runner.TraceExpectations(),
    )
    tolerated = scenario_runner.evaluate_trace_gates(
        events,
        scenario_runner.TraceExpectations(allow_tool_failures=True),
    )

    assert strict.passed is False
    assert "tool failures observed: sandbox_browser" in strict.failures
    assert tolerated.passed is True


def test_trace_gates_check_memory_routes_and_providers(monkeypatch):
    monkeypatch.setattr(scenario_runner, "_registered_tool_names", lambda: set())
    events = [
        {
            "action": "memory_retain",
            "success": True,
            "metadata": {
                "route": "fusion",
                "providers": "summary,verbatim",
            },
        },
        {
            "action": "memory_recall",
            "success": True,
            "metadata": {
                "route": "verbatim",
                "provider": "fusion",
            },
        },
    ]

    verdict = scenario_runner.evaluate_trace_gates(
        events,
        scenario_runner.TraceExpectations(
            expected_memory=True,
            required_memory_routes=("fusion", "verbatim"),
            required_memory_providers=("summary", "verbatim", "fusion"),
        ),
    )

    assert verdict.passed is True
    assert verdict.observed_memory_routes == ("fusion", "verbatim")
    assert verdict.observed_memory_providers == ("fusion", "summary", "verbatim")


def test_legacy_query_maps_to_scenario():
    scenario = scenario_runner.Scenario.from_mapping(
        {
            "id": "q1",
            "message": "remember this",
            "category": "memory_recall",
            "expected_tools": ["memory_search"],
            "expected_skills": ["memory-usage"],
            "expected_memory": True,
        }
    )

    assert scenario.id == "q1"
    assert scenario.turns[0].user == "remember this"
    assert scenario.expectations.required_tools == ("memory_search",)
    assert scenario.expectations.required_skills == ("memory-usage",)
    assert scenario.expectations.expected_memory is True


def test_scenario_maps_consent_allow_session_tools():
    scenario = scenario_runner.Scenario.from_mapping(
        {
            "id": "consent",
            "turns": [{"user": "run sandbox"}],
            "consent": {"allow_session_tools": ["sandbox_execute"]},
        }
    )

    assert scenario.consent_allow_session_tools == ("sandbox_execute",)


def test_scenario_maps_runner_variant_from_top_level_and_metadata():
    top_level = scenario_runner.Scenario.from_mapping(
        {
            "id": "simple",
            "turns": [{"user": "hi"}],
            "runner_variant": "simple",
        }
    )
    metadata = scenario_runner.Scenario.from_mapping(
        {
            "id": "meta",
            "turns": [{"user": "hi"}],
            "metadata": {"runner_variant": "langgraph"},
        }
    )

    assert top_level.runner_variant == "simple"
    assert metadata.runner_variant == "langgraph"


def test_meta_harness_service_headers_include_consent_only_when_explicit():
    plain = scenario_runner._meta_harness_service_headers(
        user_id="anonymous",
        run_id="run-1",
        scenario_id="s1",
    )
    consent = scenario_runner._meta_harness_service_headers(
        user_id="anonymous",
        run_id="run-1",
        scenario_id="s1",
        consent_allow_session_tools=("sandbox_execute", "memory_add"),
    )

    assert "x-meta-harness-consent-allow-tools" not in plain
    assert consent["x-auth-user"] == "anonymous"
    assert consent["x-meta-harness-run-id"] == "run-1"
    assert consent["x-meta-harness-scenario-id"] == "s1"
    assert consent["x-meta-harness-consent-allow-tools"] == (
        "sandbox_execute,memory_add"
    )


def test_meta_cli_loads_env_files(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BASE_ONLY=1\nSHARED_VALUE=base\n", encoding="utf-8")
    (tmp_path / ".env.development").write_text(
        "SHARED_VALUE=dev\nDEV_ONLY=1\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("BASE_ONLY", raising=False)
    monkeypatch.delenv("SHARED_VALUE", raising=False)
    monkeypatch.delenv("DEV_ONLY", raising=False)

    meta_cli._load_env_files()

    assert os.environ["BASE_ONLY"] == "1"
    assert os.environ["SHARED_VALUE"] == "dev"
    assert os.environ["DEV_ONLY"] == "1"


def test_meta_cli_keeps_explicit_env_over_env_files(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SHARED_VALUE=base\n", encoding="utf-8")
    (tmp_path / ".env.development").write_text("SHARED_VALUE=dev\n", encoding="utf-8")
    monkeypatch.setenv("SHARED_VALUE", "explicit")

    meta_cli._load_env_files()

    assert os.environ["SHARED_VALUE"] == "explicit"


def test_write_scenario_artifacts(tmp_path):
    scenario = scenario_runner.Scenario.from_mapping(
        {"id": "s1", "turns": [{"user": "hi"}], "category": "smoke"}
    )
    verdict = scenario_runner.TraceGateVerdict(
        passed=True,
        failures=(),
        warnings=(),
        observed_actions=("llm_response",),
        observed_tools=(),
        observed_skills=(),
        tool_success_rate=None,
    )
    result = scenario_runner.ScenarioRunResult(
        run_id="run-test",
        candidate_id="baseline",
        scenario_id="s1",
        thread_id="thread-1",
        user_id="u1",
        category="smoke",
        turns=1,
        transcript=({"role": "user", "content": "hi"},),
        sse_chunks=("data: {}\n\n",),
        trace_events=({"action": "llm_response", "threadId": "thread-1"},),
        score={"thread_id": "thread-1", "fitness_score": 0.5},
        trace_verdict=verdict,
    )

    artifact_dir = scenario_runner.write_scenario_artifacts(
        result, scenario, data_dir=tmp_path
    )

    assert (artifact_dir / "scores.json").exists()
    assert (artifact_dir / "verdicts.json").exists()
    assert (artifact_dir / "config.json").exists()
    assert (artifact_dir / "source_snapshot.json").exists()
    trace_path = artifact_dir / "traces" / "s1" / "thread-1.json"
    assert json.loads(trace_path.read_text())[0]["action"] == "llm_response"


def test_sse_finished_detects_finish_packet():
    assert scenario_runner.sse_finished([sse(FinishPacket())]) is True
    assert scenario_runner.sse_finished([sse(TextStartPacket())]) is False


def test_write_run_aggregate_overwrites_candidate_scores(tmp_path):
    verdict_pass = scenario_runner.TraceGateVerdict(
        passed=True,
        failures=(),
        warnings=(),
        observed_actions=("llm_response",),
        observed_tools=(),
        observed_skills=(),
        tool_success_rate=None,
    )
    verdict_fail = scenario_runner.TraceGateVerdict(
        passed=False,
        failures=("missing required tool: get_chart_state",),
        warnings=(),
        observed_actions=("llm_response",),
        observed_tools=(),
        observed_skills=(),
        tool_success_rate=None,
    )
    results = [
        scenario_runner.ScenarioRunResult(
            run_id="run-agg",
            candidate_id="baseline",
            scenario_id="a",
            thread_id="t-a",
            user_id="u",
            category="smoke",
            turns=1,
            transcript=(),
            sse_chunks=(),
            trace_events=(),
            score={"completed": True, "total_tokens": 1000, "fitness_score": 1.0},
            trace_verdict=verdict_pass,
        ),
        scenario_runner.ScenarioRunResult(
            run_id="run-agg",
            candidate_id="baseline",
            scenario_id="b",
            thread_id="t-b",
            user_id="u",
            category="smoke",
            turns=1,
            transcript=(),
            sse_chunks=(),
            trace_events=(),
            score={"completed": True, "total_tokens": 3000, "fitness_score": 0.5},
            trace_verdict=verdict_fail,
        ),
    ]

    aggregate = scenario_runner.write_run_aggregate(results, data_dir=tmp_path)

    assert aggregate["trace_gate_pass_rate"] == 0.5
    assert aggregate["completion_rate"] == 1.0
    candidate_dir = tmp_path / "runs" / "run-agg" / "candidates" / "baseline"
    scores = json.loads((candidate_dir / "scores.json").read_text())
    assert scores["avg_tokens"] == 2000.0
    assert len(json.loads((candidate_dir / "results.json").read_text())) == 2


@pytest.mark.asyncio
async def test_run_scenario_with_fake_runner_and_store(tmp_path, monkeypatch):
    class _Store:
        async def query(self, *, thread_id=None, limit=100):
            return [
                {
                    "action": "memory_recall",
                    "threadId": thread_id,
                    "success": True,
                    "metadata": {"route": "fusion"},
                },
                {
                    "action": "tool_result",
                    "threadId": thread_id,
                    "toolName": "memory_search",
                    "success": True,
                },
            ]

    monkeypatch.setattr(
        scenario_runner,
        "_registered_tool_names",
        lambda: {"memory_search"},
    )
    monkeypatch.setattr("agent.audit.store.get_audit_store", lambda: _Store())

    async def _fake_score(thread_id, *, eval_id=None):
        return {"thread_id": thread_id, "eval_id": eval_id, "completed": True}

    monkeypatch.setattr(scenario_runner, "score_session", _fake_score)

    async def _fake_runner(**kwargs):
        assert kwargs["consent_allow_session_tools"] == ()
        assert kwargs["run_id"] == "run-1"
        assert kwargs["scenario_id"] == "memory-1"
        return [
            sse(TextStartPacket()),
            sse(TextDeltaPacket(delta="ok")),
            sse(FinishPacket()),
        ]

    scenario = scenario_runner.Scenario.from_mapping(
        {
            "id": "memory-1",
            "turns": [{"user": "remember x"}, {"user": "recall x"}],
            "category": "memory",
            "expected_trace": {
                "required_tools": ["memory_search"],
                "required_memory_routes": ["fusion"],
                "expected_memory": True,
            },
        }
    )
    assert scenario.expectations.required_memory_routes == ("fusion",)

    result = await scenario_runner.run_scenario(
        scenario,
        run_id="run-1",
        candidate_id="baseline",
        runner=_fake_runner,
        data_dir=tmp_path,
    )

    assert result.trace_verdict.passed is True
    assert result.turns == 2
    assert result.transcript[-1]["content"] == "ok"
    assert result.artifact_dir


@pytest.mark.asyncio
async def test_run_scenario_uses_sse_finish_as_completion_signal(tmp_path, monkeypatch):
    class _Store:
        async def query(self, *, thread_id=None, limit=100):
            return [{"action": "llm_response", "threadId": thread_id, "success": True}]

    monkeypatch.setattr("agent.audit.store.get_audit_store", lambda: _Store())

    async def _fake_score(thread_id, *, eval_id=None):
        return {
            "thread_id": thread_id,
            "eval_id": eval_id,
            "completed": False,
            "tool_success_rate": 1.0,
            "tool_calls": 0,
            "turn_efficiency": 1.0,
            "memory_utilization": False,
            "cost_estimate_usd": 0.0,
            "fitness_score": 0.5,
        }

    monkeypatch.setattr(scenario_runner, "score_session", _fake_score)

    async def _fake_runner(**kwargs):
        return [sse(TextStartPacket()), sse(FinishPacket())]

    scenario = scenario_runner.Scenario.from_mapping(
        {"id": "finish-1", "turns": [{"user": "hi"}], "category": "smoke"}
    )

    result = await scenario_runner.run_scenario(
        scenario,
        run_id="run-finish",
        runner=_fake_runner,
        data_dir=tmp_path,
    )

    assert result.score["completed"] is True
    assert result.score["completion_source"] == "sse_finish"
    assert result.score["fitness_score"] > 0.5


@pytest.mark.asyncio
async def test_run_scenario_file_can_use_service_runner(monkeypatch, tmp_path):
    scenario_file = tmp_path / "scenarios.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenarios": [
                    {
                        "id": "svc",
                        "turns": [{"user": "hello"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def _fake_service_runner(agent_url):
        captured["agent_url"] = agent_url

        async def _fake_runner(**kwargs):
            captured["thread_id"] = kwargs["thread_id"]
            return ['data: {"type":"text-delta","delta":"service ok"}\n\n']

        return _fake_runner

    class _Store:
        async def query(self, *, thread_id=None, limit=100):
            return [{"action": "llm_response", "threadId": thread_id, "success": True}]

    async def _fake_score(thread_id, *, eval_id=None):
        return {"thread_id": thread_id, "eval_id": eval_id, "completed": True}

    monkeypatch.setattr(scenario_runner, "service_agent_runner", _fake_service_runner)
    monkeypatch.setattr("agent.audit.store.get_audit_store", lambda: _Store())
    monkeypatch.setattr(scenario_runner, "score_session", _fake_score)

    result = await scenario_runner.run_scenario_file(
        scenario_file,
        agent_url="http://127.0.0.1:8094",
        user_id="anonymous",
        data_dir=tmp_path / "meta",
    )

    assert captured["agent_url"] == "http://127.0.0.1:8094"
    assert result["results"][0]["user_id"] == "anonymous"
    assert captured["thread_id"].startswith("mh-svc-")
    assert result["scenarios_evaluated"] == 1


@pytest.mark.asyncio
async def test_run_scenario_file_pins_default_model_for_all_scenarios(monkeypatch, tmp_path):
    scenario_file = tmp_path / "scenarios.json"
    scenario_file.write_text(
        json.dumps(
            {
                "scenarios": [
                    {"id": "s1", "turns": [{"user": "one"}]},
                    {"id": "s2", "turns": [{"user": "two"}]},
                ]
            }
        ),
        encoding="utf-8",
    )
    models: list[str] = []
    monkeypatch.delenv("AGENT_DEFAULT_MODEL", raising=False)
    monkeypatch.setenv("AGENT_DEFAULT_UTILITY_MODEL", "openrouter/pinned-model")

    async def _fake_run_scenario(scenario, **kwargs):
        models.append(kwargs["model"])
        monkeypatch.setenv("AGENT_DEFAULT_UTILITY_MODEL", "")
        return scenario_runner.ScenarioRunResult(
            run_id=kwargs["run_id"],
            candidate_id=kwargs["candidate_id"],
            scenario_id=scenario.id,
            thread_id=f"thread-{scenario.id}",
            user_id=kwargs["user_id"],
            category=scenario.category,
            turns=1,
            transcript=(),
            sse_chunks=(),
            trace_events=(),
            score={"completed": True, "fitness_score": 1.0},
            trace_verdict=scenario_runner.TraceGateVerdict(
                passed=True,
                failures=(),
                warnings=(),
                observed_actions=(),
                observed_tools=(),
                observed_skills=(),
            ),
        )

    monkeypatch.setattr(scenario_runner, "run_scenario", _fake_run_scenario)

    result = await scenario_runner.run_scenario_file(
        scenario_file,
        candidate_id="pin-model",
        data_dir=tmp_path / "meta",
    )

    assert result["scenarios_evaluated"] == 2
    assert models == ["openrouter/pinned-model", "openrouter/pinned-model"]


@pytest.mark.asyncio
async def test_default_agent_runner_can_select_simple_loop(monkeypatch):
    captured = {}

    class _Registry:
        def all(self):
            return []

    async def _fake_simple_loop(ctx, messages):
        captured["thread_id"] = ctx.thread_id
        captured["messages"] = messages
        yield sse(TextStartPacket())
        yield sse(FinishPacket())

    from agent.runners import simple as simple_module
    from agent.tools import registry as registry_module

    monkeypatch.setattr(
        registry_module.ToolRegistry,
        "load",
        classmethod(lambda cls: _Registry()),
    )
    monkeypatch.setattr(simple_module, "run_simple_agent_loop", _fake_simple_loop)

    chunks = await scenario_runner._default_agent_runner(
        thread_id="thread-simple",
        user_id="u1",
        model="test-model",
        system_prompt="",
        messages=[{"role": "user", "content": "hi"}],
        enable_tools=True,
        runner_variant="simple",
    )

    assert captured["thread_id"] == "thread-simple"
    assert captured["messages"][0]["content"] == "hi"
    assert chunks[-1] == sse(FinishPacket())


@pytest.mark.asyncio
async def test_default_agent_runner_uses_env_credential_for_simulated_user(monkeypatch):
    captured = {}

    class _Registry:
        def all(self):
            return []

    async def _fake_simple_loop(ctx, messages):
        captured["api_key"] = ctx.api_key
        captured["user_id"] = ctx.user_id
        yield sse(TextStartPacket())
        yield sse(FinishPacket())

    from agent.runners import simple as simple_module
    from agent.tools import registry as registry_module

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.delenv("META_HARNESS_ALLOW_ENV_CREDENTIALS", raising=False)
    monkeypatch.setattr(
        registry_module.ToolRegistry,
        "load",
        classmethod(lambda cls: _Registry()),
    )
    monkeypatch.setattr(simple_module, "run_simple_agent_loop", _fake_simple_loop)

    await scenario_runner._default_agent_runner(
        thread_id="thread-simple",
        user_id="meta-harness",
        model="openrouter/openrouter/auto",
        system_prompt="",
        messages=[{"role": "user", "content": "hi"}],
        enable_tools=True,
        runner_variant="simple",
    )

    assert captured == {"api_key": "test-openrouter-key", "user_id": "meta-harness"}


@pytest.mark.asyncio
async def test_default_agent_runner_can_disable_env_credential(monkeypatch):
    captured = {}

    class _Registry:
        def all(self):
            return []

    async def _fake_simple_loop(ctx, messages):
        captured["api_key"] = ctx.api_key
        yield sse(TextStartPacket())
        yield sse(FinishPacket())

    from agent.runners import simple as simple_module
    from agent.tools import registry as registry_module

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("META_HARNESS_ALLOW_ENV_CREDENTIALS", "0")
    monkeypatch.setattr(
        registry_module.ToolRegistry,
        "load",
        classmethod(lambda cls: _Registry()),
    )
    monkeypatch.setattr(simple_module, "run_simple_agent_loop", _fake_simple_loop)

    await scenario_runner._default_agent_runner(
        thread_id="thread-simple",
        user_id="meta-harness",
        model="openrouter/openrouter/auto",
        system_prompt="",
        messages=[{"role": "user", "content": "hi"}],
        enable_tools=True,
        runner_variant="simple",
    )

    assert captured["api_key"] is None


@pytest.mark.asyncio
async def test_query_trace_events_retries_until_events_arrive(monkeypatch):
    calls = {"n": 0}

    class _Store:
        async def query(self, *, thread_id=None, limit=100):
            calls["n"] += 1
            if calls["n"] == 1:
                return []
            return [{"action": "llm_response", "threadId": thread_id}]

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr("agent.audit.store.get_audit_store", lambda: _Store())
    monkeypatch.setattr(scenario_runner.asyncio, "sleep", _no_sleep)

    events = await scenario_runner._query_trace_events("thread-1")

    assert calls["n"] == 2
    assert events[0]["action"] == "llm_response"


@pytest.mark.asyncio
async def test_evaluate_single_uses_real_tool_registry(monkeypatch):
    captured = {}

    class _Tool:
        name = "memory_search"

        def definition(self):
            return {"name": self.name, "description": "", "input_schema": {}}

    class _Registry:
        def all(self):
            return [_Tool()]

    async def _fake_run_agent_loop(ctx, messages):
        captured["tools"] = [tool.name for tool in ctx.tools]
        yield sse(TextStartPacket())
        yield sse(TextDeltaPacket(delta="ok"))
        yield sse(FinishPacket())

    async def _fake_score(thread_id, *, eval_id=None):
        return {"thread_id": thread_id, "completed": True}

    class _Store:
        async def query(self, *, thread_id=None, limit=100):
            return [
                {
                    "action": "tool_result",
                    "threadId": thread_id,
                    "toolName": "memory_search",
                    "success": True,
                }
            ]

    from agent.graph import runner as runner_module
    from agent.tools import registry as registry_module

    monkeypatch.setattr(runner_module, "run_agent_loop", _fake_run_agent_loop)
    monkeypatch.setattr(
        registry_module.ToolRegistry,
        "load",
        classmethod(lambda cls: _Registry()),
    )
    monkeypatch.setattr("meta_harness.scorer.score_session", _fake_score)
    monkeypatch.setattr("agent.audit.store.get_audit_store", lambda: _Store())
    monkeypatch.setattr(
        scenario_runner,
        "_registered_tool_names",
        lambda: {"memory_search"},
    )

    result = await evaluator.evaluate_single(
        {
            "id": "q-tool",
            "message": "search memory",
            "expected_tools": ["memory_search"],
        },
        eval_id="eval-1",
        runner_variant="langgraph",
    )

    assert captured["tools"] == ["memory_search"]
    assert result["trace_gates"]["passed"] is True
