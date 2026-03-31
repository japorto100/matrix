"""A2A Client — Inter-Agent Delegation via HTTP+JSON (exec-10 Phase 4).

Vereinfachte A2A Implementation:
- send_message() → sendet Task an Remote-Agent
- poll_task() → fragt Task-Status ab
- HTTP+JSON Transport (kein gRPC)

Basiert auf Google A2A Protocol, vereinfacht fuer lokale Multi-Agent Szenarien.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class A2ATask:
    """Ergebnis einer Agent-to-Agent Delegation."""

    task_id: str
    state: str  # created, running, completed, failed
    result: str | None = None
    error: str | None = None


class A2AClient:
    """HTTP Client fuer Agent-to-Agent Communication."""

    def __init__(self, timeout: float = 120.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send_message(
        self,
        agent_url: str,
        message: str,
        context: str | None = None,
    ) -> A2ATask:
        """Sendet eine Nachricht an einen Remote-Agent.

        Args:
            agent_url: Base-URL des Ziel-Agents (z.B. http://localhost:8094)
            message: User-Message
            context: Optionaler Kontext (z.B. vorherige Analyse-Ergebnisse)

        Returns:
            A2ATask mit task_id und initialem State.
        """
        task_id = str(uuid.uuid4())

        payload: dict[str, Any] = {
            "message": message,
            "threadId": f"a2a-{task_id}",
        }
        if context:
            payload["context"] = context

        try:
            resp = await self._client.post(
                f"{agent_url.rstrip('/')}/api/v1/agent/chat",
                json=payload,
            )

            if resp.status_code == 200:
                # Streaming response — collect full text
                text = ""
                for line in resp.text.split("\n"):
                    if line.startswith("data:"):
                        try:
                            packet = json.loads(line[5:].strip())
                            if packet.get("type") in ("text_delta", "text-delta"):
                                text += packet.get("text", "")
                        except json.JSONDecodeError:
                            continue

                return A2ATask(task_id=task_id, state="completed", result=text.strip())
            else:
                return A2ATask(task_id=task_id, state="failed", error=f"HTTP {resp.status_code}")

        except Exception as e:
            return A2ATask(task_id=task_id, state="failed", error=str(e))

    async def close(self) -> None:
        await self._client.aclose()
