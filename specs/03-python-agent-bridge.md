# Python Agent Bridge — NATS Consumer

**Status:** Aktiv
**Stand:** 06.04.2026 — matrix-nio entfernt (exec-05), reiner NATS Consumer im konsolidierten `python-backend/bridge/`

## Konzept

Die Python Agent Bridge ist ein FastAPI-Service in `python-backend/bridge/`, der als
**NATS Consumer** zwischen Go Appservice und Python Agent Service vermittelt. Sie ist
**kein Matrix-Client mehr** — der Go Appservice ist seit exec-05 der einzige
Matrix-Endpunkt (E2BE-Pattern, "Encrypted Backend, Bridged Endpoints").

**Flow:**
```
Matrix Room (Tuwunel)
    ↓ HTTP /transactions/
Go Appservice (Port 8090)             ← einziger Matrix-Endpunkt mit Crypto
    ↓ NATS publish (matrix.message.inbound)
Python Bridge (Port 8097)              ← DIESES PACKAGE
    ↓ HTTP SSE
Python Agent Service (Port 8094)       ← LangGraph Agent
    ↓ NATS publish (matrix.message.reply)
Go Appservice
    ↓ Encrypted reply via Olm/Megolm
Matrix Room
```

**Warum NATS statt direkter HTTP?**
- Matrix Events sind event-driven und asynchron — Pub/Sub passt natuerlich
- Go publisht "fire and forget", Python verarbeitet im eigenen Tempo
- Mehrere Bridge-Worker koennten subscriben (Skalierung)
- Ermoeglicht spaeter eine eigene "messaging bridge" (exec-05b: Slack/Discord/Telegram → Memory)

**Warum nicht mehr matrix-nio?**
- Doppelte Crypto-Verwaltung (Go + Python) ist fehleranfaellig
- Cross-Signing zwischen zwei Bots ist umstaendlich
- Python Agent kann stateless bleiben (keine Schluesselverwaltung)
- Go nutzt mautrix-go (besser maintained als matrix-nio in 2026)

---

## Verzeichnisstruktur

```
python-backend/bridge/
├── __init__.py
├── app.py             # FastAPI App (Lifecycle: NATS connect + subscribe + cleanup)
├── config.py          # Config.from_env() — NATS + Agent URLs
├── nats_handler.py    # NATS Consumer + Publisher
└── agent_client.py    # HTTP SSE Client zu Agent Service
```

Teil des konsolidierten `python-backend/` (siehe `00-overview.md`). Eigene Sub-Dependencies
gibt es nicht — alle Packages aus `python-backend/pyproject.toml`.

---

## Aktive Dependencies (`python-backend/pyproject.toml`)

Bridge nutzt nur das Subset, das fuers NATS-Consuming relevant ist:

```toml
fastapi>=0.120.3
uvicorn>=0.38.0
httpx==0.28.1
nats-py>=2.7.0       # NATS Client (E2BE-Pattern)
python-dotenv>=1.1.0
```

Keine Matrix Dependency. Kein matrix-nio. Kein E2EE Code in Python.

---

## bridge/config.py

```python
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class Config:
    # NATS
    nats_url: str               # nats://127.0.0.1:4222

    # Agent Service (in derselben Codebase, separater Process)
    agent_service_url: str      # http://127.0.0.1:8094
    agent_timeout_sec: float    # 120

    # Identity (fuer NATS Reply Subject + Audit)
    agent_user_id: str          # @agent-trading:matrix.local

    # Server (Health Check)
    host: str                   # 127.0.0.1
    port: int                   # 8097

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            nats_url=os.getenv("NATS_URL", "nats://127.0.0.1:4222"),
            agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8094"),
            agent_timeout_sec=float(os.getenv("AGENT_TIMEOUT_SEC", "120")),
            agent_user_id=os.getenv("AGENT_USER_ID", "@agent-trading:matrix.local"),
            host=os.getenv("BRIDGE_HOST", "127.0.0.1"),
            port=int(os.getenv("BRIDGE_PORT", "8097")),
        )
```

---

## bridge/nats_handler.py

Der NATS Handler abonniert `matrix.message.inbound`, ruft den Agent Service via HTTP SSE
auf und published die Antwort auf `matrix.message.reply`.

**Subjects:**

| Subject | Direction | Payload |
|---|---|---|
| `matrix.message.inbound` | Subscribe | `{room_id, sender, body, event_id, thread_id?}` |
| `matrix.message.reply` | Publish | `{room_id, agent_user_id, text, is_streaming, thread_id?}` |

