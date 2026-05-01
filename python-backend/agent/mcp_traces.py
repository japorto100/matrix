"""MCP Trace Server — exponiert Agent Execution Traces als MCP Tools (exec-17 Phase 4).

Provides 6 tools for trace inspection + harness analysis:
  - trace_list: List recent agent sessions with summary stats
  - trace_detail: Full trace of a specific session (all turns, tools, memory)
  - trace_search: Free-text search across prompts/responses/tool outputs
  - trace_compare: Compare two sessions side-by-side
  - trace_score: Derived scores for a session (efficiency, tool usage, cost)
  - harness_config: Current agent configuration (system prompts, tools, memory)
  - harness_run_scenarios: Feature 016 scenario runner with trace gates

Data source: Audit Store (JSONL or PostgreSQL) — same data that Phase 2 spans generate.

Normal: Mounted in Agent Service under /mcp-traces (agent/app.py, Port 8094)
Standalone: uv run python -m agent.mcp_traces (Port 8096, for isolated inspection)

Meta-Harness (arxiv:2603.28052v1): The proposer reads 82 files/iteration —
41% source code, 40% execution traces, 6% scores. These MCP tools serve as
the equivalent interface for Claude Code to inspect traces and suggest improvements.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

trace_mcp = FastMCP(
    "agent-traces",
    instructions=(
        "Agent Trace MCP Server — inspect agent execution history. "
        "Use trace_list to find sessions, trace_detail for full traces, "
        "trace_search to find patterns across sessions, and harness_config "
        "to see the current agent setup."
    ),
    # Effective path after app.mount("/mcp-traces", ...) is /mcp-traces/.
    streamable_http_path="/",
)


def _get_store():
    from agent.audit.store import get_audit_store

    return get_audit_store()


def _aggregate_sessions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group audit events by thread_id into session summaries."""
    by_thread: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        tid = ev.get("threadId") or ev.get("thread_id") or ""
        if tid:
            by_thread[tid].append(ev)

    sessions = []
    for thread_id, evs in by_thread.items():
        llm_responses = [e for e in evs if e.get("action") == "llm_response"]
        tool_results = [e for e in evs if e.get("action") == "tool_result"]
        total_tokens = sum(
            (e.get("metadata") or {}).get("token_usage", 0) for e in llm_responses
        )
        total_duration = sum(e.get("duration_ms", 0) for e in llm_responses)

        sessions.append(
            {
                "thread_id": thread_id,
                "events": len(evs),
                "llm_calls": len(llm_responses),
                "tool_calls": len(tool_results),
                "total_tokens": total_tokens,
                "total_duration_ms": round(total_duration, 1),
                "tools_used": sorted(
                    {e.get("toolName") or e.get("tool_name", "") for e in tool_results}
                    - {""}
                ),
                "first_event": evs[0].get("timestamp", ""),
                "last_event": evs[-1].get("timestamp", ""),
            }
        )

    sessions.sort(key=lambda s: s["last_event"], reverse=True)
    return sessions


@trace_mcp.tool(
    name="trace_list",
    description="List recent agent sessions with summary stats (turns, tokens, tools, duration).",
)
async def trace_list(last_n: int = 20) -> str:
    """List recent agent sessions."""
    store = _get_store()
    events = await store.query(limit=last_n * 20)
    sessions = _aggregate_sessions(events)
    return json.dumps(sessions[:last_n], indent=2, default=str)


