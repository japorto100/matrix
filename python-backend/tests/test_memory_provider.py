"""Tests for memory_fusion.memory_provider — exec-hermes §3.2.

ABC contract, fan-out semantics, per-provider error isolation,
FusionProvider adapter behaviour over a stub engine.
"""
from __future__ import annotations

from typing import Any

import pytest

from memory_fusion.memory_provider import (
    FusionProvider,
    MemoryManager,
    MemoryProvider,
    MemoryRecall,
)

# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------

def test_abstract_cannot_instantiate():
    with pytest.raises(TypeError):
        MemoryProvider()  # type: ignore[abstract]


def test_subclass_must_implement_core_abstract_methods():
    class _Incomplete(MemoryProvider):
        @property
        def name(self) -> str:
            return "incomplete"

    with pytest.raises(TypeError):
        _Incomplete()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Fake providers for fan-out tests
# ---------------------------------------------------------------------------

class _RecordingProvider(MemoryProvider):
    """Records every call for assertions + configurable error injection."""

    def __init__(
        self,
        name: str,
        *,
        available: bool = True,
        prefetch_result: list[MemoryRecall] | None = None,
        pre_compress_snippet: str | None = None,
        raise_on: str | None = None,
        system_block: str | None = None,
    ) -> None:
        self._name = name
        self._available = available
        self._prefetch_result = prefetch_result or []
        self._pre_compress_snippet = pre_compress_snippet
        self._raise_on = raise_on
        self._system_block = system_block
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    async def is_available(self) -> bool:
        self.calls.append("is_available")
        if self._raise_on == "is_available":
            raise RuntimeError("is_available boom")
        return self._available

    async def prefetch(self, query, *, user_id, bank_id, limit=5):
        self.calls.append(f"prefetch:{query}:{user_id}:{bank_id}:{limit}")
        if self._raise_on == "prefetch":
            raise RuntimeError("prefetch boom")
        return list(self._prefetch_result)

    async def sync_turn(self, user_message, assistant_message, *, user_id, bank_id):
        self.calls.append(f"sync_turn:{user_id}:{bank_id}")
        if self._raise_on == "sync_turn":
            raise RuntimeError("sync_turn boom")

    async def on_pre_compress(self, messages, *, user_id, bank_id):
        self.calls.append(f"on_pre_compress:{user_id}:{bank_id}:{len(messages)}")
        if self._raise_on == "on_pre_compress":
            raise RuntimeError("on_pre_compress boom")
        return self._pre_compress_snippet

    async def on_session_end(self, messages, *, user_id, bank_id):
        self.calls.append(f"on_session_end:{user_id}:{bank_id}")
        if self._raise_on == "on_session_end":
            raise RuntimeError("on_session_end boom")

    def system_prompt_block(self) -> str | None:
        return self._system_block


# ---------------------------------------------------------------------------
# MemoryManager fan-out + isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manager_fan_out_prefetch_concatenates_recalls():
    p1 = _RecordingProvider("p1", prefetch_result=[
        MemoryRecall(provider="p1", content="a"),
    ])
    p2 = _RecordingProvider("p2", prefetch_result=[
        MemoryRecall(provider="p2", content="b"),
        MemoryRecall(provider="p2", content="c"),
    ])
    mgr = MemoryManager([p1, p2])
    result = await mgr.prefetch("q", user_id="u1", bank_id="b1")
    assert len(result) == 3
    assert {r.provider for r in result} == {"p1", "p2"}


@pytest.mark.asyncio
async def test_manager_skips_unavailable_providers():
    p_down = _RecordingProvider("down", available=False, prefetch_result=[
        MemoryRecall(provider="down", content="should not surface"),
    ])
    p_ok = _RecordingProvider("ok", prefetch_result=[
        MemoryRecall(provider="ok", content="yes"),
    ])
    mgr = MemoryManager([p_down, p_ok])
    result = await mgr.prefetch("q", user_id="u1", bank_id="b1")
    assert [r.provider for r in result] == ["ok"]
    assert "prefetch:q:u1:b1:5" not in p_down.calls  # never asked


