"""Runtime loop guards shared by graph and graphless agent runners."""

from __future__ import annotations

import os
from typing import Any

TOOL_FAILURE_GUARD_FLAG = "tool_retry_guard_stopped"


def max_tool_failures_per_tool() -> int:
    """Return the max repeated failed results per tool before stopping a loop."""

    try:
        value = int(os.environ.get("AGENT_MAX_TOOL_FAILURES_PER_TOOL", "2"))
    except ValueError:
        value = 2
    return max(value, 1)


def repeated_tool_failure_guard(
    tool_results: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
    *,
    max_failures: int | None = None,
) -> dict[str, Any] | None:
    """Return stop metadata when one tool failed repeatedly in this turn."""

    limit = max_tool_failures_per_tool() if max_failures is None else max(max_failures, 1)
    failures: dict[str, int] = {}
    for result in tool_results or []:
        if not isinstance(result, dict) or not result.get("error"):
            continue
        tool_name = str(result.get("tool_name") or "<unknown>")
        failures[tool_name] = failures.get(tool_name, 0) + 1
        if failures[tool_name] >= limit:
            return {
                "stop": True,
                "reason": "repeated_tool_failure",
                "tool_name": tool_name,
                "failure_count": failures[tool_name],
                "max_failures": limit,
                "degradation_flag": TOOL_FAILURE_GUARD_FLAG,
                "message": (
                    "Stopped after repeated tool failures for "
                    f"{tool_name}. The last tool result did not produce a "
                    "safe successful output."
                ),
            }
    return None