@trace_mcp.tool(
    name="trace_detail",
    description="Get full trace for a session — all LLM calls, tool executions, memory operations, with prompts and responses.",
)
async def trace_detail(thread_id: str) -> str:
    """Get complete trace for a specific session."""
    store = _get_store()
    events = await store.query(thread_id=thread_id, limit=500)
    if not events:
        return json.dumps({"error": f"No events found for thread_id: {thread_id}"})

    trace = {
        "thread_id": thread_id,
        "event_count": len(events),
        "timeline": [],
    }

    for ev in events:
        entry: dict[str, Any] = {
            "timestamp": ev.get("timestamp"),
            "action": ev.get("action"),
            "success": ev.get("success"),
        }
        if ev.get("duration_ms"):
            entry["duration_ms"] = ev["duration_ms"]
        if ev.get("toolName") or ev.get("tool_name"):
            entry["tool_name"] = ev.get("toolName") or ev.get("tool_name")
        if ev.get("input"):
            entry["input"] = ev["input"]
        if ev.get("output"):
            entry["output"] = ev["output"]
        if ev.get("metadata"):
            entry["metadata"] = ev["metadata"]
        if ev.get("iteration") is not None:
            entry["iteration"] = ev["iteration"]

        trace["timeline"].append(entry)

    return json.dumps(trace, indent=2, default=str)


@trace_mcp.tool(
    name="trace_search",
    description="Search across traces for a keyword in prompts, responses, tool names, or outputs.",
)
async def trace_search(query: str, last_n: int = 50) -> str:
    """Free-text search across audit events."""
    store = _get_store()
    events = await store.query(limit=last_n * 20)

    query_lower = query.lower()
    matches = []

    for ev in events:
        searchable = json.dumps(ev, default=str).lower()
        if query_lower in searchable:
            matches.append(
                {
                    "thread_id": ev.get("threadId") or ev.get("thread_id", ""),
                    "timestamp": ev.get("timestamp"),
                    "action": ev.get("action"),
                    "tool_name": ev.get("toolName") or ev.get("tool_name"),
                    "preview": searchable[:300],
                }
            )
            if len(matches) >= last_n:
                break

    return json.dumps(
        {"query": query, "matches": len(matches), "results": matches},
        indent=2,
        default=str,
    )


@trace_mcp.tool(
    name="trace_compare",
    description="Compare two sessions side-by-side — differences in turns, tools, tokens, duration.",
)
async def trace_compare(session_a: str, session_b: str) -> str:
    """Compare two agent sessions."""
    store = _get_store()
    events_a = await store.query(thread_id=session_a, limit=500)
    events_b = await store.query(thread_id=session_b, limit=500)

    def _summarize(evs: list[dict]) -> dict:
        llm = [e for e in evs if e.get("action") == "llm_response"]
        tools = [e for e in evs if e.get("action") == "tool_result"]
        return {
            "events": len(evs),
            "llm_calls": len(llm),
            "tool_calls": len(tools),
            "total_tokens": sum(
                (e.get("metadata") or {}).get("token_usage", 0) for e in llm
            ),
            "total_duration_ms": round(sum(e.get("duration_ms", 0) for e in llm), 1),
            "tools_used": sorted(
                {e.get("toolName") or e.get("tool_name", "") for e in tools} - {""}
            ),
            "success_rate": (
                sum(1 for e in tools if e.get("success")) / len(tools) if tools else 1.0
            ),
        }

    return json.dumps(
        {
            "session_a": {"thread_id": session_a, **_summarize(events_a)},
            "session_b": {"thread_id": session_b, **_summarize(events_b)},
        },
        indent=2,
        default=str,
    )


@trace_mcp.tool(
    name="trace_score",
    description="Compute derived quality scores for a session — efficiency, tool usage, cost estimate.",
)
async def trace_score(thread_id: str) -> str:
    """Score a session based on audit data (Meta-Harness: scores are 6% of proposer reads)."""
    store = _get_store()
    events = await store.query(thread_id=thread_id, limit=500)
    if not events:
        return json.dumps({"error": f"No events found for thread_id: {thread_id}"})

    llm_responses = [e for e in events if e.get("action") == "llm_response"]
    tool_results = [e for e in events if e.get("action") == "tool_result"]
    consent_decisions = [e for e in events if e.get("action") == "consent_decision"]

    total_tokens = sum(
        (e.get("metadata") or {}).get("token_usage", 0) for e in llm_responses
    )
    total_duration_ms = sum(e.get("duration_ms", 0) for e in llm_responses)
    tool_successes = sum(1 for t in tool_results if t.get("success"))
    tool_failures = len(tool_results) - tool_successes
    denied_tools = sum(
        1
        for c in consent_decisions
        if (c.get("metadata") or {}).get("decision") in ("hard_deny", "deny")
    )

    scores = {
        "thread_id": thread_id,
        "turns": len(llm_responses),
        "turn_efficiency": round(1.0 / max(len(llm_responses), 1), 3),
        "total_tokens": total_tokens,
        "total_duration_ms": round(total_duration_ms, 1),
        "tool_success_rate": round(tool_successes / max(len(tool_results), 1), 3),
        "tool_failure_count": tool_failures,
        "tools_denied": denied_tools,
        "completed": any((e.get("metadata") or {}).get("done") for e in llm_responses),
    }
    return json.dumps(scores, indent=2, default=str)