@pytest.mark.asyncio
async def test_manager_isolates_per_provider_errors():
    """A crash in one provider must not starve the others."""
    p_crash = _RecordingProvider("crash", raise_on="prefetch")
    p_ok = _RecordingProvider("ok", prefetch_result=[
        MemoryRecall(provider="ok", content="still good"),
    ])
    mgr = MemoryManager([p_crash, p_ok])
    result = await mgr.prefetch("q", user_id="u1", bank_id="b1")
    assert [r.provider for r in result] == ["ok"]


@pytest.mark.asyncio
async def test_manager_is_available_error_skips_provider():
    """An exception in is_available disqualifies the provider."""
    p_bad = _RecordingProvider("bad", raise_on="is_available")
    p_ok = _RecordingProvider("ok", prefetch_result=[
        MemoryRecall(provider="ok", content="yes"),
    ])
    mgr = MemoryManager([p_bad, p_ok])
    result = await mgr.prefetch("q", user_id="u1", bank_id="b1")
    assert [r.provider for r in result] == ["ok"]


@pytest.mark.asyncio
async def test_manager_sync_turn_calls_every_available():
    p1 = _RecordingProvider("p1")
    p2 = _RecordingProvider("p2")
    mgr = MemoryManager([p1, p2])
    await mgr.sync_turn("hi", "hello", user_id="u1", bank_id="b1")
    assert any("sync_turn" in c for c in p1.calls)
    assert any("sync_turn" in c for c in p2.calls)


@pytest.mark.asyncio
async def test_manager_on_pre_compress_collects_non_empty_snippets():
    p1 = _RecordingProvider("p1", pre_compress_snippet="retained one")
    p2 = _RecordingProvider("p2", pre_compress_snippet=None)   # provider just persists, no snippet
    p3 = _RecordingProvider("p3", pre_compress_snippet="retained three")
    mgr = MemoryManager([p1, p2, p3])
    snippets = await mgr.on_pre_compress(
        [{"role": "user", "content": "x"}], user_id="u1", bank_id="b1",
    )
    assert snippets == ["retained one", "retained three"]


@pytest.mark.asyncio
async def test_manager_on_pre_compress_error_does_not_break_others():
    p_crash = _RecordingProvider("crash", raise_on="on_pre_compress")
    p_ok = _RecordingProvider("ok", pre_compress_snippet="still got this")
    mgr = MemoryManager([p_crash, p_ok])
    snippets = await mgr.on_pre_compress([], user_id="u1", bank_id="b1")
    assert snippets == ["still got this"]


def test_manager_system_prompt_blocks_aggregates_non_empty():
    p1 = _RecordingProvider("p1", system_block="block 1")
    p2 = _RecordingProvider("p2", system_block=None)
    p3 = _RecordingProvider("p3", system_block="block 3")
    mgr = MemoryManager([p1, p2, p3])
    assert mgr.system_prompt_blocks() == ["block 1", "block 3"]


def test_manager_providers_property_is_defensive_copy():
    p = _RecordingProvider("p1")
    mgr = MemoryManager([p])
    exposed = mgr.providers
    exposed.append(_RecordingProvider("hijack"))
    assert len(mgr.providers) == 1  # unaffected by external append


# ---------------------------------------------------------------------------
# FusionProvider adapter
# ---------------------------------------------------------------------------

class _StubFusionEngine:
    """Minimal stand-in for FusionMemoryEngine with a recall/retain surface."""

    def __init__(self, recall_items: list[dict[str, Any]] | None = None) -> None:
        self._recall_items = recall_items or []
        self.retain_calls: list[tuple[str, str, str, str]] = []
        self.retain_batch_calls: list[dict[str, Any]] = []

    async def recall(self, query, *, bank_id, limit=5):
        return list(self._recall_items)

    async def retain_batch_async(self, **kwargs) -> list[list[str]]:
        self.retain_batch_calls.append(kwargs)
        return [["unit-1"]]

    async def retain(
        self, *, user_message, assistant_message, bank_id, user_id,
    ) -> None:
        self.retain_calls.append(
            (user_message, assistant_message, bank_id, user_id),
        )


