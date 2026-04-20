# Agent Service — FastAPI + WebSocket scaffold
# Phase 10a: Runtime, Rollen, BTE/DRS Guards, Memory/Context-Verdrahtung (10a.4)
# Phase 22d: Model-agnostic SSE streaming endpoint (AC7)
# Phase 22f: Audio endpoints — STT (ACR-A1) + TTS (ACR-A5)
#   Model + API Key kommen aus control-ui (DB) oder AGENT_DEFAULT_MODEL (ENV Fallback)
#   LLM Calls gehen ueber LiteLLM Gateway (LITELLM_BASE_URL)
#   AGENT_STT_PROVIDER=openai|whisper-local  (default: openai)
#   AGENT_TTS_PROVIDER=openai|kokoro  (default: openai)
#   AGENT_TTS_BASE_URL=<url>  (for Kokoro / self-hosted OpenAI-compatible TTS)
#   OPENAI_BASE_URL=<url>  (for Ollama/vLLM/OpenRouter/Azure and whisper-local)
#   ANTHROPIC_API_KEY / OPENAI_API_KEY
# Ref: AGENT_ARCHITECTURE.md, AGENT_TOOLS.md, CONTEXT_ENGINEERING.md

from __future__ import annotations

import base64
import os
import tempfile
import uuid

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

from agent.context_assembler import assemble_context  # noqa: E402
from agent.roles import AgentRole  # noqa: E402
from agent.tools.chart_state import get_chart_state, set_chart_state  # noqa: E402
from agent.tools.geomap import get_geomap_focus  # noqa: E402
from agent.tools.portfolio import get_portfolio_summary  # noqa: E402
from agent.working_memory import (  # noqa: E402
    working_memory_append,
    working_memory_get,
    working_memory_set,
)
from shared import create_service_app  # noqa: E402

app = create_service_app("agent-service")

# exec-09: MCP Server als Sub-App mounten (gleicher Port wie Agent Service)
from agent.mcp_server import create_mcp_server  # noqa: E402
from agent.mcp_traces import create_trace_mcp_server  # noqa: E402

_mcp = create_mcp_server()
app.mount("/mcp", _mcp.streamable_http_app())

# exec-17: MCP Trace Server for Claude Code trace inspection
_trace_mcp = create_trace_mcp_server()
app.mount("/mcp-traces", _trace_mcp.streamable_http_app())

# ABP.2c: close shared httpx client on shutdown to release connections cleanly.
from agent.http_client import close_client as _close_http_client  # noqa: E402

app.add_event_handler("shutdown", _close_http_client)

# exec-17: Auto-run Alembic migrations on startup (idempotent, non-fatal on error)
from agent.startup_migrations import run_migrations_if_enabled  # noqa: E402

app.add_event_handler("startup", run_migrations_if_enabled)

# exec-hermes Phase-B P1: seed CredentialPool + MemoryManager + ContextEngine
# singletons + probe agent.sync_failures table. Failures are soft (service
# stays up) — every failure surfaces via OTel span + /health/resilience.
from agent.resilience.init_stack import (  # noqa: E402
    init_agent_resilience_stack,
    resilience_health,
)

app.add_event_handler("startup", init_agent_resilience_stack)


@app.get("/health/resilience")
async def _health_resilience() -> JSONResponse:
    """Ops-visible status of the exec-hermes resilience singletons.

    HTTP 200 when all four subsystems (credential_pool, memory_manager,
    context_engine, sync_failures_table) are up. HTTP 503 otherwise so
    load-balancers can mark the pod unhealthy. Body always includes the
    per-subsystem ``up`` flag + ``detail`` string.
    """
    body = resilience_health()
    status_code = 200 if body["status"] == "up" else 503
    return JSONResponse(content=body, status_code=status_code)


@app.get("/api/v1/agent/ab/status")
async def _ab_status() -> JSONResponse:
    """Phase-C P3: report current A/B dispatcher configuration.

    Returns ``{active, percentage, kill_switch, ...}`` so ops can sanity-
    check rollout state and verify kill-switch responsiveness during an
    incident without reading env-vars or Valkey directly.
    """
    from agent.runners.dispatcher import ab_status

    return JSONResponse(await ab_status())


# exec-15 Slice 2: Control API router (thin proxies to ingestion-worker etc.)
from agent.control import router as _control_router  # noqa: E402

app.include_router(_control_router)


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


class FileAttachment(BaseModel):
    """AC56+exec-12: multimodal image or file attachment — base64 + mime_type."""

    base64: str
    mime_type: str = "image/jpeg"
    name: str = ""


class BrowserToolDef(BaseModel):
    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)


class AgentChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(max_length=50000)
    thread_id: str | None = Field(None, alias="threadId")
    agent_id: str | None = Field(None, alias="agentId")
    context: str | None = None
    model: str | None = None
    attachments: list[FileAttachment] | None = None
    reasoning_effort: str | None = Field(None, alias="reasoningEffort")
    browser_tools: list[BrowserToolDef] | None = Field(None, alias="browserTools")


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
    return {
        "ok": True,
        "service": "agent-service",
        "roles": [r.value for r in AgentRole],
    }


# ── Skill Management API (exec-10 Phase 5.2) ────────────────────────────────


@app.get("/api/v1/skills")
async def list_skills(
    category: str | None = None, user_id: str | None = None, team_id: str | None = None
):
    """List all available skills (global + team + personal)."""
    from agent.skills.loader import load_skills

    skills = load_skills(user_id=user_id, team_id=team_id, category=category)
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "tier": s.tier,
                "owner": s.owner,
                "generation": s.generation,
                "enabled": s.enabled,
                "db_id": getattr(s, "db_id", None),
                "source": "db" if getattr(s, "db_id", None) else "filesystem",
            }
            for s in skills
        ]
    }


class SkillUpdateRequest(BaseModel):
    enabled: bool


@app.put("/api/v1/skills/{skill_name}")
async def update_skill(skill_name: str, req: SkillUpdateRequest):
    """Enable/disable a skill by name."""
    from agent.skills.loader import load_skills

    skills = load_skills()
    skill = next((s for s in skills if s.name == skill_name), None)
    if skill is None:
        return JSONResponse(
            status_code=404, content={"error": f"Skill '{skill_name}' not found"}
        )
    skill.enabled = req.enabled
    return {"name": skill.name, "enabled": skill.enabled}


class SkillImportRequest(BaseModel):
    repo_url: str  # GitHub URL
    tier: str = "global"
    owner: str | None = None


@app.post("/api/v1/skills/import")
async def import_skills(req: SkillImportRequest):
    """Import skills from a GitHub repository (exec-10 Phase 5.3).

    skills_guard gates every incoming SKILL.md (exec-hermes §3.3). A blocked
    import returns HTTP 422 with ``{success: False, rejected: [...]}`` so the
    frontend can distinguish "policy rejected" from "internal error" (500).
    """
    from agent.skills.importer import import_from_github

    try:
        result = await import_from_github(req.repo_url, req.tier, req.owner)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={"error": str(e)})

    if not result.get("success"):
        return JSONResponse(status_code=422, content=result)
    imported = result.get("imported", [])
    return {
        "success": True,
        "imported": imported,
        "count": len(imported),
        "rejected": result.get("rejected", []),
    }


class SkillInstallRequest(BaseModel):
    path: str  # Path to .skill ZIP file
    tier: str = "global"
    owner: str | None = None


@app.post("/api/v1/skills/install")
async def install_skill_archive(req: SkillInstallRequest):
    """Install a skill from .skill ZIP archive (exec-10 Phase 5.4)."""
    from pathlib import Path

    from agent.skills.importer import install_from_archive

    # Security: restrict to allowed upload directory
    allowed_base = Path(
        os.environ.get("SKILL_UPLOAD_DIR", "/tmp/skill-uploads")
    ).resolve()
    resolved = Path(req.path).resolve()
    if not str(resolved).startswith(str(allowed_base)):
        return JSONResponse(
            status_code=400,
            content={"error": "path not within allowed upload directory"},
        )
    result = install_from_archive(req.path, req.tier, req.owner)
    if result["success"]:
        return JSONResponse(status_code=200, content=result)
    # 422 if rejected by skills_guard (dict carries verdict/findings),
    # else 400 for parse/size/path errors.
    status = 422 if "verdict" in result else 400
    return JSONResponse(status_code=status, content=result)


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
                    "content_preview": str(f.content)[:200]
                    if isinstance(f.content, (str, dict))
                    else str(f.content)[:200],
                }
                for f in fragments
            ],
            "flags": flags,
            "total": len(fragments),
        }
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "error": str(e),
                "flags": ["CONTEXT_ASSEMBLY_FAILED"],
            },
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