**Pattern:** Eine Inbound-Message kann mehrere Reply-Messages erzeugen (Streaming-Chunks
oder Tool-Updates). Der Go Appservice rendert sie entweder als Edits oder als neue
Messages, je nach `is_streaming`.

---

## bridge/agent_client.py

HTTP Client zum Agent Service (Port 8094). Nutzt `/api/v1/agent/chat` mit SSE Streaming
und sammelt die Text-Deltas zu einer vollstaendigen Antwort, die dann via NATS published
wird.

**Endpoint:** `POST http://127.0.0.1:8094/api/v1/agent/chat`

**Request:**
```json
{
  "message": "User text",
  "threadId": "<room_id or thread_id>",
  "context": "matrix_room:!xyz:matrix.local sender:@alice:matrix.local"
}
```

**Response:** SSE stream im Vercel AI Data Stream Protocol
(siehe `agent-output-pattern.md`):
```
data: {"type":"thread_id","threadId":"..."}
data: {"type":"text_delta","id":"...","text":"Hello"}
data: {"type":"text_delta","id":"...","text":" world"}
data: {"type":"finish","usage":{...}}
```

Der Bridge sammelt alle `text_delta` Events und published sie entweder
- **als ein Reply** (default, `is_streaming=false`) — komplette Antwort am Ende
- **chunked** (zukunfts-optional, `is_streaming=true`) — Edits in Matrix

---

## bridge/app.py

```python
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bridge.config import Config
from bridge.agent_client import AgentClient
from bridge.nats_handler import NATSHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config.from_env()
agent_client = AgentClient(config)
nats_handler: NATSHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global nats_handler
    nats_handler = NATSHandler(config, agent_client)
    await nats_handler.connect()
    await nats_handler.subscribe()
    logger.info("Bridge started — subscribed to matrix.message.inbound")
    yield
    if nats_handler:
        await nats_handler.close()
    await agent_client.close()
    logger.info("Bridge stopped")


app = FastAPI(title="matrix-bridge", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent_user_id": config.agent_user_id,
        "nats": nats_handler.is_connected() if nats_handler else False,
    }
```

---

## ENV (`python-backend/.env`)

```env
NATS_URL=nats://127.0.0.1:4222
AGENT_SERVICE_URL=http://127.0.0.1:8094
AGENT_TIMEOUT_SEC=120
AGENT_USER_ID=@agent-trading:matrix.local
BRIDGE_HOST=127.0.0.1
BRIDGE_PORT=8097
```

---

## Starten

```bash
cd python-backend
uv run uvicorn bridge.app:app --host 127.0.0.1 --port 8097 --reload
```

Oder via docker-compose:
```bash
podman-compose up python-bridge
```

---

## Vorteile vs. matrix-nio Bridge

| Aspekt | matrix-nio Bridge (alt) | NATS Consumer Bridge (aktuell) |
|---|---|---|
| Matrix Crypto | Doppelt (Go + Python) | Nur Go |
| State | Stateful (Sync Token, Olm Store) | Stateless |
| Failure Recovery | Kompliziert (Sync Resume) | Trivial (NATS Replay/Queue) |
| Skalierbarkeit | 1 Bot Account | Mehrere Worker moeglich |
| Dependency-Last | matrix-nio[e2e] (libolm via CGO) | nats-py (pure Python) |
| Code-Komplexitaet | ~300 LoC (matrix_client.py) | ~80 LoC (nats_handler.py) |

---

## Verhaeltnis zum Go Appservice

```
Go Appservice (E2EE-Endpoint)        Python Bridge (Logic Bridge)
├── mautrix-go + goolm                ├── nats-py
├── Crypto Store (SQLite)             ├── HTTP Client (httpx)
├── Cross-Signing                     ├── Agent Service Caller
├── @agent-* Namespace                └── Stateless
├── NATS Producer
└── HTTP Proxy zu Agent Service
```

Beide Services sind im docker-compose default Profile aktiv:
```yaml
services:
  go-appservice:    # Port 8090
  python-bridge:    # Port 8097 (DIESES PACKAGE)
  python-agent:     # Port 8094 (Agent Service, separater Process)
  nats:             # Port 4222
  tuwunel:          # Port 8448
```

---

## Spaetere Erweiterung: exec-05b Messaging Bridges

Das gleiche NATS Pattern kann fuer andere Messaging-Plattformen genutzt werden:
- `slack.message.inbound` → Bridge zu Memory Engine
- `discord.message.inbound` → Bridge zu Memory Engine
- `telegram.message.inbound` → Bridge zu Memory Engine

Siehe `specs/execution/exec-05b-messaging-bridges.md` (Status: Geplant).
