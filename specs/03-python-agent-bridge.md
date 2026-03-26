# Python Agent Bridge — matrix-nio

## Konzept

Die Python Agent Bridge ist ein eigenständiger FastAPI-Service (analog zum bestehenden `agent-service`),
der als **Matrix-Bot** fungiert. Er:
- Verbindet sich mit dem Tuwunel Homeserver via matrix-nio
- Empfängt Nachrichten aus Matrix-Räumen
- Leitet diese an den bestehenden **Agent-Service** (Port 8094) weiter
- Schreibt Antworten zurück in den Matrix-Raum

**Wichtig:** Dieser Service nutzt einen einfachen Bot-Account (`@trading-agent:matrix.local`),
keinen Appservice-Namespace. Der Go-Appservice ist für virtuelle Multi-Agent-IDs zuständig.
Beide Ansätze können parallel existieren.

- matrix-nio: https://github.com/matrix-nio/matrix-nio
- Letzte Aktivität: Feb 2026

---

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
namespaces = true
include = ["agent_bridge*"]

[project]
name = "matrix-agent-bridge"
version = "0.1.0"
description = "Matrix Bot Bridge — verbindet Matrix-Räume mit dem Agent-Service"
requires-python = ">=3.11"
dependencies = [
    # ── HTTP Framework ──────────────────────────────────────────────────────
    "fastapi==0.116.1",
    "uvicorn==0.35.0",
    "httpx==0.28.1",
    "python-dotenv==1.0.1",

    # ── Matrix Client ───────────────────────────────────────────────────────
    # matrix-nio: async, sans-I/O, E2EE support, aktiv Feb 2026
    "matrix-nio[e2e]>=0.26.0",

    # ── Message Queue (optional, Alternative zu direktem HTTP) ─────────────
    "nats-py>=2.7.0",

    # ── Cache / State ───────────────────────────────────────────────────────
    "redis>=5.0.0",

    # ── OpenTelemetry (opt-in) ──────────────────────────────────────────────
    "opentelemetry-sdk>=1.29.0",
    "opentelemetry-instrumentation-fastapi>=0.50b0",
]