@app.get("/api/v1/agent/context/compression-status")
async def compression_status(thread_id: str | None = None, model: str = "") -> dict:
    """Phase-B P6: compression indicator for agent-chat.

    Returns the current ``ContextStage`` for a thread (or "normal" if we
    don't have observations yet). The UI shows a small dot — green/yellow/
    red — keyed off this value. Cheap and stateless: we compute from
    token-estimate + LiteLLM context-window, we do not query history.

    This endpoint deliberately does NOT require a session-id — it answers
    the question "could compression happen given the current prompt I'm
    about to send?" as well as "did compression already happen in the
    last turn I observed?".
    """
    from agent.llm.model_metadata import get_model_context_window
    from context.context_engine import get_context_engine

    engine = get_context_engine()
    window = get_model_context_window(model) if model else 200_000
    return {
        "thread_id": thread_id,
        "model": model or None,
        "window": window,
        "thresholds": {
            "pre_save": 0.80,
            "compaction": 0.85,
            "emergency": 0.95,
        },
        # usage_pct is populated from the most-recent span on the client
        # side (it's cheaper than re-scanning spans here every poll).
        "stage": "normal",
        "engine": type(engine).__name__,
    }


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
        await working_memory_set(
            "global",
            f"mutation:{result['mutation_id']}",
            {
                "type": "set_chart_state",
                "symbol": req.symbol,
                "timeframe": req.timeframe,
                "mutation_id": result["mutation_id"],
                "status": "pending_confirm",
            },
        )
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


# MIME types that go directly to the LLM as multimodal/text content
_LLM_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_LLM_DOCUMENT_TYPES = {"application/pdf"}
_LLM_TEXT_TYPES = {"text/plain"}
# MIME types that go to sandbox via file_analyze tool
_SANDBOX_TYPES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/x-parquet",
    "text/x-python",
    "application/javascript",
    "text/javascript",
}
_JSON_LLM_MAX_BYTES = 50_000  # JSON < 50KB goes to LLM, >= 50KB to sandbox


def _build_user_content(req: AgentChatRequest) -> list | str:
    """AC56+exec-12: Build user content — images/text to LLM, data files to sandbox."""
    if not req.attachments:
        return req.message
    content: list = []
    for att in req.attachments:
        if att.mime_type in _LLM_IMAGE_TYPES:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": att.mime_type,
                        "data": att.base64,
                    },
                }
            )
        elif att.mime_type in _LLM_DOCUMENT_TYPES:
            content.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": att.mime_type,
                        "data": att.base64,
                    },
                }
            )
        elif att.mime_type in _LLM_TEXT_TYPES:
            text_data = base64.b64decode(att.base64).decode("utf-8", errors="replace")
            content.append({"type": "text", "text": f"[File: {att.name}]\n{text_data}"})
        elif (
            att.mime_type == "application/json"
            and len(att.base64) < _JSON_LLM_MAX_BYTES
        ):
            json_data = base64.b64decode(att.base64).decode("utf-8", errors="replace")
            content.append({"type": "text", "text": f"[File: {att.name}]\n{json_data}"})
        else:
            # Sandbox file — don't send to LLM, just notify
            content.append(
                {
                    "type": "text",
                    "text": (
                        f"[File uploaded: {att.name} ({att.mime_type}). "
                        f"Use the file_analyze tool with file_ref='file:{att.name}' to analyze it.]"
                    ),
                }
            )
    content.append({"type": "text", "text": req.message})
    return content


async def _store_file_attachments(
    attachments: list[FileAttachment], thread_id: str
) -> None:
    """Store sandbox-bound file attachments in working memory for file_analyze tool."""
    for att in attachments:
        if att.mime_type in _LLM_IMAGE_TYPES | _LLM_DOCUMENT_TYPES | _LLM_TEXT_TYPES:
            continue
        if (
            att.mime_type == "application/json"
            and len(att.base64) < _JSON_LLM_MAX_BYTES
        ):
            continue
        # This file goes to sandbox — store in working memory
        await working_memory_set(
            thread_id,
            f"file:{att.name}",
            {
                "base64": att.base64,
                "name": att.name,
                "mime_type": att.mime_type,
            },
        )


