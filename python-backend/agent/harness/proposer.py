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
4. SKILL STRATEGY — which skills were found/refined/used, coverage scores, trigger quality

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

    # 5. Skill strategy analysis from audit events
    skill_events = [
        ev
        for ev in all_events
        if (ev.get("action") or "").startswith("skill_")
    ]
    skill_summary = {
        "total_skill_events": len(skill_events),
        "by_action": {},
        "recent_coverage_scores": [],
        "recent_skill_ids": [],
    }
    for ev in skill_events[:50]:
        action = ev.get("action", "")
        skill_summary["by_action"][action] = (
            skill_summary["by_action"].get(action, 0) + 1
        )
        meta = ev.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:  # noqa: BLE001
                meta = {}
        if meta.get("coverage_score") is not None:
            skill_summary["recent_coverage_scores"].append(
                meta["coverage_score"]
            )
        if meta.get("skill_ids"):
            for sid in meta["skill_ids"][:5]:
                if sid not in skill_summary["recent_skill_ids"]:
                    skill_summary["recent_skill_ids"].append(sid)

    # 6. Trigger quality aggregation (best-effort)
    trigger_quality = None
    try:
        from agent.skills.trigger_quality import compute_trigger_quality

        tq = compute_trigger_quality(days=30, min_n=3)
        if tq:
            trigger_quality = [s.as_dict() for s in tq]
    except Exception:  # noqa: BLE001
        pass

    return {
        "config": json.loads(config.to_json()),
        "scores": scores,
        "traces": trace_summaries,
        "skill_strategy": skill_summary,
        "trigger_quality": trigger_quality,
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

    _save_proposal(proposal, context.get("config"))

    return proposal


def _proposal_prompt_override(proposal: dict[str, Any]) -> str:
    """Convert system-prompt proposals into a candidate prompt overlay."""
    changes = proposal.get("proposed_changes") or []
    prompt_changes = []
    for change in changes:
        if not isinstance(change, dict):
            continue
        target = str(change.get("target", "")).lower()
        if "system_prompt" not in target and "prompt" not in target:
            continue
        text = str(change.get("change") or "").strip()
        rationale = str(change.get("rationale") or "").strip()
        if not text:
            continue
        prompt_changes.append(
            {
                "target": change.get("target", "system_prompt"),
                "change": text,
                "rationale": rationale,
            }
        )
    if not prompt_changes:
        return ""
    return (
        "Harness candidate prompt overlay generated from proposer output:\n"
        + json.dumps(prompt_changes, indent=2, default=str)
    )


def _save_proposal(proposal: dict[str, Any], config_snapshot: dict | None = None) -> None:
    """Save proposal to DB (agent.component_configs) AND optionally filesystem.

    Primary: DB (exec-18 Migration 018). Versioned, queryable, Pareto-ready.
    Secondary: Filesystem (Meta-Harness pattern, kept as option).

    Env HARNESS_SAVE_MODE: 'db' (default) | 'filesystem' | 'both'
    """
    import os

    save_mode = os.environ.get("HARNESS_SAVE_MODE", "both").strip().lower()

    # ── DB path (primary) ────────────────────────────────────────────
    if save_mode in ("db", "both"):
        try:
            _save_proposal_db(proposal, config_snapshot)
        except Exception as e:  # noqa: BLE001
            logger.warning("DB proposal save failed, falling back to filesystem: %s", e)
            save_mode = "filesystem"  # degrade gracefully

    # ── Filesystem path (secondary / fallback) ───────────────────────
    if save_mode in ("filesystem", "both"):
        _save_proposal_fs(proposal)


def _save_proposal_db(proposal: dict[str, Any], config_snapshot: dict | None) -> None:
    """Persist proposal as component_config row in agent.component_configs."""
    import os
    import time

    import psycopg

    db_url = os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )
    now_ms = int(time.time() * 1000)
    component_id = "harness.default"

    with psycopg.connect(db_url, autocommit=True) as conn:
        # Ensure component exists
        conn.execute(
            """
            INSERT INTO agent.components
                (component_id, component_type, name, created_at)
            VALUES (%s, 'agent', 'Default Harness', %s)
            ON CONFLICT (component_id) DO NOTHING
            """,
            (component_id, now_ms),
        )

        # Next version number
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM agent.component_configs WHERE component_id = %s",
            (component_id,),
        ).fetchone()
        next_version = (row[0] if row else 0) + 1

        # Insert config
        conn.execute(
            """
            INSERT INTO agent.component_configs
                (component_id, version, label, stage, config, notes,
                 proposer_model, created_at)
            VALUES (%s, %s, %s, 'draft', %s::jsonb, %s, %s, %s)
            """,
            (
                component_id,
                next_version,
                f"v{next_version:03d}",
                json.dumps(config_snapshot or {}, default=str),
                json.dumps(proposal.get("analysis", ""), default=str)[:2000],
                proposal.get("model", ""),
                now_ms,
            ),
        )

        # Update component current_version
        conn.execute(
            "UPDATE agent.components SET current_version = %s, updated_at = %s WHERE component_id = %s",
            (next_version, now_ms, component_id),
        )

    logger.info("Harness proposal saved to DB: %s v%03d", component_id, next_version)


def _save_proposal_fs(proposal: dict[str, Any]) -> None:
    """Save proposal to data/harness/candidates/ directory (Meta-Harness filesystem pattern)."""
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

    logger.info("Harness proposal saved to filesystem: %s", version_dir)


async def propose_loop(
    *,
    iterations: int = 5,
    candidates_per_iter: int = 1,
    model: str = "",
    last_n_sessions: int = 10,
    eval_max_queries: int = 1,
    eval_concurrency: int = 2,
) -> list[dict[str, Any]]:
    """Run multiple proposer iterations (Meta-Harness: ~20 iterations, ~60 candidates).

    Each iteration: propose -> evaluate candidate overlay on the real search-set
    evaluator when ``eval_max_queries`` is positive.
    """
    all_proposals = []
    for i in range(iterations):
        for _c in range(candidates_per_iter):
            logger.info("Proposer iteration %d/%d", i + 1, iterations)
            proposal = await propose(model=model, last_n_sessions=last_n_sessions)
            proposal["loop_iteration"] = i + 1
            if eval_max_queries > 0:
                from agent.harness.evaluator import evaluate_search_set

                eval_id = f"harness-loop-{proposal.get('timestamp', i + 1)}"
                evaluation = await evaluate_search_set(
                    system_prompt_override=_proposal_prompt_override(proposal),
                    max_queries=eval_max_queries,
                    eval_id=eval_id,
                    concurrency=eval_concurrency,
                )
                proposal["evaluation"] = evaluation
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