@trace_mcp.tool(
    name="harness_config",
    description="Get current agent harness configuration — system prompts, tool registry, memory config per role.",
)
async def harness_config(role: str = "") -> str:
    """Return the current agent harness configuration (Meta-Harness: source code equivalent)."""
    config: dict[str, Any] = {}

    # System prompts per role
    try:
        from agent.roles import TRADING_ROLE_MEMORY, TRADING_ROLE_PROMPTS

        if role:
            for r, prompt in TRADING_ROLE_PROMPTS.items():
                if r.value == role:
                    config["system_prompt"] = prompt[:2000]
                    break
            for r, mem_config in TRADING_ROLE_MEMORY.items():
                if r.value == role:
                    config["memory_config"] = mem_config
                    break
        else:
            config["roles"] = {
                r.value: {"prompt_preview": p[:200], "prompt_length": len(p)}
                for r, p in TRADING_ROLE_PROMPTS.items()
            }
            config["memory_config"] = {
                r.value: c for r, c in TRADING_ROLE_MEMORY.items()
            }
    except Exception:
        config["roles"] = {"error": "Could not load roles"}

    # Tool registry
    try:
        from agent.tools.registry import ToolRegistry

        registry = ToolRegistry.load()
        config["tools"] = [
            {
                "name": t.definition()["name"],
                "description": t.definition().get("description", "")[:100],
            }
            for t in registry.all()
        ]
    except Exception:
        config["tools"] = {"error": "Could not load tool registry"}

    # Consent config
    try:
        from agent.consent.config import get_consent_config

        cc = get_consent_config()
        config["consent"] = {
            "max_iterations": cc.rate_limits.get_max_iterations(),
            "tool_timeout_sec": cc.rate_limits.get_tool_timeout(),
        }
    except Exception:
        pass

    # Graph structure
    config["graph_flow"] = (
        "START → memory_recall → llm_call → "
        "[approval_gate → tool_execute → increment]* → memory_retain → END"
    )

    return json.dumps(config, indent=2, default=str)


@trace_mcp.tool(
    name="harness_propose",
    description="Run the Meta-Harness proposer. External LLM calls are disabled by default; enable META_HARNESS_ENABLE_EXTERNAL_LLM=true to use API proposer mode.",
)
async def harness_propose(last_n_sessions: int = 10, model: str = "") -> str:
    """Run the harness proposer guard or explicit external-LLM proposer."""
    from meta_harness.proposer import propose

    result = await propose(model=model, last_n_sessions=last_n_sessions)
    return json.dumps(result, indent=2, default=str)


@trace_mcp.tool(
    name="harness_history",
    description="List all harness proposal candidates with their scores and timestamps.",
)
async def harness_history() -> str:
    """List previous harness proposals from data/harness/candidates/."""
    from meta_harness.proposer import HARNESS_DATA_DIR

    candidates_dir = HARNESS_DATA_DIR / "candidates"
    if not candidates_dir.exists():
        return json.dumps({"candidates": [], "total": 0})

    candidates = []
    for version_dir in sorted(candidates_dir.glob("v*")):
        entry: dict[str, Any] = {"version": version_dir.name}
        proposal_path = version_dir / "proposal.json"
        if proposal_path.exists():
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            entry["timestamp"] = proposal.get("timestamp", "")
            entry["model"] = proposal.get("model", "")
            entry["sessions_analyzed"] = proposal.get("sessions_analyzed", 0)
            entry["changes_proposed"] = len(proposal.get("proposed_changes", []))
        candidates.append(entry)

    return json.dumps({"candidates": candidates, "total": len(candidates)}, indent=2)


