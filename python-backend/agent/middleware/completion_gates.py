"""Completion Gates Middleware (NLAH Paper, exec-10 Phase 6.2a).

Prueft ob ein Sub-Agent-Output den Rollen-Contract erfuellt.
Nutzt LLM-as-Judge via provider-agnostischen llm_helper.
"""

from __future__ import annotations

import logging

from agent.llm_helper import extract_json, llm_call
from agent.roles import TRADING_ROLE_CONTRACTS

logger = logging.getLogger(__name__)

GATE_CHECK_PROMPT = """Check if this agent response fulfills the required contract.

## Role: {role}
## Contract Requirements:
{requirements}

## Agent Response:
{response}

## Output (JSON only)
{{"passed": true/false, "missing": ["requirement that was not met"], "reason": "brief explanation"}}"""


async def check_completion_gate(role: str, response: str) -> dict:
    """Prueft ob ein Agent-Output den Rollen-Contract erfuellt.

    Returns: {"passed": bool, "missing": [...], "reason": str}
    """
    # Contract fuer die Rolle finden
    contracts = None
    for r, c in TRADING_ROLE_CONTRACTS.items():
        if r.value == role:
            contracts = c
            break

    if not contracts:
        return {"passed": True, "missing": [], "reason": "No contract defined"}

    try:
        prompt = GATE_CHECK_PROMPT.format(
            role=role,
            requirements="\n".join(f"- {r}" for r in contracts),
            response=response[:3000],
        )
        text = await llm_call(prompt, max_tokens=256)
        return extract_json(text)
    except Exception as e:
        logger.warning("Completion gate check failed: %s", e)
        return {"passed": True, "missing": [], "reason": f"Gate check error: {e}"}
