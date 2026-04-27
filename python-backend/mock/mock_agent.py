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
import time
from datetime import datetime
from typing import Any

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

    logger.info(
        "Chat request | thread=%s context=%s msg=%.60s", thread_id, context, message
    )

    return StreamingResponse(
        _sse_stream(message, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _latest_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    str(item.get("text") or "")
                    for item in content
                    if isinstance(item, dict)
                ]
                return " ".join(part for part in parts if part)
    return ""


def _mock_chat_text(prompt: str) -> str:
    text = prompt.strip().lower()
    if "runner parity smoke" in text:
        return "runner parity smoke."
    if "memory" in text:
        return "Mock memory response."
    if "tool" in text:
        return "Mock tool-free response."
    return "Mock LLM response."


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint for local harness gates."""
    body = await request.json()
    messages = body.get("messages") or []
    model = str(body.get("model") or "mock/local")
    max_tokens = body.get("max_tokens")
    prompt = _latest_user_text(messages if isinstance(messages, list) else [])
    content = _mock_chat_text(prompt)
    if isinstance(max_tokens, int) and max_tokens > 0:
        content = " ".join(content.split()[:max_tokens])

    prompt_tokens = sum(
        len(str(message.get("content") or "").split())
        for message in messages
        if isinstance(message, dict)
    )
    completion_tokens = len(content.split())
    return {
        "id": f"chatcmpl-mock-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


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
    return {
        "service": "llm-mock-agent",
        "port": 8094,
        "endpoints": ["/api/v1/agent/chat", "/health"],
    }


if __name__ == "__main__":
    import os

    host = os.environ.get("MOCK_HOST", "127.0.0.1")
    port = int(os.environ.get("MOCK_PORT", "8094"))
    logger.info("Mock Agent startet auf http://%s:%s", host, port)
    logger.info(
        "Endpunkte: POST /api/v1/agent/chat | POST /chat/completions | GET /health"
    )
    uvicorn.run(app, host=host, port=port, log_level="warning")
