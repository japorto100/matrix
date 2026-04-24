"""agent.a2ui — thin wrapper around Google's ``a2ui-agent-sdk``.

Scope:

* **Validation + schema**: reuse the official ``A2uiSchemaManager`` +
  ``A2uiValidator`` + ``BasicCatalog`` so our system prompts and tree
  validation stay aligned with the A2UI spec v0.9.
* **Incremental parsing**: reuse ``A2uiStreamParser`` for streaming LLM
  output; partial A2UI JSON blocks get progressively yielded as
  structured messages.
* **Wire packets**: we **do not** use the SDK's transport code. Instead
  we translate parsed SDK messages into our own ``streaming.py``
  Ansatz-X packets (``a2ui-surface-start`` / ``a2ui-update-*`` /
  ``a2ui-surface-end``) so they ride the same SSE channel as text and
  tool deltas.

Out of scope (installed as transitive deps, never imported here):

* ``google.adk`` — Google's Agent Dev Kit runtime. We use LangGraph.
* ``google.genai`` — Gemini direct client. We route via litellm.
* ``a2a-sdk`` — Agent-to-Agent protocol (kept for future exec-10 /
  exec-61 wiring; not loaded at runtime by this module).

Keeping only ``a2ui.schema`` / ``a2ui.parser`` / ``a2ui.basic_catalog``
imported means the google.adk + google.genai + a2a runtimes stay
outside our hot path — verified by sys.modules probe on the import set.
"""

from __future__ import annotations

from .emitter import (
    SYSTEM_PROMPT_ROLE_DEFAULT,
    A2uiEmitter,
    build_system_prompt,
    get_shared_catalog,
    get_shared_schema_manager,
    translate_sdk_message,
    validate_protocol_messages,
)

__all__ = [
    "A2uiEmitter",
    "SYSTEM_PROMPT_ROLE_DEFAULT",
    "build_system_prompt",
    "get_shared_catalog",
    "get_shared_schema_manager",
    "translate_sdk_message",
    "validate_protocol_messages",
]
