# /// script
# dependencies = ["fastapi>=0.116.0", "uvicorn>=0.35.0"]
# ///
"""
LLM Mock Agent — simuliert den echten Agent-Service für Tests.

Start:  uv run llm-mock/mock_agent.py
Port:   8094 (identisch zum echten Agent-Service)
Zweck:  Testen ob Matrix → Go Appservice → Python Bridge → Agent funktioniert,
        ohne den echten AI-Service zu benötigen.

SSE Format (Vercel AI Data Stream Protocol):
  data: {"type":"thread_id","threadId":"..."}
  data: {"type":"text_start","id":"t1"}
  data: {"type":"text_delta","id":"t1","text":"..."}
  data: {"type":"text_end","id":"t1"}
  data: {"type":"finish","usage":{"input_tokens":10,"output_tokens":20}}
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO, format="[mock-agent] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Mock Agent", version="1.0.0")

# Mock-Antworten (rotierend)
_RESPONSES = [
    "Hallo! Ich bin der **Mock-Agent**. Deine Nachricht ist angekommen. 🤖",
    "Mock-Antwort: Das Matrix-Setup funktioniert einwandfrei! Go ↔ NATS ↔ Python ↔ Mock.",
    "Alles gut hier! Wenn du das siehst, ist der komplette Stack aktiv:\nTuwunel → Go Appservice → NATS → Python Bridge → Mock Agent",
    "Test erfolgreich! Stack läuft: Homeserver ✅ | NATS ✅ | Go Appservice ✅ | Python Bridge ✅ | Mock ✅",
]
_response_idx = 0


async def _sse_stream(message: str, thread_id: str):
    """Generiert einen SSE-Stream im Vercel AI Data Stream Protocol Format."""
    global _response_idx

    mock_text = _RESPONSES[_response_idx % len(_RESPONSES)]
    _response_idx += 1

    # Thread-ID Paket
    yield f"data: {json.dumps({'type': 'thread_id', 'threadId': thread_id})}\n\n"
    await asyncio.sleep(0.05)

    # Text-Start
    yield f"data: {json.dumps({'type': 'text_start', 'id': 't1'})}\n\n"
    await asyncio.sleep(0.05)

    # Text in Chunks streamen (realistisch)
    words = mock_text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield f"data: {json.dumps({'type': 'text_delta', 'id': 't1', 'text': chunk})}\n\n"
        await asyncio.sleep(0.04)  # 40ms pro Wort — realistisches Streaming

    # Text-Ende
    yield f"data: {json.dumps({'type': 'text_end', 'id': 't1'})}\n\n"
    await asyncio.sleep(0.05)

    # Finish mit Tokens
    yield f"data: {json.dumps({'type': 'finish', 'usage': {'input_tokens': len(message.split()), 'output_tokens': len(mock_text.split())}})}\n\n"


@app.post("/api/v1/agent/chat")
async def agent_chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    thread_id = body.get("threadId", "unknown")
    context = body.get("context", "")

    logger.info("Chat request | thread=%s context=%s msg=%.60s", thread_id, context, message)

    return StreamingResponse(
        _sse_stream(message, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "llm-mock-agent",
        "time": datetime.now().isoformat(),
        "note": "Mock-Agent — kein echter LLM, nur für Tests",
    }


@app.get("/")
async def root():
    return {"service": "llm-mock-agent", "port": 8094, "endpoints": ["/api/v1/agent/chat", "/health"]}


if __name__ == "__main__":
    import os

    host = os.environ.get("MOCK_HOST", "127.0.0.1")
    logger.info("Mock Agent startet auf http://%s:8094", host)
    logger.info("Endpunkte: POST /api/v1/agent/chat | GET /health")
    uvicorn.run(app, host=host, port=8094, log_level="warning")
