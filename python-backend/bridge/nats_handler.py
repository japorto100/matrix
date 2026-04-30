"""NATS Handler — subscribed auf matrix.message.inbound, ruft Agent auf, published Reply.

Ersetzt den matrix-nio Sync-Loop. Python Bridge wird reiner NATS-Consumer.
Go Appservice ist einziger Matrix-Endpunkt (E2BE-Pattern).
"""

from __future__ import annotations

import json
import logging
import re
from collections import OrderedDict

import nats
from nats.aio.client import Client as NATSClient

from bridge.agent_client import AgentClient
from bridge.config import Config

logger = logging.getLogger(__name__)

SUBJECT_INBOUND = "matrix.message.inbound"
SUBJECT_INBOUND_ROUTED = "matrix.message.inbound.>"
SUBJECT_INBOUND_AGENT_PREFIX = "matrix.message.inbound.agent."
SUBJECT_REPLY = "matrix.message.reply"
_AGENT_NAME_RE = re.compile(r"[^a-z0-9_-]+")
MAX_RECENT_EVENT_IDS = 2048


def sanitize_agent_name(agent_name: str) -> str:
    """Normalize agent names before constructing Matrix user IDs."""
    value = (agent_name or "").strip().lower()
    value = value.removeprefix("@").removeprefix("agent-")
    value = value.split(":", 1)[0]
    value = _AGENT_NAME_RE.sub("-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-_")
    return (value[:64].strip("-_")) or "default"


