"""Top-level Control API router.

Includes sub-routers from each control area. To add a new control surface:
1. Create agent/control/<area>.py with `router = APIRouter(tags=[...])`
2. Import here and include with router.include_router(...)
"""

from __future__ import annotations

from fastapi import APIRouter

from agent.control.a2a import router as a2a_router
from agent.control.agents import router as agents_router
from agent.control.audit import router as audit_router
from agent.control.context import router as context_router
from agent.control.episodes import router as episodes_router
from agent.control.highlights import router as highlights_router
from agent.control.ingestion import router as ingestion_router
from agent.control.kg_context import router as kg_context_router
from agent.control.kg_crud import router as kg_router
from agent.control.mcp import router as mcp_router
from agent.control.memory import router as memory_router
from agent.control.models import router as models_router
from agent.control.overview import router as overview_router
from agent.control.permissions import router as permissions_router
from agent.control.sandbox import router as sandbox_router
from agent.control.security import router as security_router
from agent.control.sessions import router as sessions_router
from agent.control.skills import router as skills_router
from agent.control.system import router as system_router
from agent.control.tools import router as tools_router
from agent.control.user_llm import router as user_llm_router

router = APIRouter(prefix="/api/v1/control", tags=["control"])

# Slice 2: Ingestion proxy (thin httpx to ingestion-worker :8098)
router.include_router(ingestion_router)

# Slice 3: Memory layer health + Episodes (faceted list/get/delete via Hindsight)
router.include_router(memory_router)
router.include_router(episodes_router)
router.include_router(highlights_router)
router.include_router(kg_context_router)

# Slice 4: Trading KG CRUD (via memory_engine/kg_store.py Kuzu backend)
router.include_router(kg_router)

# Slice 5: Agent Configuration (agents, permissions, skills, tools, sandbox)
router.include_router(agents_router)
router.include_router(permissions_router)
router.include_router(skills_router)
router.include_router(tools_router)
router.include_router(sandbox_router)

# Slice 6: System Observability (system, audit, sessions, mcp, a2a)
router.include_router(system_router)
router.include_router(audit_router)
router.include_router(context_router)
router.include_router(sessions_router)
router.include_router(mcp_router)
router.include_router(a2a_router)

# Slice 7: Two-Tier User Mode adds (overview, security, api/models)
router.include_router(overview_router)
router.include_router(security_router)
router.include_router(models_router)

# exec-16: Per-user LLM settings (API keys, default model, per-role routing)
router.include_router(user_llm_router)

__all__ = ["router"]
