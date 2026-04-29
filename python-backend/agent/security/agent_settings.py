"""Per-user agent settings resolver.

Contract table (planned/optional): agent.user_agent_settings
columns: user_id text, agent_id text, settings jsonb.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

MemoryScope = Literal["none", "personal", "personal_kb", "world", "all"]
VALID_MEMORY_SCOPES: frozenset[str] = frozenset(
    {"none", "personal", "personal_kb", "world", "all"}
)


@dataclass(frozen=True)
class UserAgentSettings:
    user_id: str
    agent_id: str = "default"
    prompt: str = ""
    memory_scope: MemoryScope = "all"
    enabled_skills: tuple[str, ...] = ()
    disabled_skills: tuple[str, ...] = ()
    tool_allowlist: tuple[str, ...] = ()

    def prompt_block(self) -> str:
        lines = [
            "## User Agent Settings",
            f"- agent_id: {self.agent_id}",
            f"- memory_scope: {self.memory_scope}",
        ]
        if self.prompt:
            lines.append(f"- prompt_override: {self.prompt}")
        if self.enabled_skills:
            lines.append(f"- enabled_skills: {', '.join(self.enabled_skills)}")
        if self.disabled_skills:
            lines.append(f"- disabled_skills: {', '.join(self.disabled_skills)}")
        if self.tool_allowlist:
            lines.append(f"- tool_allowlist: {', '.join(self.tool_allowlist)}")
        return "\n".join(lines)


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw = value.split(",")
    elif isinstance(value, list | tuple | set):
        raw = list(value)
    else:
        return ()
    return tuple(str(item).strip() for item in raw if str(item).strip())


def normalize_user_agent_settings(
    raw: dict[str, Any] | None,
    *,
    user_id: str,
    agent_id: str = "default",
) -> UserAgentSettings:
    data = dict(raw or {})
    memory_scope = str(data.get("memory_scope") or data.get("memoryScope") or "all")
    memory_scope = memory_scope.strip().lower()
    if memory_scope not in VALID_MEMORY_SCOPES:
        memory_scope = "all"
    return UserAgentSettings(
        user_id=user_id,
        agent_id=str(data.get("agent_id") or data.get("agentId") or agent_id or "default"),
        prompt=str(data.get("prompt") or data.get("system_prompt") or "").strip(),
        memory_scope=memory_scope,  # type: ignore[arg-type]
        enabled_skills=_tuple_of_strings(
            data.get("enabled_skills") or data.get("enabledSkills")
        ),
        disabled_skills=_tuple_of_strings(
            data.get("disabled_skills") or data.get("disabledSkills")
        ),
        tool_allowlist=_tuple_of_strings(
            data.get("tool_allowlist") or data.get("toolAllowlist")
        ),
    )


async def get_user_agent_settings(
    user_id: str,
    *,
    agent_id: str = "default",
) -> UserAgentSettings | None:
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url or not user_id:
        return None

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (
                await conn.execute(
                    """
                    SELECT settings
                    FROM agent.user_agent_settings
                    WHERE user_id = %s AND agent_id = %s
                    """,
                    (user_id, agent_id),
                )
            ).fetchone()
    except Exception as exc:  # noqa: BLE001
        logger.debug("get_user_agent_settings failed for %s/%s: %s", user_id, agent_id, exc)
        return None

    if not row or not isinstance(row[0], dict):
        return None
    return normalize_user_agent_settings(row[0], user_id=user_id, agent_id=agent_id)
