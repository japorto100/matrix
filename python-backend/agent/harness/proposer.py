"""Harness Proposer — LLM-based harness optimization (exec-17 Phase 5).

Reads execution traces + scores + current harness config, then asks an LLM
to propose improvements. Works with any LLM via LiteLLM.

Meta-Harness paper (arxiv:2603.28052v1):
  "The main advantage of Meta-Harness is not just search over code, but search
   with selective access to prior diagnostic experience."

The proposer reads:
  - Current harness config (system prompts, tools, memory settings)
  - Recent execution traces (from audit store)
  - Session scores (from scorer.py)
And generates:
  - Analysis of failure patterns
  - Proposed changes to the harness
  - A new HarnessConfig variant

Usage:
  Standalone:  uv run python -m agent.harness.proposer
  Via MCP:     harness_propose() tool in mcp_traces.py
  Via API LLM: any model through LiteLLM
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HARNESS_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "harness"

PROPOSER_SYSTEM_PROMPT = """\
You are a Harness Optimization Agent analyzing an AI trading agent system.

Your job is to analyze execution traces and suggest improvements to the agent's
configuration (system prompts, tool usage patterns, memory settings).

You will receive:
1. CURRENT HARNESS CONFIG — the agent's system prompts, available tools, memory settings
2. RECENT TRACES — what happened in recent agent sessions (LLM calls, tool uses, memory)
3. SCORES — quality metrics for recent sessions

Analyze the data and respond with a JSON object:
{
  "analysis": "Your analysis of patterns, failures, and inefficiencies",
  "proposed_changes": [
    {
      "target": "system_prompt.fundamentals_analyst" | "tool_config" | "memory_config",
      "change": "Description of what to change",
      "rationale": "Why this should improve performance",
      "priority": "high" | "medium" | "low"
    }
  ],
  "expected_improvement": "What you expect to improve and by how much"
}

Focus on actionable, specific changes. Don't suggest vague improvements.
Reference specific trace data to justify your proposals.
"""


async def _gather_context(last_n_sessions: int = 10) -> dict[str, Any]:
    """Gather all context the proposer needs: config + traces + scores."""
    from agent.audit.store import get_audit_store
    from agent.harness.config import capture_current_config
    from agent.harness.scorer import score_session

    # 1. Current harness config
    config = capture_current_config()

    # 2. Recent traces
    store = get_audit_store()
    all_events = await store.query(limit=last_n_sessions * 20)

    # Group by thread_id
    from collections import defaultdict

    by_thread: dict[str, list[dict]] = defaultdict(list)
    for ev in all_events:
        tid = ev.get("threadId") or ev.get("thread_id", "")
        if tid:
            by_thread[tid].append(ev)

    thread_ids = sorted(
        by_thread.keys(),
        key=lambda t: by_thread[t][-1].get("timestamp", ""),
        reverse=True,
    )[:last_n_sessions]

    # 3. Scores per session
    scores = []
    for tid in thread_ids:
        s = await score_session(tid)
        scores.append(s)

    # 4. Trace summaries (truncated for LLM context)
    trace_summaries = []
    for tid in thread_ids:
        evs = by_thread[tid]
        summary = {
            "thread_id": tid,
            "events": len(evs),
            "timeline": [],
        }
        for ev in evs[:30]:  # Max 30 events per session for context
            entry = {
                "action": ev.get("action"),
                "success": ev.get("success"),
            }
            if ev.get("duration_ms"):
                entry["duration_ms"] = ev["duration_ms"]
            if ev.get("toolName") or ev.get("tool_name"):
                entry["tool"] = ev.get("toolName") or ev.get("tool_name")
            if ev.get("metadata"):
                entry["meta"] = ev["metadata"]
            # Include truncated input/output for LLM analysis
            if ev.get("input"):
                inp = ev["input"]
                entry["input_preview"] = (
                    str(inp)[:300]
                    if isinstance(inp, str)
                    else json.dumps(inp, default=str)[:300]
                )
            if ev.get("output"):
                out = ev["output"]
                entry["output_preview"] = (
                    str(out)[:300]
                    if isinstance(out, str)
                    else json.dumps(out, default=str)[:300]
                )
            summary["timeline"].append(entry)
        trace_summaries.append(summary)

    return {
        "config": json.loads(config.to_json()),
        "scores": scores,
        "traces": trace_summaries,
    }


async def propose(
    model: str = "",
    last_n_sessions: int = 10,
) -> dict[str, Any]:
    """Run the proposer: gather context → ask LLM → return proposal.

    Uses LiteLLM so any configured model works (Anthropic, OpenAI, Gemini, etc.).
    """
    import os

    from agent.llm_client import get_litellm_client

    if not model:
        model = os.environ.get(
            "AGENT_DEFAULT_UTILITY_MODEL", "claude-haiku-4-5-20251001"
        )

    # Gather all context
    context = await _gather_context(last_n_sessions)

    # Build the prompt
    user_prompt = f"""## Current Harness Config
{json.dumps(context["config"], indent=2, default=str)[:5000]}

