# Agent Service — FastAPI + WebSocket scaffold
# Phase 10a: Runtime, Rollen, BTE/DRS Guards, Memory/Context-Verdrahtung (10a.4)
# Phase 22d: Model-agnostic SSE streaming endpoint (AC7)
# Phase 22f: Audio endpoints — STT (ACR-A1) + TTS (ACR-A5)
#   AGENT_PROVIDER=anthropic|openai|openai-compatible  (default: anthropic)
#   AGENT_MODEL=<model id>  (default: claude-sonnet-4-6 / gpt-4o)
#   AGENT_STT_PROVIDER=openai|whisper-local  (default: openai)
#   AGENT_TTS_PROVIDER=openai|kokoro  (default: openai)
#   AGENT_TTS_BASE_URL=<url>  (for Kokoro / self-hosted OpenAI-compatible TTS)
#   OPENAI_BASE_URL=<url>  (for Ollama/vLLM/OpenRouter/Azure and whisper-local)
#   ANTHROPIC_API_KEY / OPENAI_API_KEY
# Ref: AGENT_ARCHITECTURE.md, AGENT_TOOLS.md, CONTEXT_ENGINEERING.md

from __future__ import annotations

import base64
import json
import os
import tempfile
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from shared import create_service_app  # noqa: E402
from agent.roles import AgentRole  # noqa: E402
from agent.context_assembler import assemble_context  # noqa: E402
from agent.working_memory import (  # noqa: E402
    working_memory_append,
    working_memory_get,
    working_memory_set,
)
from agent.tools.chart_state import get_chart_state, set_chart_state  # noqa: E402
from agent.tools.geomap import get_geomap_focus  # noqa: E402
from agent.tools.portfolio import get_portfolio_summary  # noqa: E402

app = create_service_app("agent-service")

# ABP.2c: close shared httpx client on shutdown to release connections cleanly.
from agent.http_client import close_client as _close_http_client  # noqa: E402
app.add_event_handler("shutdown", _close_http_client)


class ContextRequest(BaseModel):
    query: str
    kg_node_type: str = "Stratagem"
    kg_limit: int = 10
    episodic_limit: int = 3
    vector_limit: int = 5


class WorkingMemorySetRequest(BaseModel):
    session_id: str
    entry_id: str
    content: dict | str


class WorkingMemoryAppendRequest(BaseModel):
    session_id: str
    role: str
    content: dict | str


class SetChartStateRequest(BaseModel):
    symbol: str
    timeframe: str


class ImageAttachment(BaseModel):
    """AC56: multimodal image attachment — base64 + mime_type."""
    base64: str
    mime_type: str = "image/jpeg"
    name: str = ""


class AgentChatRequest(BaseModel):
    message: str
    threadId: str | None = None
    agentId: str | None = None
    context: str | None = None
    model: str | None = None  # AC107: override AGENT_MODEL env var
    attachments: list[ImageAttachment] | None = None  # AC56: multimodal images
    reasoningEffort: str | None = None  # AC108: low/medium/high


class AudioTranscribeRequest(BaseModel):
    """ACR-A1: base64-encoded audio → transcript text."""
    audio_base64: str
    mime_type: str = "audio/webm"
    language: str | None = None


class AudioSynthesizeRequest(BaseModel):
    """ACR-A5: text → audio bytes (mp3)."""
    text: str
    voice: str = "alloy"  # openai voices: alloy/echo/fable/onyx/nova/shimmer
    model: str | None = None  # override AGENT_TTS_MODEL env var


@app.get("/health")
async def health():
    return {"ok": True, "service": "agent-service", "roles": [r.value for r in AgentRole]}


@app.post("/api/v1/agent/context")
async def agent_context(req: ContextRequest):
    """Assemble context from Memory layers (KG, Episodic, Vector) for agent. Phase 10a.4."""
    try:
        fragments, flags = await assemble_context(
            req.query,
            kg_node_type=req.kg_node_type,
            kg_limit=req.kg_limit,
            episodic_limit=req.episodic_limit,
            vector_limit=req.vector_limit,
        )
        return {
            "ok": True,
            "fragments": [
                {
                    "source": f.source,
                    "relevance": f.relevance,
                    "content_preview": str(f.content)[:200] if isinstance(f.content, (str, dict)) else str(f.content)[:200],
                }
                for f in fragments
            ],
            "flags": flags,
            "total": len(fragments),
        }
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": str(e), "flags": ["CONTEXT_ASSEMBLY_FAILED"]},
        )


