"""MemoryProvider ABC + MemoryManager (exec-hermes §3.2).

Pluggable memory backends sit behind one abstract contract so the agent
harness can treat Hindsight, MemPalace, Fusion, and future providers
(Personal-KB, World-Model) uniformly. ``MemoryManager`` coordinates
multiple providers — fan-out for prefetch / sync_turn / on_pre_compress,
per-provider error isolation so a broken provider can't starve the rest.

Design follows the hermes reference (`_ref/hermes-agent/agent/memory_provider.py`)
but deliberately **minimal** for Phase A:

- ``prefetch`` (recall before turn)
- ``sync_turn`` (write after turn)
- ``on_pre_compress`` (killer hook at the ≥80% context-window threshold —
  see exec-context §6.1 and exec-memory §3e)
- ``on_session_end`` (final flush)
- ``system_prompt_block`` (static injection)

Concrete implementations accept an engine instance in the constructor so
they stay testable without a live Postgres / palace. A factory helper
(:func:`auto_fusion_provider`) builds the default setup from env.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryRecall",
    "MemoryProvider",
    "MemoryManager",
    "FusionProvider",
    "auto_fusion_provider",
    "get_memory_manager",
    "set_memory_manager",
    "reset_memory_manager",
]


@dataclass(frozen=True)
class MemoryRecall:
    """One unit of recalled memory returned by :meth:`MemoryProvider.prefetch`."""

    provider: str
    content: str
    source_ref: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryProvider(ABC):
    """Abstract contract for a memory backend.

    Subclasses must provide :attr:`name`, :meth:`is_available`,
    :meth:`prefetch`, and :meth:`sync_turn`. All other hooks have safe
    defaults — override when the provider has something useful to do.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier (e.g. ``"hindsight"``, ``"mempalace"``, ``"fusion"``)."""

    @abstractmethod
    async def is_available(self) -> bool:
        """True when the provider can serve requests right now.

        Implementations typically check that the underlying engine was
        initialised successfully and its backing store is reachable.
        """

    async def initialize(self) -> None:
        """Idempotent boot. Override for eager init; default no-op."""

    async def shutdown(self) -> None:
        """Graceful teardown. Override when needed; default no-op."""

    @abstractmethod
    async def prefetch(
        self,
        query: str,
        *,
        user_id: str,
        bank_id: str,
        limit: int = 5,
    ) -> list[MemoryRecall]:
        """Recall items before a turn. Must return a list (possibly empty)."""

    @abstractmethod
    async def sync_turn(
        self,
        user_message: str,
        assistant_message: str,
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        """Persist the finished turn (write-after)."""

    async def on_pre_compress(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> str | None:
        """Fire at the ≥80% context-window threshold BEFORE compaction
        shrinks the visible chat. Providers should persist verbatim content
        and MAY return a short summary snippet to re-inject post-compact.

        Default implementation is a no-op returning ``None``.
        """
        return None

    async def on_session_end(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        """End-of-session flush. Default no-op."""

    def system_prompt_block(self) -> str | None:
        """Static block injected into the system prompt. ``None`` = no inject."""
        return None


class MemoryManager:
    """Coordinate a list of :class:`MemoryProvider` instances.

    Responsible for fan-out semantics:

    - :meth:`prefetch` queries every available provider and concatenates
      their :class:`MemoryRecall` lists.
    - :meth:`sync_turn` / :meth:`on_session_end` dispatch sequentially;
      per-provider errors are logged and swallowed so one flaky provider
      cannot break the agent loop.
    - :meth:`on_pre_compress` returns the non-empty snippets each provider
      emitted so the caller can choose how to re-inject them.

    Not thread-safe. Single-loop asyncio is the intended runtime.
    """

    def __init__(self, providers: list[MemoryProvider]) -> None:
        self._providers: list[MemoryProvider] = list(providers)

    @property
    def providers(self) -> list[MemoryProvider]:
        """Registered providers in insertion order (defensive copy)."""
        return list(self._providers)

    async def available_providers(self) -> list[MemoryProvider]:
        out: list[MemoryProvider] = []
        for p in self._providers:
            try:
                if await p.is_available():
                    out.append(p)
            except Exception:  # noqa: BLE001
                logger.debug(
                    "memory provider %s is_available check raised", p.name,
                    exc_info=True,
                )
        return out

    async def prefetch(
        self,
        query: str,
        *,
        user_id: str,
        bank_id: str,
        limit_per_provider: int = 5,
    ) -> list[MemoryRecall]:
        recalls: list[MemoryRecall] = []
        for p in await self.available_providers():
            try:
                batch = await p.prefetch(
                    query,
                    user_id=user_id,
                    bank_id=bank_id,
                    limit=limit_per_provider,
                )
                recalls.extend(batch)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "memory provider %s prefetch failed: %s", p.name, exc,
                )
        return recalls

    async def sync_turn(
        self,
        user_message: str,
        assistant_message: str,
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        for p in await self.available_providers():
            try:
                await p.sync_turn(
                    user_message, assistant_message,
                    user_id=user_id, bank_id=bank_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "memory provider %s sync_turn failed: %s", p.name, exc,
                )

    async def on_pre_compress(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> list[str]:
        """Fan-out pre-compress. Returns the list of non-empty snippets.

        Snippets come from providers that chose to emit a post-compact
        digest; providers that only persist verbatim data return ``None``
        and contribute nothing to the snippet list.
        """
        snippets: list[str] = []
        for p in await self.available_providers():
            try:
                snippet = await p.on_pre_compress(
                    messages, user_id=user_id, bank_id=bank_id,
                )
                if snippet:
                    snippets.append(snippet)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "memory provider %s on_pre_compress failed: %s",
                    p.name, exc,
                )
        return snippets

    async def on_session_end(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        for p in await self.available_providers():
            try:
                await p.on_session_end(
                    messages, user_id=user_id, bank_id=bank_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "memory provider %s on_session_end failed: %s",
                    p.name, exc,
                )

    def system_prompt_blocks(self) -> list[str]:
        """Return the list of static system-prompt blocks the providers inject."""
        blocks: list[str] = []
        for p in self._providers:
            block = p.system_prompt_block()
            if block:
                blocks.append(block)
        return blocks


# ---------------------------------------------------------------------------
# Concrete: FusionProvider — wraps the existing FusionMemoryEngine
# ---------------------------------------------------------------------------

class FusionProvider(MemoryProvider):
    """MemoryProvider that delegates to a :class:`FusionMemoryEngine`.

    Fusion is the matrix-canonical unified Hindsight + MemPalace runtime
    (see ``memory_fusion/README.md``). This provider is a thin adapter so
    the new ABC-driven callers can talk to the engine uniformly with
    Hindsight and MemPalace providers (which can be added as additional
    concrete subclasses later).

    The provider is defensive by design: every call catches engine
    exceptions and logs rather than re-raising. A broken memory path must
    not break the agent loop.
    """

    def __init__(self, engine: Any, *, system_block: str | None = None) -> None:
        self._engine = engine
        self._system_block = system_block

    @property
    def name(self) -> str:
        return "fusion"

    async def is_available(self) -> bool:
        return self._engine is not None

    async def prefetch(
        self,
        query: str,
        *,
        user_id: str,
        bank_id: str,
        limit: int = 5,
    ) -> list[MemoryRecall]:
        if self._engine is None:
            return []
        # FusionMemoryEngine exposes `recall` methods — use best-effort lookup
        # so different engine versions remain compatible.
        recall_method = getattr(self._engine, "recall", None)
        if recall_method is None:
            return []
        try:
            items = await recall_method(
                bank_id=bank_id,
                query=query,
                n_results=limit,
                request_context=self._request_context(),
            )
        except TypeError:
            # Test doubles and older engine variants may expose a simpler
            # recall(query, *, bank_id, limit) shape.
            try:
                items = await recall_method(query, bank_id=bank_id, limit=limit)
            except Exception as exc:  # noqa: BLE001
                logger.debug("fusion recall (compat) failed: %s", exc)
                return []
        except Exception as exc:  # noqa: BLE001
            logger.debug("fusion recall failed: %s", exc)
            return []

        recalls: list[MemoryRecall] = []
        for raw in items or []:
            if isinstance(raw, dict):
                content = str(raw.get("content") or raw.get("text") or "")
                source_ref = str(raw.get("source_ref") or raw.get("ref") or "")
                confidence = float(raw.get("confidence") or raw.get("score") or 0.0)
                metadata = raw.get("metadata") or {}
            else:
                content = str(getattr(raw, "content", "") or getattr(raw, "text", "") or "")
                source_ref = str(getattr(raw, "source_ref", "") or getattr(raw, "ref", "") or "")
                confidence = float(
                    getattr(raw, "confidence", None) or getattr(raw, "score", None) or 0.0
                )
                metadata = getattr(raw, "metadata", {}) or {}
            if not content:
                continue
            recalls.append(MemoryRecall(
                provider=self.name,
                content=content,
                source_ref=source_ref,
                confidence=confidence,
                metadata=metadata if isinstance(metadata, dict) else {},
            ))
        return recalls

    async def sync_turn(
        self,
        user_message: str,
        assistant_message: str,
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        if self._engine is None:
            return
        retain_batch = getattr(self._engine, "retain_batch_async", None)
        if retain_batch is not None:
            content = f"User: {user_message}\nAssistant: {assistant_message}".strip()
            if not content:
                return
            try:
                await retain_batch(
                    bank_id=bank_id,
                    contents=[
                        self._content_item(
                            content,
                            source="sync_turn",
                            user_id=user_id,
                            bank_id=bank_id,
                        )
                    ],
                    request_context=self._request_context(),
                    document_tags=["agent_turn", "sync_turn"],
                    consumer="agent_writer",
                    operation_context={
                        "user_id": user_id,
                        "agent_id": "agent",
                        "actor_role": "assistant",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("fusion retain_batch_async failed: %s", exc)
            return

        retain = getattr(self._engine, "retain", None)
        if retain is None:
            return
        try:
            await retain(
                user_message=user_message,
                assistant_message=assistant_message,
                bank_id=bank_id,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("fusion retain failed: %s", exc)

    async def on_pre_compress(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> str | None:
        """Archive visible messages before context is compacted or compressed."""
        if self._engine is None or not messages:
            return None
        retain_batch = getattr(self._engine, "retain_batch_async", None)
        if retain_batch is None:
            return None

        content = self._format_messages(messages)
        if not content:
            return None
        try:
            await retain_batch(
                bank_id=bank_id,
                contents=[
                    self._content_item(
                        content,
                        source="pre_compress",
                        user_id=user_id,
                        bank_id=bank_id,
                        metadata={
                            "message_count": str(len(messages)),
                            "archive_boundary": "pre_compaction_or_compression",
                        },
                    )
                ],
                request_context=self._request_context(),
                document_tags=["pre_compress", "verbatim_archive"],
                route="verbatim",
                defer_embedding=True,
                consumer="agent_context_archive",
                operation_context={
                    "user_id": user_id,
                    "agent_id": "agent",
                    "actor_role": "assistant",
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("fusion pre-compress archive failed: %s", exc)
            return None
        return f"Archived {len(messages)} messages before context reduction."

    async def on_session_end(
        self,
        messages: list[dict[str, Any]],
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        await self.on_pre_compress(messages, user_id=user_id, bank_id=bank_id)

    @staticmethod
    def _request_context() -> Any:
        try:
            from hindsight_api.models import RequestContext

            return RequestContext()
        except Exception:  # noqa: BLE001
            return {}

    @staticmethod
    def _format_messages(messages: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for msg in messages:
            role = str(msg.get("role") or "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(part) for part in content)
            text = str(content or "").strip()
            if text:
                lines.append(f"[{role}] {text}")
        return "\n".join(lines).strip()

    @staticmethod
    def _content_item(
        content: str,
        *,
        source: str,
        user_id: str,
        bank_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        digest = sha256(
            f"{bank_id}:{user_id}:{source}:{content}".encode()
        ).hexdigest()[:16]
        return {
            "content": content,
            "context": f"{source}:user:{user_id}",
            "event_date": now,
            "document_id": f"{bank_id}:{source}:{digest}",
            "tags": [source, "agent_memory"],
            "metadata": {
                "user_id": user_id,
                "bank_id": bank_id,
                "source": source,
                "source_type": "conversation",
                "evidence_kind": "verbatim",
                "artifact_type": "conversation_turn"
                if source == "sync_turn"
                else "conversation_archive",
                "source_ref": f"{bank_id}:{source}:{digest}",
                "filed_at": now.isoformat(),
                **dict(metadata or {}),
            },
        }

    def system_prompt_block(self) -> str | None:
        return self._system_block


async def auto_fusion_provider(*, system_block: str | None = None) -> FusionProvider | None:
    """Build a :class:`FusionProvider` over the env-configured engine.

    Returns ``None`` when env gates the memory provider to ``disabled`` or
    the engine fails to initialise — callers should fall through to an
    empty :class:`MemoryManager` in that case.
    """
    try:
        from memory_fusion.engine import get_memory_engine

        engine = await get_memory_engine()
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto_fusion_provider engine init failed: %s", exc)
        return None
    if engine is None:
        return None
    return FusionProvider(engine, system_block=system_block)


# ---------------------------------------------------------------------------
# Module-level accessor (mirror of get_credential_pool in resilience/)
# ---------------------------------------------------------------------------

_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager | None:
    """Return the process-wide :class:`MemoryManager` singleton.

    Unlike :func:`get_credential_pool`, this accessor can legitimately
    return ``None`` — it is seeded by
    ``agent.resilience.init_stack._init_agent_resilience_stack`` only
    after ``auto_fusion_provider()`` succeeds. Callers must handle the
    ``None`` case (fall back to legacy hindsight-recall path).
    """
    return _manager


def set_memory_manager(manager: MemoryManager | None) -> None:
    """Seed or clear the singleton. Called exclusively by init_stack."""
    global _manager
    _manager = manager


def reset_memory_manager() -> None:
    """Testing helper — drop the singleton so the next seed takes effect."""
    global _manager
    _manager = None
