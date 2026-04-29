"""HTTP Client zum bestehenden Agent-Service.

Der Agent-Service-Endpoint /api/v1/agent/chat gibt SSE zurück (text/event-stream).
Wir sammeln alle TextDeltaPackets und geben den vollen Text zurück.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from bridge.config import Config

logger = logging.getLogger(__name__)

# SSE packet types from agent/streaming.py. Keep the legacy underscore aliases
# because older scheduler/A2A helpers still emit them in tests and fixtures.
_TEXT_DELTA_TYPES = {"text_delta", "text-delta"}
_FINISH = "finish"
_ERROR = "error"


class AgentClient:
    """HTTP Client zum bestehenden Agent-Service (port 8094 / 11500)."""

    def __init__(self, config: Config) -> None:
        self.base_url = config.agent_service_url.rstrip("/")
        self.timeout = config.agent_timeout_sec
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0, read=self.timeout, write=30.0, pool=5.0
            ),
        )

    async def send_message(
        self,
        message: str,
        room_id: str,
        sender: str,
        thread_id: str | None = None,
        model: str | None = None,
    ) -> str:
        """
        Sendet eine Nachricht an den Agent-Service und gibt die vollständige Antwort zurück.

        Der Endpoint /api/v1/agent/chat streamt SSE (Vercel AI Data Stream Protocol):
          data: {"type":"thread_id","threadId":"..."}
          data: {"type":"text_start","id":"t1"}
          data: {"type":"text_delta","id":"t1","text":"Hallo"}
          data: {"type":"text_delta","id":"t1","text":" Welt"}
          data: {"type":"text_end","id":"t1"}
          data: {"type":"finish","usage":{...}}

        Wir sammeln alle text_delta Pakete und konkatenieren sie.
        """
        payload: dict[str, Any] = {
            "message": message,
            "threadId": thread_id or room_id,
            "context": f"matrix_room:{room_id} sender:{sender}",
        }
        if model:
            payload["model"] = model

        full_text = ""
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/api/v1/agent/chat",
                json=payload,
                headers={"x-auth-user": sender} if sender else None,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        packet = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.debug("SSE non-JSON line: %s", raw[:80])
                        continue

                    ptype = packet.get("type", "")
                    if ptype in _TEXT_DELTA_TYPES:
                        full_text += packet.get("delta") or packet.get("text", "")
                    elif ptype == _ERROR:
                        logger.error(
                            "Agent error packet: %s",
                            packet.get("errorText") or packet.get("error"),
                        )
                    elif ptype == _FINISH:
                        logger.debug(
                            "Agent finished, usage=%s", packet.get("usage", {})
                        )
                        break

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Agent HTTP error %d: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return "(Agent nicht erreichbar — HTTP-Fehler)"
        except httpx.TimeoutException:
            logger.error("Agent request timed out after %ss", self.timeout)
            return "(Agent-Timeout — Anfrage dauerte zu lange)"
        except Exception as exc:
            logger.exception("Agent request failed: %s", exc)
            return f"(Agent-Fehler: {exc!s})"

        return full_text.strip() or "(keine Antwort)"

    async def health_check(self) -> bool:
        """Prüft ob der Agent-Service erreichbar ist."""
        try:
            resp = await self._client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