@app.get("/api/v1/agent/working-memory/{session_id}")
async def get_working_memory(session_id: str):
    """Get M5 scratchpad for session. Phase 10c."""
    data = await working_memory_get(session_id)
    return {"ok": True, "session_id": session_id, "entries": data}


@app.post("/api/v1/agent/working-memory")
async def set_working_memory(req: WorkingMemorySetRequest):
    """Set entry in M5 scratchpad. Phase 10c."""
    await working_memory_set(req.session_id, req.entry_id, req.content)
    return {"ok": True, "entry_id": req.entry_id}


@app.post("/api/v1/agent/working-memory/append")
async def append_working_memory(req: WorkingMemoryAppendRequest):
    """Append entry to M5 scratchpad. Phase 10c."""
    entry_id = await working_memory_append(req.session_id, req.role, req.content)
    return {"ok": True, "entry_id": entry_id}


@app.get("/api/v1/agent/tools/chart-state")
async def tool_chart_state():
    """WebMCP Tool: get_chart_state. Phase 10e.1."""
    return await get_chart_state()


@app.get("/api/v1/agent/tools/portfolio-summary")
async def tool_portfolio_summary():
    """WebMCP Tool: get_portfolio_summary. Phase 10e.2."""
    return await get_portfolio_summary()


@app.get("/api/v1/agent/tools/geomap-focus")
async def tool_geomap_focus():
    """WebMCP Tool: get_geomap_focus. Phase 10e.3."""
    return await get_geomap_focus()


@app.post("/api/v1/agent/tools/set_chart_state")
async def tool_set_chart_state(req: SetChartStateRequest):
    """WebMCP Mutation Tool: set_chart_state. Phase 10.v3.
    Stores pending mutation — frontend must confirm before applying."""
    try:
        result = await set_chart_state(req.symbol, req.timeframe)
        await working_memory_set("global", f"mutation:{result['mutation_id']}", {
            "type": "set_chart_state",
            "symbol": req.symbol,
            "timeframe": req.timeframe,
            "mutation_id": result["mutation_id"],
            "status": "pending_confirm",
        })
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


def _build_system_prompt(context: str | None) -> str:
    parts = [
        "You are a professional trading assistant for TradeView Fusion.",
        "You provide market analysis, strategy insights, and research.",
        "POLICY: no_trading_actions — you NEVER execute trades, place orders, or modify positions.",
        "All your responses are read-only advisory. Critical mutations require explicit user action.",
    ]
    if context:
        parts.append(f"Current context: {context}")
    return "\n".join(parts)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _build_user_content(req: "AgentChatRequest") -> list | str:
    """AC56: Build Anthropic user content — text + optional image blocks."""
    if not req.attachments:
        return req.message
    content: list = []
    for att in req.attachments:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": att.mime_type,
                "data": att.base64,
            },
        })
    content.append({"type": "text", "text": req.message})
    return content


_REASONING_BUDGET: dict[str, int] = {
    "low": 1024,
    "medium": 4096,
    "high": 16384,
}