## Recent Session Scores ({len(context["scores"])} sessions)
{json.dumps(context["scores"], indent=2, default=str)[:3000]}

## Recent Execution Traces
{json.dumps(context["traces"], indent=2, default=str)[:8000]}

Analyze the above data. What patterns do you see? What specific changes to the
harness (system prompts, tool config, memory settings) would improve agent performance?
"""

    client = get_litellm_client()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PROPOSER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    raw_response = response.choices[0].message.content or ""

    # Try to parse JSON from the response
    proposal: dict[str, Any] = {"raw_response": raw_response}
    try:
        # Find JSON block in response
        import re

        json_match = re.search(r"\{[\s\S]*\}", raw_response)
        if json_match:
            proposal = json.loads(json_match.group())
            proposal["raw_response"] = raw_response
    except (json.JSONDecodeError, AttributeError):
        pass

    # Save proposal to filesystem (Meta-Harness pattern: candidates directory)
    proposal["timestamp"] = datetime.now(UTC).isoformat()
    proposal["model"] = model
    proposal["sessions_analyzed"] = len(context["scores"])

    _save_proposal(proposal)

    return proposal


def _save_proposal(proposal: dict[str, Any]) -> None:
    """Save proposal to data/harness/candidates/ directory."""
    candidates_dir = HARNESS_DATA_DIR / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # Find next version number
    existing = sorted(candidates_dir.glob("v*"))
    next_num = len(existing) + 1
    version_dir = candidates_dir / f"v{next_num:03d}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # Save proposal
    (version_dir / "proposal.json").write_text(
        json.dumps(proposal, indent=2, default=str), encoding="utf-8"
    )

    # Save current config snapshot alongside
    from agent.harness.config import capture_current_config

    config = capture_current_config()
    config.version = f"v{next_num:03d}"
    config.save(version_dir / "config.json")

    logger.info("Harness proposal saved: %s", version_dir)


async def propose_loop(
    *,
    iterations: int = 5,
    candidates_per_iter: int = 1,
    model: str = "",
    last_n_sessions: int = 10,
) -> list[dict[str, Any]]:
    """Run multiple proposer iterations (Meta-Harness: ~20 iterations, ~60 candidates).

    Each iteration: propose → (future: evaluate → score → update frontier).
    Currently propose-only; evaluation integration is future work.
    """
    all_proposals = []
    for i in range(iterations):
        for _c in range(candidates_per_iter):
            logger.info("Proposer iteration %d/%d", i + 1, iterations)
            proposal = await propose(model=model, last_n_sessions=last_n_sessions)
            proposal["loop_iteration"] = i + 1
            all_proposals.append(proposal)

    logger.info(
        "Proposer loop complete: %d iterations, %d candidates",
        iterations,
        len(all_proposals),
    )
    return all_proposals


# Standalone mode: uv run python -m agent.harness.proposer [--iterations N]
if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Harness Proposer (Meta-Harness)")
    parser.add_argument("--model", default="", help="LLM model to use (via LiteLLM)")
    parser.add_argument(
        "--sessions", type=int, default=10, help="Number of recent sessions to analyze"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of proposer iterations (loop mode)",
    )
    parser.add_argument(
        "--candidates", type=int, default=1, help="Candidates per iteration"
    )
    args = parser.parse_args()

    async def main():
        if args.iterations > 1:
            results = await propose_loop(
                iterations=args.iterations,
                candidates_per_iter=args.candidates,
                model=args.model,
                last_n_sessions=args.sessions,
            )
            print(json.dumps(results, indent=2, default=str))
        else:
            result = await propose(model=args.model, last_n_sessions=args.sessions)
            print(json.dumps(result, indent=2, default=str))

    asyncio.run(main())