class NATSHandler:
    """NATS Consumer: empfängt Matrix-Messages von Go, leitet an Agent weiter, published Reply."""

    def __init__(self, config: Config, agent_client: AgentClient) -> None:
        self._config = config
        self._agent = agent_client
        self._nc: NATSClient | None = None
        self._allowed_agents = tuple(
            sanitize_agent_name(agent) for agent in config.nats_allowed_agents
        )
        self._recent_event_ids: OrderedDict[str, None] = OrderedDict()

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

        for subject in self._subscription_subjects():
            await self._nc.subscribe(subject, cb=self._on_inbound)
        logger.info(
            "Subscribed to NATS inbound subjects: %s",
            self._subscription_subjects(),
        )

    async def close(self) -> None:
        if self._nc and not self._nc.is_closed:
            await self._nc.drain()
            logger.info("NATS connection drained")

    @property
    def is_connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    async def _on_inbound(self, msg: nats.aio.msg.Msg) -> None:
        """Handler für eingehende Matrix-Messages von Go Appservice."""
        if not self._is_subject_allowed(str(getattr(msg, "subject", "") or "")):
            logger.warning(
                "Rejected unauthorized NATS subject: %s",
                getattr(msg, "subject", ""),
            )
            return

        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from NATS: %s", msg.data[:200])
            return

        room_id = data.get("room_id", "")
        sender = data.get("sender", "")
        body = data.get("body", "")
        event_id = data.get("event_id", "")
        thread_id = data.get("thread_id")
        target_agent = data.get("target_agent", "")
        is_thread_reply = bool(data.get("is_thread_reply", False))

        if not self._is_target_allowed(target_agent):
            logger.warning("Rejected unauthorized target_agent: %s", target_agent)
            return

        if self._is_agent_sender(sender):
            logger.info("Ignored Matrix echo from agent sender: %s", sender)
            return

        if event_id and not self._remember_event_id(str(event_id)):
            logger.info("Ignored replayed Matrix event: %s", event_id)
            return

        if is_thread_reply and not thread_id:
            logger.warning(
                "Rejected malformed Matrix thread reply without thread_id: event=%s",
                event_id or "(missing)",
            )
            return

        if not body:
            return

        logger.info(
            "NATS inbound: room=%s sender=%s target_agent=%s body_len=%d",
            room_id,
            sender,
            target_agent or "(default)",
            len(body),
        )

        # exec-16: User-Settings fuer Matrix Mention (sender → model + api_key)
        model: str | None = None
        try:
            from agent.security.credentials import get_user_default_model

            model = await get_user_default_model(sender)
        except Exception:
            pass  # DB nicht verfuegbar → kein User-Model, Agent nutzt Fallback

        # Agent aufrufen (HTTP SSE, wie bisher)
        reply_text = await self._agent.send_message(
            message=body,
            room_id=room_id,
            sender=sender,
            thread_id=thread_id,
            model=model,
            matrix_event_id=event_id,
            target_agent=target_agent,
            is_thread_reply=is_thread_reply,
        )

        # Reply-UserID: dynamisch pro target_agent aus dem incoming-payload.
        # Fallback auf config-default wenn kein target_agent parsed wurde (z.B. DM ohne mention).
        reply_agent_user_id = self._resolve_reply_user_id(target_agent)

        # Reply an Go Appservice zurück senden
        reply = {
            "room_id": room_id,
            "agent_user_id": reply_agent_user_id,
            "text": reply_text,
            "is_streaming": False,
        }
        if thread_id:
            reply["thread_root_id"] = thread_id

        if self._nc and not self._nc.is_closed:
            await self._nc.publish(SUBJECT_REPLY, json.dumps(reply).encode())
            logger.info(
                "NATS reply published: room=%s text_len=%d", room_id, len(reply_text)
            )

    def _resolve_reply_user_id(self, target_agent: str) -> str:
        """Baut die reply-Matrix-User-ID aus dem target_agent aus dem NATS-payload.

        Go-Appservice parst `@agent-<name>` aus dem message-body via `extractAgentName()` und
        setzt `target_agent="<name>"` im InboundMessage. Wir mappen das zurück auf die volle
        Matrix-User-ID via Appservice-Namespace-Pattern `@agent-<name>:<server>`.

        Fallback: config-default (`AGENT_USER_ID` env-var) wenn target_agent leer — deckt
        DMs ohne expliziten mention ab.

        Server-Name wird aus der config-default abgeleitet um Format-Drift zu vermeiden.
        """
        if not target_agent:
            return self._config.agent_user_id

        # Server-name aus default user_id extrahieren: "@agent-trading:matrix.local" → "matrix.local"
        default = self._config.agent_user_id
        server_name = default.split(":", 1)[1] if ":" in default else "matrix.local"
        return f"@agent-{sanitize_agent_name(target_agent)}:{server_name}"

    def _subscription_subjects(self) -> list[str]:
        """Subjects this bridge instance is allowed to read.

        Empty allowlist preserves the historical single-bridge behavior:
        consume global and all routed subjects. A non-empty allowlist makes the
        instance agent-scoped; it reads only explicit agent subjects and does
        not subscribe to the global catch-all.
        """
        if not self._allowed_agents:
            return [SUBJECT_INBOUND, SUBJECT_INBOUND_ROUTED]
        return [
            SUBJECT_INBOUND_AGENT_PREFIX + agent for agent in self._allowed_agents
        ]

    def _is_subject_allowed(self, subject: str) -> bool:
        if not self._allowed_agents:
            return True
        prefix = SUBJECT_INBOUND_AGENT_PREFIX
        if not subject.startswith(prefix):
            return False
        return sanitize_agent_name(subject.removeprefix(prefix)) in self._allowed_agents

    def _is_target_allowed(self, target_agent: str) -> bool:
        if not self._allowed_agents:
            return True
        return sanitize_agent_name(target_agent) in self._allowed_agents

    def _remember_event_id(self, event_id: str) -> bool:
        """Return False when a reconnect/replay delivers an already seen event."""
        event_id = event_id.strip()
        if not event_id:
            return True
        if event_id in self._recent_event_ids:
            self._recent_event_ids.move_to_end(event_id)
            return False
        self._recent_event_ids[event_id] = None
        while len(self._recent_event_ids) > MAX_RECENT_EVENT_IDS:
            self._recent_event_ids.popitem(last=False)
        return True

    def _is_agent_sender(self, sender: str) -> bool:
        """Defense-in-depth echo guard for events already filtered by Go."""
        if not sender.startswith("@") or ":" not in sender:
            return False
        sender_local, sender_server = sender[1:].split(":", 1)
        default = self._config.agent_user_id
        default_server = default.split(":", 1)[1] if ":" in default else "matrix.local"
        default_local = default.split(":", 1)[0].lstrip("@")
        prefix = default_local.split("-", 1)[0] + "-" if "-" in default_local else "agent-"
        return sender_server == default_server and sender_local.startswith(prefix)

    async def _on_disconnect(self) -> None:
        logger.warning("NATS disconnected")

    async def _on_reconnect(self) -> None:
        logger.info("NATS reconnected")

    async def _on_error(self, e: Exception) -> None:
        logger.error("NATS error: %s", e)
