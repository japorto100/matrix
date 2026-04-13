"""Consolidation Sub-Graph — Trace2Skill Batch-Analyse (exec-10 Phase 6.1).

LangGraph Graph mit 3 Nodes:
  1. Error-Analyst: Analysiert Failure-Trajectories → Error-Patterns
  2. Success-Analyst: Analysiert Success-Trajectories → Success-Patterns
  3. Consolidator: Merged beide → 1 konsolidierter Skill

Parallel: Error + Success laufen gleichzeitig.
Sequential: Consolidator wartet auf beide.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agent.llm_helper import extract_json, llm_call
from agent.skills.loader import SKILLS_BASE

logger = logging.getLogger(__name__)


class ConsolidationState(TypedDict):
    """State fuer den Consolidation Sub-Graph."""

    trajectories: list[dict[str, Any]]
    user_id: str
    error_patterns: list[str]
    success_patterns: list[str]
    consolidated_skill: dict[str, Any]
    skill_path: str


ERROR_PROMPT = """You are an Error Analyst. Analyze ONLY the FAILED trajectories below.
Identify COMMON failure patterns (not one-off issues).

## Failed Trajectories
{trajectories}

## Output (JSON)
{{"patterns": ["pattern1: description", "pattern2: description"], "root_causes": ["cause1", "cause2"]}}

Only include patterns that appear in 2+ trajectories."""

SUCCESS_PROMPT = """You are a Success Analyst. Analyze ONLY the SUCCESSFUL trajectories below.
Identify what these successful interactions did RIGHT.

## Successful Trajectories
{trajectories}

## Output (JSON)
{{"patterns": ["best_practice1: description", "best_practice2: description"], "key_strategies": ["strategy1", "strategy2"]}}

Only include patterns that appear in 2+ trajectories."""

MERGE_PROMPT = """You are a Skill Consolidator. Merge the error patterns and success patterns
into ONE actionable skill document.

## Error Patterns (what goes wrong)
{error_patterns}

## Success Patterns (what works well)
{success_patterns}

## Output (JSON)
{{
    "name": "skill-name-kebab-case",
    "description": "One-line description",
    "category": "general|trading|risk|research",
    "content": "Markdown with ## Workflow\\n## Best Practices\\n## Anti-Patterns sections",
    "confidence": 0.0-1.0
}}

The skill should teach the agent to AVOID the error patterns and FOLLOW the success patterns."""


async def _error_analyst(state: ConsolidationState) -> dict[str, Any]:
    """Analysiert nur Failure-Trajectories."""
    failures = [t for t in state["trajectories"] if not t.get("success")]
    if not failures:
        return {"error_patterns": []}

    formatted = _format_trajectories(failures)
    text = await llm_call(ERROR_PROMPT.format(trajectories=formatted), max_tokens=1024)
    try:
        data = extract_json(text)
        return {
            "error_patterns": data.get("patterns", []) + data.get("root_causes", [])
        }
    except Exception:
        return {"error_patterns": []}


async def _success_analyst(state: ConsolidationState) -> dict[str, Any]:
    """Analysiert nur Success-Trajectories."""
    successes = [t for t in state["trajectories"] if t.get("success")]
    if not successes:
        return {"success_patterns": []}

    formatted = _format_trajectories(successes)
    text = await llm_call(
        SUCCESS_PROMPT.format(trajectories=formatted), max_tokens=1024
    )
    try:
        data = extract_json(text)
        return {
            "success_patterns": data.get("patterns", [])
            + data.get("key_strategies", [])
        }
    except Exception:
        return {"success_patterns": []}


async def _consolidator(state: ConsolidationState) -> dict[str, Any]:
    """Merged Error + Success Patterns zu einem Skill."""
    error_patterns = state.get("error_patterns", [])
    success_patterns = state.get("success_patterns", [])

    if not error_patterns and not success_patterns:
        return {"consolidated_skill": {}, "skill_path": ""}

    text = await llm_call(
        MERGE_PROMPT.format(
            error_patterns="\n".join(f"- {p}" for p in error_patterns),
            success_patterns="\n".join(f"- {p}" for p in success_patterns),
        ),
        max_tokens=2048,
    )

    try:
        skill_data = extract_json(text)
    except Exception:
        return {"consolidated_skill": {}, "skill_path": ""}

    confidence = skill_data.get("confidence", 0)
    if confidence < 0.5:
        logger.info(
            "Consolidated skill confidence too low (%.2f), skipping", confidence
        )
        return {"consolidated_skill": skill_data, "skill_path": ""}

    # Skill speichern
    user_id = state["user_id"]
    name = f"consolidated-{skill_data.get('name', 'unknown')}"
    skill_dir = SKILLS_BASE / "personal" / user_id / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = (
        f"---\n"
        f"name: {name}\n"
        f"description: {skill_data.get('description', '')}\n"
        f"category: {skill_data.get('category', 'general')}\n"
        f"consolidated: true\n"
        f"source_trajectories: {len(state['trajectories'])}\n"
        f"confidence: {confidence}\n"
        f"generated: {datetime.now().isoformat()}\n"
        f"user_id: {user_id}\n"
        f"---\n\n"
        f"{skill_data.get('content', '')}\n"
    )
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # References Subdirectory
    if error_patterns or success_patterns:
        ref_dir = skill_dir / "references"
        ref_dir.mkdir(exist_ok=True)
        ref_content = "# Analysis Patterns\n\n"
        if error_patterns:
            ref_content += (
                "## Error Patterns\n"
                + "\n".join(f"- {p}" for p in error_patterns)
                + "\n\n"
            )
        if success_patterns:
            ref_content += (
                "## Success Patterns\n"
                + "\n".join(f"- {p}" for p in success_patterns)
                + "\n"
            )
        (ref_dir / "patterns.md").write_text(ref_content, encoding="utf-8")

    logger.info(
        "Consolidated %d trajectories → skill '%s' (confidence=%.2f)",
        len(state["trajectories"]),
        name,
        confidence,
    )

    return {"consolidated_skill": skill_data, "skill_path": str(skill_dir / "SKILL.md")}


def _format_trajectories(trajectories: list[dict]) -> str:
    """Formatiert Trajectories fuer LLM-Prompt."""
    parts = []
    for i, t in enumerate(trajectories[:10]):
        status = "SUCCESS" if t.get("success") else "FAILURE"
        reason = t.get("failure_reason", "")
        msgs = t.get("messages", [])
        user_msg = next(
            (m.get("content", "")[:200] for m in msgs if m.get("role") == "user"), ""
        )
        parts.append(
            f"### Trajectory {i + 1} ({status})\n"
            f"Request: {user_msg}\n"
            f"Tools: {t.get('tool_calls_count', 0)}\n"
            f"{'Failure: ' + reason if reason else ''}"
        )
    return "\n\n".join(parts)


def create_consolidation_graph() -> Any:
    """Erstellt den Consolidation Sub-Graph.

    Flow: START → [Error-Analyst, Success-Analyst] (parallel) → Consolidator → END
    """
    graph = StateGraph(ConsolidationState)

    graph.add_node("error_analyst", _error_analyst)
    graph.add_node("success_analyst", _success_analyst)
    graph.add_node("consolidator", _consolidator)

    # Parallel: Error + Success
    graph.add_edge(START, "error_analyst")
    graph.add_edge(START, "success_analyst")

    # Beide → Consolidator
    graph.add_edge("error_analyst", "consolidator")
    graph.add_edge("success_analyst", "consolidator")

    # Consolidator → END
    graph.add_edge("consolidator", END)

    return graph.compile(checkpointer=MemorySaver())
