"""Matrix Bot Client via matrix-nio.

Verbindet sich mit dem Tuwunel Homeserver, empfängt Nachrichten und leitet
sie an den bestehenden Agent-Service weiter.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LoginResponse,
    MatrixRoom,
    RoomMessageText,
    SyncError,
)

from agent_bridge.agent_client import AgentClient
from agent_bridge.config import Config

logger = logging.getLogger(__name__)


class MatrixBotClient:
    """Async Matrix Bot Client (kein E2EE — Go Appservice übernimmt Crypto, Option C)."""

    def __init__(self, config: Config, agent_client: AgentClient) -> None:
        self.config = config
        self.agent_client = agent_client
        self._client: AsyncClient | None = None
        self._stopped = False

    async def start(self) -> None:
        """Initialisiert den Client und startet die Sync-Schleife."""
        Path(self.config.store_path).mkdir(parents=True, exist_ok=True)

        nio_config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
        )

        self._client = AsyncClient(
            homeserver=self.config.homeserver_url,
            user=self.config.bot_user_id,
            config=nio_config,
        )

        # Event Handler registrieren
        self._client.add_event_callback(self._on_message, RoomMessageText)  # pyright: ignore[reportArgumentType]
        self._client.add_event_callback(self._on_invite, InviteMemberEvent)  # pyright: ignore[reportArgumentType]

        # Login
        await self._login()

        # Display Name setzen (einmalig beim Start)
        await self._client.set_displayname("Trading Agent")
        logger.info("Display name set")

        logger.info(
            "Matrix bot started user_id=%s store=%s",
            self.config.bot_user_id,
            self.config.store_path,
        )

        # Sync-Schleife
        while not self._stopped:
            resp = await self._client.sync(timeout=30_000, full_state=True)
            if isinstance(resp, SyncError):
                logger.error("Sync error: %s", resp.message)
                await asyncio.sleep(5)

    async def _login(self) -> None:
        """Login via gespeichertem Access Token oder Passwort."""
        assert self._client is not None  # noqa: S101

        if self.config.bot_access_token:
            self._client.access_token = self.config.bot_access_token
            self._client.user_id = self.config.bot_user_id
            logger.info("Using existing access token")
            return

        resp = await self._client.login(
            password=self.config.bot_password,
            device_name=self.config.device_name,
        )
        if isinstance(resp, LoginResponse):
            logger.info(
                "Logged in successfully access_token_prefix=%s", resp.access_token[:12]
            )
            # Token ausgeben damit User es in .env eintragen kann
            print("\n✅ Login erfolgreich!")  # noqa: T201
            print(f"   MATRIX_BOT_ACCESS_TOKEN={resp.access_token}")  # noqa: T201
            print("   → In .env eintragen für schnellere Starts\n")  # noqa: T201
        else:
            raise RuntimeError(f"Matrix login failed: {resp}")

    async def _on_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        """Eingehende Text-Nachricht verarbeiten."""
        assert self._client is not None  # noqa: S101

        # Eigene Nachrichten ignorieren
        if event.sender == self.config.bot_user_id:
            return

        # Sender-Homeserver prüfen (falls Whitelist konfiguriert)
        if self.config.allowed_homeservers:
            _, sender_hs = (
                event.sender.rsplit(":", 1) if ":" in event.sender else ("", "")
            )
            if sender_hs not in self.config.allowed_homeservers:
                logger.debug(
                    "Ignoring message from non-allowed homeserver: %s", event.sender
                )
                return

        body = event.body

        # In Gruppen-Chats: nur reagieren wenn Bot erwähnt wird
        if self.config.mention_only_in_groups and len(room.users) > 2:
            localpart = self.config.bot_localpart
            if (
                f"@{localpart}" not in body
                and self.config.bot_user_id not in body
                and not body.lower().startswith(("agent,", "hey agent", "bot,"))
            ):
                return

        logger.info("Message from %s in %s: %s", event.sender, room.room_id, body[:80])

        # Tipp-Indikator senden
        await self._client.room_typing(room.room_id, typing_state=True, timeout=30_000)

        try:
            reply_text = await self.agent_client.send_message(
                message=body,
                room_id=room.room_id,
                sender=event.sender,
                thread_id=room.room_id,
            )

            # Antwort in Matrix-Raum senden (als Reply auf die Nachricht)
            await self._client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": reply_text,
                    "m.relates_to": {
                        "m.in_reply_to": {"event_id": event.event_id},
                    },
                },
            )

        except Exception as exc:
            logger.exception("Failed to get agent reply: %s", exc)
            await self._client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "⚠️ Fehler beim Verarbeiten der Anfrage.",
                },
            )
        finally:
            await self._client.room_typing(room.room_id, typing_state=False)

    async def _on_invite(self, room: MatrixRoom, event: InviteMemberEvent) -> None:
        """Bot nimmt Einladungen automatisch an."""
        assert self._client is not None  # noqa: S101

        if event.state_key == self.config.bot_user_id:
            logger.info("Joining room %s (invited by %s)", room.room_id, event.sender)
            await self._client.join(room.room_id)

    async def stop(self) -> None:
        self._stopped = True
        if self._client:
            await self._client.close()
        logger.info("Matrix bot stopped")