@trace_mcp.tool(
    name="harness_evaluate",
    description="Run the agent against the search set and collect scores. Use to evaluate the current harness or a proposed variant.",
)
async def harness_evaluate(
    max_queries: int = 5,
    concurrency: int = 4,
    use_cache: bool = True,
    split: str = "search",
    allow_holdout: bool = False,
) -> str:
    """Evaluate current harness against search set queries."""
    from meta_harness.evaluator import evaluate_search_set

    result = await evaluate_search_set(
        max_queries=max_queries,
        concurrency=concurrency,
        use_cache=use_cache,
        split=split,
        allow_holdout=allow_holdout,
    )
    return json.dumps(result, indent=2, default=str)


@trace_mcp.tool(
    name="harness_run_scenarios",
    description="Run Feature 016 Meta-Harness scenario JSON with trace gates and write raw candidate artifacts.",
)
async def harness_run_scenarios(
    path: str,
    max_scenarios: int = 0,
    scenario_ids: list[str] | None = None,
    candidate_id: str = "baseline",
    user_id: str = "anonymous",
    model: str = "",
    agent_url: str = "",
) -> str:
    """Run multi-turn scenario fixtures through in-process or live-service agent."""
    from meta_harness.scenario_runner import run_scenario_file

    result = await run_scenario_file(
        Path(path),
        max_scenarios=max_scenarios,
        scenario_ids=tuple(scenario_ids or ()),
        candidate_id=candidate_id,
        user_id=user_id,
        model=model,
        agent_url=agent_url,
    )
    return json.dumps(result, indent=2, default=str)


@trace_mcp.tool(
    name="harness_pareto",
    description="Show the Pareto frontier of harness candidates — the set of non-dominated configurations across all scoring dimensions.",
)
async def harness_pareto() -> str:
    """Get the Pareto frontier summary."""
    from meta_harness.pareto import get_frontier_summary

    return json.dumps(get_frontier_summary(), indent=2, default=str)


@trace_mcp.tool(
    name="harness_decide_candidate",
    description="Record a keep/discard/defer decision for a Meta-Harness candidate with rationale and metrics.",
)
async def harness_decide_candidate(
    run_id: str,
    candidate_id: str,
    decision: str,
    rationale: str,
    metrics_json: str = "{}",
    follow_up: str = "",
) -> str:
    """Record candidate decision for future proposer inspection."""
    from meta_harness.decisions import record_candidate_decision

    metrics = json.loads(metrics_json or "{}")
    if not isinstance(metrics, dict):
        raise ValueError("metrics_json must decode to an object")
    entry = record_candidate_decision(
        run_id=run_id,
        candidate_id=candidate_id,
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale,
        metrics=metrics,
        follow_up=follow_up,
    )
    return json.dumps(entry.as_dict(), indent=2, default=str)


@trace_mcp.tool(
    name="harness_loop",
    description="Run multiple proposer iterations. External LLM proposer is disabled by default; Codex should act as proposer unless explicitly enabled.",
)
async def harness_loop(
    iterations: int = 3,
    model: str = "",
    eval_max_queries: int = 1,
) -> str:
    """Run the proposer loop for N iterations."""
    from meta_harness.proposer import propose_loop

    results = await propose_loop(
        iterations=iterations,
        candidates_per_iter=1,
        model=model,
        eval_max_queries=eval_max_queries,
    )
    return json.dumps(
        {"iterations": len(results), "proposals": results}, indent=2, default=str
    )


def create_trace_mcp_server() -> FastMCP:
    """Factory for trace MCP server (used by app.py mount)."""
    return trace_mcp


# Standalone mode: uv run python -m agent.mcp_traces
if __name__ == "__main__":
    trace_mcp.run(transport="streamable-http", host="127.0.0.1", port=8096)