async def _stream_anthropic(req: AgentChatRequest, system_prompt: str, thread_id: str):
    """Stream via Anthropic SDK — emits Vercel AI Data Stream Protocol events.
    AC56: multimodal content blocks. AC108: extended thinking via reasoningEffort.
    ACR-G5: emits message-metadata with token usage. ACR-G7: emits thread-id."""
    try:
        from anthropic import AsyncAnthropic, APIError, APIStatusError
    except ImportError:
        yield _sse({"type": "error", "error": "anthropic package not installed"})
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield _sse({"type": "error", "error": "ANTHROPIC_API_KEY not configured"})
        return

    model = req.model or os.environ.get("AGENT_MODEL", "claude-sonnet-4-6")
    client = AsyncAnthropic(api_key=api_key)
    text_id = "t1"

    # AC108: reasoning/thinking budget
    thinking_param: dict | None = None
    if req.reasoningEffort and req.reasoningEffort in _REASONING_BUDGET:
        budget = _REASONING_BUDGET[req.reasoningEffort]
        thinking_param = {"type": "enabled", "budget_tokens": budget}

    user_content = _build_user_content(req)
    stream_kwargs: dict = {
        "model": model,
        "max_tokens": 8192 if thinking_param else 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    if thinking_param:
        stream_kwargs["thinking"] = thinking_param

    try:
        # ACR-G7: thread-id as first event so frontend can update threadIdRef
        yield _sse({"type": "thread-id", "threadId": thread_id})
        yield _sse({"type": "text-start", "id": text_id})
        async with client.messages.stream(**stream_kwargs) as stream:
            async for text in stream.text_stream:
                yield _sse({"type": "text-delta", "id": text_id, "delta": text})
            final = await stream.get_final_message()
            prompt_tokens = final.usage.input_tokens
            completion_tokens = final.usage.output_tokens
        yield _sse({"type": "text-end", "id": text_id})
        # ACR-G5: message-metadata → message.metadata in Vercel AI SDK onFinish
        yield _sse({"type": "message-metadata", "metadata": {
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "threadId": thread_id,
        }})
        yield _sse({"type": "finish", "finishReason": "stop"})
    except APIStatusError as e:
        yield _sse({"type": "error", "error": f"Anthropic API error {e.status_code}: {e.message}"})
    except APIError as e:
        yield _sse({"type": "error", "error": f"Anthropic API error: {e.message}"})
    except Exception as e:
        yield _sse({"type": "error", "error": str(e)})


async def _stream_openai(req: AgentChatRequest, system_prompt: str, thread_id: str):
    """Stream via OpenAI SDK — covers OpenAI, OpenRouter, Ollama, vLLM, Azure.
    Set OPENAI_BASE_URL to target any OpenAI-compatible endpoint.
    ACR-G5: emits message-metadata with token usage. ACR-G7: emits thread-id."""
    try:
        from openai import AsyncOpenAI, APIError, APIStatusError
    except ImportError:
        yield _sse({"type": "error", "error": "openai package not installed"})
        return

    api_key = os.environ.get("OPENAI_API_KEY", "not-set")
    base_url = os.environ.get("OPENAI_BASE_URL")  # None = default OpenAI
    model = req.model or os.environ.get("AGENT_MODEL", "gpt-4o")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    text_id = "t1"
    try:
        # ACR-G7: thread-id as first event so frontend can update threadIdRef
        yield _sse({"type": "thread-id", "threadId": thread_id})
        yield _sse({"type": "text-start", "id": text_id})
        prompt_tokens = 0
        completion_tokens = 0
        # AC56: build OpenAI-compatible multimodal content
        if req.attachments:
            user_parts: list = []
            for att in req.attachments:
                user_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{att.mime_type};base64,{att.base64}"},
                })
            user_parts.append({"type": "text", "text": req.message})
            user_content_oa: list | str = user_parts
        else:
            user_content_oa = req.message

        stream = await client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content_oa},
            ],
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield _sse({"type": "text-delta", "id": text_id, "delta": chunk.choices[0].delta.content})
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens or 0
                completion_tokens = chunk.usage.completion_tokens or 0
        yield _sse({"type": "text-end", "id": text_id})
        # ACR-G5: message-metadata → message.metadata in Vercel AI SDK onFinish
        yield _sse({"type": "message-metadata", "metadata": {
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "threadId": thread_id,
        }})
        yield _sse({"type": "finish", "finishReason": "stop"})
    except APIStatusError as e:
        yield _sse({"type": "error", "error": f"OpenAI API error {e.status_code}: {e.message}"})
    except APIError as e:
        yield _sse({"type": "error", "error": f"OpenAI API error: {e.message}"})
    except Exception as e:
        yield _sse({"type": "error", "error": str(e)})


