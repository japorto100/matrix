"""NATS Handler — subscribed auf matrix.message.inbound, ruft Agent auf, published Reply.

Ersetzt den matrix-nio Sync-Loop. Python Bridge wird reiner NATS-Consumer.
Go Appservice ist einziger Matrix-Endpunkt (E2BE-Pattern).
"""

from __future__ import annotations

import json
import logging

import nats
from nats.aio.client import Client as NATSClient

from bridge.agent_client import AgentClient
from bridge.config import Config

logger = logging.getLogger(__name__)

SUBJECT_INBOUND = "matrix.message.inbound"
SUBJECT_REPLY = "matrix.message.reply"


class NATSHandler:
    """NATS Consumer: empfängt Matrix-Messages von Go, leitet an Agent weiter, published Reply."""

    def __init__(self, config: Config, agent_client: AgentClient) -> None:
        self._config = config
        self._agent = agent_client
        self._nc: NATSClient | None = None

    async def connect(self) -> None:
        url = self._config.nats_url
        if not url:
            raise RuntimeError("NATS_URL nicht gesetzt — Bridge kann nicht starten")

        self._nc = await nats.connect(
            url,
            max_reconnect_attempts=10,
            reconnect_time_wait=2,
            disconnected_cb=self._on_disconnect,
            reconnected_cb=self._on_reconnect,
            error_cb=self._on_error,
        )
        logger.info("NATS connected: %s", url)

        await self._nc.subscribe(SUBJECT_INBOUND, cb=self._on_inbound)
        logger.info("Subscribed to %s", SUBJECT_INBOUND)

    async def close(self) -> None:
        if self._nc and not self._nc.is_closed:
            await self._nc.drain()
            logger.info("NATS connection drained")

    @property
    def is_connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    async def _on_inbound(self, msg: nats.aio.msg.Msg) -> None:
        """Handler für eingehende Matrix-Messages von Go Appservice."""
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from NATS: %s", msg.data[:200])
            return

        room_id = data.get("room_id", "")
        sender = data.get("sender", "")
        body = data.get("body", "")
        thread_id = data.get("thread_id")

        if not body:
            return

        logger.info(
            "NATS inbound: room=%s sender=%s body_len=%d",
            room_id, sender, len(body),
        )

        # Agent aufrufen (HTTP SSE, wie bisher)
        reply_text = await self._agent.send_message(
            message=body,
            room_id=room_id,
            sender=sender,
            thread_id=thread_id,
        )

        # Reply an Go Appservice zurück senden
        reply = {
            "room_id": room_id,
            "agent_user_id": self._config.agent_user_id,
            "text": reply_text,
            "is_streaming": False,
        }

        if self._nc and not self._nc.is_closed:
            await self._nc.publish(SUBJECT_REPLY, json.dumps(reply).encode())
            logger.info("NATS reply published: room=%s text_len=%d", room_id, len(reply_text))

    async def _on_disconnect(self) -> None:
        logger.warning("NATS disconnected")

    async def _on_reconnect(self) -> None:
        logger.info("NATS reconnected")

    async def _on_error(self, e: Exception) -> None:
        logger.error("NATS error: %s", e)