class _KeywordFusionEngine:
    async def recall(self, *, bank_id, query, n_results, request_context):
        return [
            type(
                "FusionHit",
                (),
                {
                    "text": f"{bank_id}:{query}",
                    "ref": "fusion-ref",
                    "score": 0.77,
                    "metadata": {"route": "fusion", "n_results": n_results},
                },
            )()
        ]


@pytest.mark.asyncio
async def test_fusion_provider_recall_shapes_to_memory_recall():
    engine = _StubFusionEngine(recall_items=[
        {"content": "one", "source_ref": "x#1", "confidence": 0.9},
        {"text": "two", "metadata": {"tag": "a"}},
        "not-a-dict-skipped",  # type: ignore[list-item]
    ])
    provider = FusionProvider(engine)
    recalls = await provider.prefetch(
        "q", user_id="u1", bank_id="b1", limit=5,
    )
    assert len(recalls) == 2
    assert recalls[0].content == "one"
    assert recalls[0].source_ref == "x#1"
    assert recalls[1].content == "two"  # picked up from .text fallback
    assert recalls[1].metadata == {"tag": "a"}


@pytest.mark.asyncio
async def test_fusion_provider_prefetch_supports_keyword_only_fusion_recall():
    provider = FusionProvider(_KeywordFusionEngine())
    recalls = await provider.prefetch("risk preference", user_id="u1", bank_id="b1")
    assert len(recalls) == 1
    assert recalls[0].content == "b1:risk preference"
    assert recalls[0].source_ref == "fusion-ref"
    assert recalls[0].confidence == 0.77
    assert recalls[0].metadata["route"] == "fusion"


@pytest.mark.asyncio
async def test_fusion_provider_sync_turn_calls_retain():
    engine = _StubFusionEngine()
    provider = FusionProvider(engine)
    await provider.sync_turn("hi", "hello", user_id="u1", bank_id="b1")
    assert engine.retain_batch_calls
    call = engine.retain_batch_calls[0]
    assert call["bank_id"] == "b1"
    assert call["consumer"] == "agent_writer"
    assert call["contents"][0]["content"] == "User: hi\nAssistant: hello"
    assert call["contents"][0]["metadata"]["source"] == "sync_turn"


@pytest.mark.asyncio
async def test_fusion_provider_is_available_true_with_engine():
    assert await FusionProvider(_StubFusionEngine()).is_available() is True


@pytest.mark.asyncio
async def test_fusion_provider_is_available_false_without_engine():
    assert await FusionProvider(None).is_available() is False


@pytest.mark.asyncio
async def test_fusion_provider_returns_empty_list_when_engine_none():
    provider = FusionProvider(None)
    assert await provider.prefetch("q", user_id="u1", bank_id="b1") == []


@pytest.mark.asyncio
async def test_fusion_provider_handles_engine_without_recall_method():
    """A future engine variant missing .recall must not crash the provider."""
    class _EngineNoRecall:
        pass

    provider = FusionProvider(_EngineNoRecall())
    assert await provider.prefetch("q", user_id="u1", bank_id="b1") == []


@pytest.mark.asyncio
async def test_fusion_provider_system_block_passes_through():
    engine = _StubFusionEngine()
    provider = FusionProvider(engine, system_block="inject me")
    assert provider.system_prompt_block() == "inject me"


@pytest.mark.asyncio
async def test_fusion_provider_default_pre_compress_returns_none():
    """FusionProvider archives pre-compress messages via the fusion engine."""
    engine = _StubFusionEngine()
    provider = FusionProvider(engine)
    result = await provider.on_pre_compress(
        [{"role": "user", "content": "important detail"}],
        user_id="u1",
        bank_id="b1",
    )
    assert result == "Archived 1 messages before context reduction."
    call = engine.retain_batch_calls[0]
    assert call["bank_id"] == "b1"
    assert call["consumer"] == "agent_context_archive"
    assert call["contents"][0]["metadata"]["source"] == "pre_compress"
    assert "important detail" in call["contents"][0]["content"]