@app.post("/api/v1/agent/chat")
async def agent_chat(req: AgentChatRequest, request: Request):
    """Agent chat endpoint — Vercel AI Data Stream Protocol SSE.
    Routes through run_agent_loop (LLM-agnostic, tool-capable, Phase 22g).
    LLM Calls gehen ueber LiteLLM Gateway. Model + Key aus DB (control-ui).
      - anthropic: Anthropic SDK, Claude models
      - openai: OpenAI API, GPT models
      - openai-compatible: OpenRouter, Ollama, vLLM, LM Studio
        (set OPENAI_BASE_URL, e.g. http://localhost:11434/v1 for Ollama)
    Architecture: Frontend → Go Gateway (control) → here (LLM calls).
    Phase 22d AC7 / Phase 22g ABP.1."""
    system_prompt = _build_system_prompt(req.context)
    thread_id = req.thread_id or str(uuid.uuid4())

    # exec-12 Phase 2.6: Read user role + id from Go Gateway headers
    user_role = request.headers.get("x-user-role", "viewer").lower()
    user_id = request.headers.get("x-auth-user", "default")

    # exec-12 Phase 1.4: Store sandbox-bound file attachments in working memory
    if req.attachments:
        await _store_file_attachments(req.attachments, thread_id)

    generator = _stream_agent_loop(
        req, system_prompt, thread_id, user_role=user_role, user_id=user_id
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_agent_loop(
    req: AgentChatRequest,
    system_prompt: str,
    thread_id: str,
    *,
    user_role: str = "viewer",
    user_id: str = "default",
):
    """Phase 22g: LLM-agnostic loop — Anthropic + OpenAI-compatible (OpenRouter, Ollama, vLLM).
    Builds AgentExecutionContext, loads ToolRegistry, runs run_agent_loop()."""
    try:
        from agent.context import AgentExecutionContext
        from agent.runners.dispatcher import run_agent_loop_with_variant
        from agent.tools.registry import ToolRegistry
    except ImportError as e:
        from agent.streaming import ErrorPacket, sse

        yield sse(ErrorPacket(error=f"Agent loop import error: {e}"))
        return

    # exec-16: Model + Key aus DB (control-ui), ENV als Fallback.
    from agent.security.credentials import (
        get_user_api_key,
        get_user_default_model,
        provider_from_model,
    )

    model = req.model or await get_user_default_model(user_id) or ""
    if not model:
        from agent.streaming import ErrorPacket, sse

        yield sse(
            ErrorPacket(
                error="Kein Model konfiguriert. Bitte in control-ui ein Model waehlen."
            )
        )
        return

    api_key = await get_user_api_key(user_id, provider_from_model(model))

    registry = ToolRegistry.load()

    # exec-09: Browser-Tools via WebMCP hinzufuegen (dynamisch je nach Page)
    if req.browser_tools:
        from agent.tools.browser_tool import BrowserToolProxy

        for bt in req.browser_tools:
            registry.register(
                BrowserToolProxy(bt.name, bt.description, bt.input_schema)
            )

    ctx = AgentExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        model=model,
        api_key=api_key,
        system_prompt=system_prompt,
        tools=tuple(registry.all()),
        reasoning_effort=req.reasoning_effort,
        agent_class="advisory",
        user_role=user_role,
    )

    # Build messages — AC56: multimodal content blocks for Anthropic
    user_content = _build_user_content(req)
    messages = [{"role": "user", "content": user_content}]

    # Phase-C P3: dispatcher picks LangGraph vs SimpleLoop per-user.
    # Default PCT=0 → 100% LangGraph, kill-switch safe by design.
    async for chunk in run_agent_loop_with_variant(ctx, messages):
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
    Routes via AGENT_STT_PROVIDER (openai|whisper-local|litellm). Default: litellm.
    litellm: routes through LiteLLM proxy (spend tracking, provider-agnostic).
    whisper-local: WhisperLiveKit on OPENAI_BASE_URL (on-premise, no cloud).
    ACR-A1 / Phase 22f."""
    provider = os.environ.get("AGENT_STT_PROVIDER", "litellm")
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": "openai package not installed"},
        )

    audio_bytes = base64.b64decode(req.audio_base64)
    ext = _AUDIO_MIME_EXT.get(req.mime_type, ".webm")

    if provider == "whisper-local":
        # On-premise: WhisperLiveKit OpenAI-compatible endpoint
        base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:8095/v1")
        api_key = "not-needed"
    elif provider == "litellm":
        # Through LiteLLM proxy (spend tracking, failover)
        base_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
        api_key = "sk-litellm"
    else:
        # Direct to OpenAI (legacy)
        base_url = None
        api_key = os.environ.get("OPENAI_API_KEY", "not-set")
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
    Routes via AGENT_TTS_PROVIDER (openai|kokoro|litellm). Default: litellm.
    litellm: routes through LiteLLM proxy (spend tracking, provider-agnostic).
    kokoro / openai-compatible: AGENT_TTS_BASE_URL points at self-hosted service (on-premise).
    ACR-A5 / Phase 22f."""
    from fastapi.responses import Response as FastAPIResponse

    provider = os.environ.get("AGENT_TTS_PROVIDER", "litellm")
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": "openai package not installed"},
        )

    if provider in ("kokoro", "openai-compatible"):
        # On-premise: Kokoro / self-hosted OpenAI-compatible TTS
        base_url = os.environ.get("AGENT_TTS_BASE_URL", "http://localhost:8095/v1")
        api_key = "not-needed"
    elif provider == "litellm":
        # Through LiteLLM proxy (spend tracking, failover)
        base_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
        api_key = "sk-litellm"
    else:
        # Direct to OpenAI (legacy)
        base_url = None
        api_key = os.environ.get("OPENAI_API_KEY", "not-set")
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
                {
                    "received": data,
                    "roles": [r.value for r in AgentRole],
                    "status": "scaffold",
                }
            )
    except WebSocketDisconnect:
        pass