@app.post("/api/v1/agent/chat")
async def agent_chat(req: AgentChatRequest):
    """Agent chat endpoint — Vercel AI Data Stream Protocol SSE.
    Routes through run_agent_loop (LLM-agnostic, tool-capable, Phase 22g).
    Provider: AGENT_PROVIDER=anthropic (default) | openai | openai-compatible
      - anthropic: Anthropic SDK, Claude models
      - openai: OpenAI API, GPT models
      - openai-compatible: OpenRouter, Ollama, vLLM, LM Studio
        (set OPENAI_BASE_URL, e.g. http://localhost:11434/v1 for Ollama)
    Architecture: Frontend → Go Gateway (control) → here (LLM calls).
    Phase 22d AC7 / Phase 22g ABP.1."""
    system_prompt = _build_system_prompt(req.context)
    thread_id = req.threadId or str(uuid.uuid4())

    generator = _stream_agent_loop(req, system_prompt, thread_id)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_agent_loop(req: AgentChatRequest, system_prompt: str, thread_id: str):
    """Phase 22g: LLM-agnostic loop — Anthropic + OpenAI-compatible (OpenRouter, Ollama, vLLM).
    Builds AgentExecutionContext, loads ToolRegistry, runs run_agent_loop()."""
    try:
        from agent.context import AgentExecutionContext
        from agent.loop import run_agent_loop
        from agent.tools.registry import ToolRegistry
    except ImportError as e:
        from agent.streaming import ErrorPacket, sse
        yield sse(ErrorPacket(error=f"Agent loop import error: {e}"))
        return

    # Default model per provider
    provider = os.environ.get("AGENT_PROVIDER", "anthropic").lower()
    default_model = "claude-sonnet-4-6" if provider == "anthropic" else "gpt-4o"
    model = req.model or os.environ.get("AGENT_MODEL", default_model)

    registry = ToolRegistry.load()
    ctx = AgentExecutionContext(
        user_id="default",  # Go Gateway forwards X-Auth-User-Id; future: read from header
        thread_id=thread_id,
        model=model,
        system_prompt=system_prompt,
        tools=tuple(registry.all()),
        reasoning_effort=req.reasoningEffort,
        agent_class="advisory",
    )

    # Build messages — AC56: multimodal content blocks for Anthropic
    user_content = _build_user_content(req)
    messages = [{"role": "user", "content": user_content}]

    async for chunk in run_agent_loop(ctx, messages):
        yield chunk


_AUDIO_MIME_EXT: dict[str, str] = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/mp3": ".mp3",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/m4a": ".m4a",
}


@app.post("/api/v1/audio/transcribe")
async def audio_transcribe(req: AudioTranscribeRequest):
    """STT: base64 audio → transcript text.
    Routes via AGENT_STT_PROVIDER (openai|whisper-local). Default: openai (Whisper API).
    whisper-local uses OPENAI_BASE_URL to point at WhisperLiveKit OpenAI-compatible endpoint.
    ACR-A1 / Phase 22f."""
    provider = os.environ.get("AGENT_STT_PROVIDER", "openai")
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return JSONResponse(status_code=502, content={"ok": False, "error": "openai package not installed"})

    audio_bytes = base64.b64decode(req.audio_base64)
    ext = _AUDIO_MIME_EXT.get(req.mime_type, ".webm")
    api_key = os.environ.get("OPENAI_API_KEY", "not-set")
    # whisper-local: point at self-hosted endpoint (WhisperLiveKit on Port 8095)
    base_url = os.environ.get("OPENAI_BASE_URL") if provider == "whisper-local" else None
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        with open(tmp_path, "rb") as audio_file:
            # Only pass language when set — avoids openai SDK's str|Omit sentinel typing.
            transcribe_kwargs: dict = {"model": "whisper-1", "file": audio_file}
            if req.language is not None:
                transcribe_kwargs["language"] = req.language
            transcript = await client.audio.transcriptions.create(**transcribe_kwargs)
        return {"ok": True, "text": transcript.text}
    except Exception as e:
        return JSONResponse(status_code=502, content={"ok": False, "error": str(e)})
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.post("/api/v1/audio/synthesize")
async def audio_synthesize(req: AudioSynthesizeRequest):
    """TTS: text → audio bytes (mp3).
    Routes via AGENT_TTS_PROVIDER (openai|kokoro). Default: openai.
    kokoro / openai-compatible: AGENT_TTS_BASE_URL points at self-hosted service.
    ACR-A5 / Phase 22f."""
    from fastapi.responses import Response as FastAPIResponse

    provider = os.environ.get("AGENT_TTS_PROVIDER", "openai")
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return JSONResponse(status_code=502, content={"ok": False, "error": "openai package not installed"})

    api_key = os.environ.get("OPENAI_API_KEY", "not-set")
    # Kokoro / self-hosted: AGENT_TTS_BASE_URL overrides default OpenAI endpoint
    base_url = os.environ.get("AGENT_TTS_BASE_URL") if provider in ("kokoro", "openai-compatible") else None
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    tts_model = req.model or os.environ.get("AGENT_TTS_MODEL", "tts-1")

    try:
        response = await client.audio.speech.create(
            model=tts_model,
            voice=req.voice,
            input=req.text,
            response_format="mp3",
        )
        return FastAPIResponse(
            content=response.content,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as e:
        return JSONResponse(status_code=502, content={"ok": False, "error": str(e)})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket scaffold for agent runtime. Phase 10a."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Placeholder: echo back with role info
            await websocket.send_json(
                {"received": data, "roles": [r.value for r in AgentRole], "status": "scaffold"}
            )
    except WebSocketDisconnect:
        pass