[tool.ruff]
exclude = [".venv", ".venv/**"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

---

## Verzeichnisstruktur

```
python-agent-bridge/
├── pyproject.toml
├── .env
├── agent_bridge/
│   ├── __init__.py
│   ├── app.py            # FastAPI App (Health, Status endpoints)
│   ├── config.py         # Config via env vars
│   ├── matrix_client.py  # matrix-nio Client + Event Loop
│   ├── agent_client.py   # HTTP Client → bestehender Agent-Service (Port 8094)
│   └── models.py         # Pydantic Models
├── tests/
│   └── test_matrix_client.py
└── scripts/
    └── register_bot.py   # Einmalig: Bot-Account registrieren
```

---

## agent_bridge/config.py

```python
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Matrix
    homeserver_url: str
    bot_user_id: str
    bot_password: str
    bot_access_token: str | None  # nach erstem Login gespeichert
    device_name: str
    store_path: str               # E2EE Key Store

    # Agent Service (bestehend)
    agent_service_url: str        # http://localhost:8094
    agent_timeout_sec: float

    # NATS (optional)
    nats_url: str | None

    # Server
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            homeserver_url=os.getenv("MATRIX_HOMESERVER_URL", "http://localhost:8448"),
            bot_user_id=os.getenv("MATRIX_BOT_USER_ID", "@trading-agent:matrix.local"),
            bot_password=os.environ["MATRIX_BOT_PASSWORD"],
            bot_access_token=os.getenv("MATRIX_BOT_ACCESS_TOKEN"),
            device_name=os.getenv("MATRIX_DEVICE_NAME", "TradingAgent-Bridge"),
            store_path=os.getenv("MATRIX_STORE_PATH", "./data/matrix_store"),
            agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://localhost:8094"),
            agent_timeout_sec=float(os.getenv("AGENT_TIMEOUT_SEC", "120")),
            nats_url=os.getenv("NATS_URL"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8097")),
        )
```

---

## agent_bridge/matrix_client.py

```python
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from nio import (
    AsyncClient,
    AsyncClientConfig,
    LoginResponse,
    MatrixRoom,
    RoomMessageText,
    InviteMemberEvent,
    SyncError,
)

from agent_bridge.config import Config
from agent_bridge.agent_client import AgentClient

logger = logging.getLogger(__name__)


class MatrixBotClient:
    def __init__(self, config: Config, agent_client: AgentClient) -> None:
        self.config = config
        self.agent_client = agent_client
        self._client: AsyncClient | None = None

    async def start(self) -> None:
        """Initialisiert den Matrix Client und startet die Sync-Schleife."""
        Path(self.config.store_path).mkdir(parents=True, exist_ok=True)

        # E2EE-fähige Config
        nio_config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
            encryption_enabled=True,   # E2EE aktivieren
        )

        self._client = AsyncClient(
            homeserver=self.config.homeserver_url,
            user=self.config.bot_user_id,
            store_path=self.config.store_path,
            config=nio_config,
        )

        # Event Handler registrieren
        self._client.add_event_callback(self._on_message, RoomMessageText)
        self._client.add_event_callback(self._on_invite, InviteMemberEvent)

        # Login
        await self._login()

        # Trust eigene Geräte (für E2EE)
        if self._client.should_upload_keys:
            await self._client.keys_upload()

        logger.info("Matrix bot started, user_id=%s", self.config.bot_user_id)

        # Sync-Schleife (never_timeout = läuft bis Cancellation)
        await self._client.sync_forever(timeout=30_000, full_state=True)

    async def _login(self) -> None:
        """Login via Passwort oder gespeichertem Access Token."""
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
            logger.info("Logged in, access_token=%s...", resp.access_token[:10])
            # Token für spätere Starts speichern (in .env oder DB)
        else:
            raise RuntimeError(f"Login failed: {resp}")

    async def _on_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        """Eingehende Textnachricht im Raum."""
        # Eigene Nachrichten ignorieren
        if event.sender == self.config.bot_user_id:
            return

        logger.info(
            "Message in %s from %s: %s",
            room.room_id,
            event.sender,
            event.body[:100],
        )

        # Tipp-Indikator senden
        await self._client.room_typing(room.room_id, typing_state=True, timeout=30_000)

        try:
            # An Agent-Service weiterleiten
            reply = await self.agent_client.send_message(
                message=event.body,
                room_id=room.room_id,
                sender=event.sender,
                thread_id=room.room_id,  # Raum-ID als Thread-ID
            )

            # Antwort in Matrix-Raum schreiben
            await self._client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": reply,
                    # Reply-Referenz auf ursprüngliche Nachricht
                    "m.relates_to": {
                        "m.in_reply_to": {"event_id": event.event_id}
                    },
                },
            )
        except Exception as exc:
            logger.error("Agent call failed: %s", exc)
            await self._client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": "⚠️ Fehler beim Verarbeiten der Anfrage."},
            )
        finally:
            await self._client.room_typing(room.room_id, typing_state=False)

    async def _on_invite(self, room: MatrixRoom, event: InviteMemberEvent) -> None:
        """Bot nimmt Einladungen automatisch an."""
        if event.state_key == self.config.bot_user_id:
            logger.info("Joining room %s (invited by %s)", room.room_id, event.sender)
            await self._client.join(room.room_id)

    async def stop(self) -> None:
        if self._client:
            await self._client.close()
```

---

## agent_bridge/agent_client.py

```python
from __future__ import annotations

import logging
import httpx

from agent_bridge.config import Config

logger = logging.getLogger(__name__)


class AgentClient:
    """HTTP Client zum bestehenden Agent-Service (Port 8094)."""

    def __init__(self, config: Config) -> None:
        self.base_url = config.agent_service_url
        self.timeout = config.agent_timeout_sec
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def send_message(
        self,
        message: str,
        room_id: str,
        sender: str,
        thread_id: str | None = None,
    ) -> str:
        """
        Sendet Nachricht an Agent-Service und gibt Text-Antwort zurück.
        Nutzt den bestehenden /agent/chat Endpoint (Phase 22d SSE streaming).
        Für Matrix: Non-Streaming → vollständige Antwort sammeln.
        """
        # Option A: Non-Streaming JSON Endpoint
        resp = await self._client.post(
            f"{self.base_url}/agent/chat",
            json={
                "message": message,
                "threadId": thread_id or room_id,
                "context": f"matrix_room:{room_id} sender:{sender}",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "")

        # Option B: SSE Stream sammeln (falls kein JSON-Endpoint)
        # full_text = ""
        # async with self._client.stream("POST", f"{self.base_url}/agent/chat/stream", ...) as r:
        #     async for line in r.aiter_lines():
        #         if line.startswith("data:"):
        #             chunk = json.loads(line[5:])
        #             if chunk.get("type") == "text_delta":
        #                 full_text += chunk.get("text", "")
        # return full_text

    async def close(self) -> None:
        await self._client.aclose()
```

---

## agent_bridge/app.py

```python
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent_bridge.config import Config
from agent_bridge.agent_client import AgentClient
from agent_bridge.matrix_client import MatrixBotClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config.from_env()
agent_client = AgentClient(config)
matrix_bot: MatrixBotClient | None = None
_sync_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global matrix_bot, _sync_task
    matrix_bot = MatrixBotClient(config, agent_client)
    _sync_task = asyncio.create_task(matrix_bot.start())
    logger.info("Matrix bot started")
    yield
    if matrix_bot:
        await matrix_bot.stop()
    if _sync_task:
        _sync_task.cancel()
    await agent_client.close()
    logger.info("Matrix bot stopped")


app = FastAPI(title="matrix-agent-bridge", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "bot": config.bot_user_id}
```

---

## .env (Python Agent Bridge)

```env
MATRIX_HOMESERVER_URL=http://localhost:8448
MATRIX_BOT_USER_ID=@trading-agent:matrix.local
MATRIX_BOT_PASSWORD=SICHERES_PASSWORT
# Nach erstem Login eintragen (aus Login-Response):
# MATRIX_BOT_ACCESS_TOKEN=syt_...
MATRIX_DEVICE_NAME=TradingAgent-Bridge
MATRIX_STORE_PATH=./data/matrix_store
AGENT_SERVICE_URL=http://localhost:8094
AGENT_TIMEOUT_SEC=120
NATS_URL=nats://localhost:4222
HOST=127.0.0.1
PORT=8097
```

---

## Starten

```powershell
cd python-agent-bridge
uv run uvicorn agent_bridge.app:app --host 127.0.0.1 --port 8097 --reload
```

---

## Verbindung zum Go Appservice

Der Python Bot und der Go Appservice sind **komplementär**:

| | Python matrix-nio Bot | Go Appservice |
|---|---|---|
| Matrix User-ID | `@trading-agent:domain` (echter Account) | `@agent-*:domain` (virtuell, Namespace) |
| Registrierung | Admin API (Token-basiert) | registration.yaml bei Tuwunel |
| Gut für | Einfacher Single-Agent-Bot | Multi-Agent, virtuelle IDs |
| Komplexität | Gering | Mittel |

**Empfehlung für Phase 1:** Mit Python matrix-nio Bot starten (simpler).
Go Appservice für Phase 2 wenn Multi-Agent-Matrix-IDs benötigt werden.
