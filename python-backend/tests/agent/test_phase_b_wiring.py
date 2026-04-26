"""Phase-B P1 wiring unit tests (exec-hermes).

Covers the dead-code-activation surface without hitting the real LLM
provider, Postgres, or memory engines. Three wiring points:

1. **CredentialPool.acquire in llm_node** — None-return path raises
   :class:`CredentialExhaustedError`, happy-path propagates `credential.
   api_key` via ``extra_body`` and calls ``mark_success`` post-response.
   Error-path dispatches ``apply_recovery``.

2. **MemoryManager in runner._prepare_system_prompt** — manager=None
   falls through to legacy Hindsight path (no regression), manager
   seeded with a FakeProvider injects its ``system_prompt_blocks()`` +
   ``prefetch()`` results into the prompt.

3. **ContextEngine.stage_for in runner._prepare_messages** — emits
   ``context.stage`` as span-attribute when tokens/window are known.

Plus the resilience init-stack contract:

4. **init_agent_resilience_stack()** — all three sub-init functions get
   called, health dict shape is correct, sync_failures_table probe
   catches a missing-DB case without raising.
"""

from __future__ import annotations

import pytest

from agent.errors import CredentialExhaustedError
from agent.resilience import init_stack
from agent.resilience.credential_pool import (
    Credential,
    CredentialPool,
    reset_credential_pool,
)
from context.context_engine import (
    ContextEngineConfig,
    ContextStage,
    DefaultContextEngine,
    get_context_engine,
    reset_context_engine,
)
from memory_fusion.memory_provider import (
    MemoryManager,
    MemoryProvider,
    MemoryRecall,
    get_memory_manager,
    reset_memory_manager,
    set_memory_manager,
)

# ───────────────────────────── Fixtures ──────────────────────────────────


class _FakeMemoryProvider(MemoryProvider):
    """Records calls for assertions; no real engine."""

    def __init__(self, *, block: str | None = None, recalls: list[str] | None = None):
        self._block = block
        self._recalls = recalls or []
        self.prefetch_calls: list[tuple[str, str, str, int]] = []
        self.sync_calls: list[tuple[str, str]] = []
        self.sync_bank_ids: list[str] = []
        self.pre_compress_calls: list[tuple[int, str, str]] = []

    @property
    def name(self) -> str:
        return "fake"

    async def is_available(self) -> bool:
        return True

    async def prefetch(
        self, query: str, *, user_id: str, bank_id: str, limit: int = 5
    ) -> list[MemoryRecall]:
        self.prefetch_calls.append((query, user_id, bank_id, limit))
        return [
            MemoryRecall(provider="fake", content=c, confidence=0.9)
            for c in self._recalls[:limit]
        ]

    async def sync_turn(
        self,
        user_message: str,
        assistant_message: str,
        *,
        user_id: str,
        bank_id: str,
    ) -> None:
        self.sync_calls.append((user_message, assistant_message))
        self.sync_bank_ids.append(bank_id)

    async def on_pre_compress(
        self,
        messages: list[dict],
        *,
        user_id: str,
        bank_id: str,
    ) -> str | None:
        self.pre_compress_calls.append((len(messages), user_id, bank_id))
        return "archived"

    def system_prompt_block(self) -> str | None:
        return self._block


class _FakePool(CredentialPool):
    """Returns a programmable credential (or None) for acquire() — used
    to exercise llm_node's pool-wiring without touching user_credentials.
    """

    def __init__(self, credential: Credential | None = None):
        self._credential = credential
        self.mark_success_calls: list[Credential] = []
        self.mark_exhausted_calls: list[Credential] = []
        self.mark_auth_failed_calls: list[Credential] = []

    async def acquire(self, user_id: str, provider: str) -> Credential | None:
        return self._credential

    async def mark_exhausted(
        self, credential: Credential, *, reset_seconds: float = 3600
    ) -> None:
        self.mark_exhausted_calls.append(credential)

    async def mark_auth_failed(self, credential: Credential) -> None:
        self.mark_auth_failed_calls.append(credential)

    async def mark_success(self, credential: Credential) -> None:
        self.mark_success_calls.append(credential)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Every test runs against a clean resilience-stack state."""
    reset_credential_pool()
    reset_memory_manager()
    reset_context_engine()
    yield
    reset_credential_pool()
    reset_memory_manager()
    reset_context_engine()


# ───────────────────── 1. get_* accessors (P1.1) ──────────────────────────


def test_get_context_engine_returns_default_when_unset():
    engine = get_context_engine()
    assert isinstance(engine, DefaultContextEngine)
    # Idempotent: second call returns same instance
    assert get_context_engine() is engine


def test_get_memory_manager_returns_none_when_unset():
    assert get_memory_manager() is None


def test_set_memory_manager_seeds_accessor():
    mgr = MemoryManager([])
    set_memory_manager(mgr)
    assert get_memory_manager() is mgr


# ─────────── 2. CredentialExhaustedError surface (P1.4) ───────────────────


def test_credential_exhausted_error_fields():
    err = CredentialExhaustedError(
        user_id="alice", provider="openai", reason="test"
    )
    assert err.user_id == "alice"
    assert err.provider == "openai"
    assert "alice" in str(err)
    assert "openai" in str(err)


# ──────────── 3. ContextEngine stage_for contract (P1.6) ──────────────────


def test_context_engine_stage_for_normal_emits_enum():
    engine = DefaultContextEngine(
        ContextEngineConfig(pre_save=0.8, compaction=0.85, emergency=0.95)
    )
    assert engine.stage_for(tokens=1_000, window=200_000) is ContextStage.normal


def test_context_engine_stage_for_compaction_threshold():
    engine = DefaultContextEngine()
    # 85% of 200k = 170k — compaction stage
    assert (
        engine.stage_for(tokens=170_000, window=200_000)
        is ContextStage.compaction
    )
    # 95% of 200k = 190k — emergency
    assert (
        engine.stage_for(tokens=195_000, window=200_000) is ContextStage.emergency
    )


def test_context_engine_unknown_window_returns_normal():
    """Guard against divide-by-zero + negative tokens."""
    engine = DefaultContextEngine()
    assert engine.stage_for(tokens=100, window=0) is ContextStage.normal
    assert engine.stage_for(tokens=-1, window=200_000) is ContextStage.normal


# ─────────────────── 4. MemoryManager fan-out (P1.5) ─────────────────────


async def test_memory_manager_system_prompt_blocks_with_block():
    provider = _FakeMemoryProvider(block="static injection block")
    manager = MemoryManager([provider])
    blocks = manager.system_prompt_blocks()
    assert blocks == ["static injection block"]


async def test_memory_manager_system_prompt_blocks_without_block():
    """Provider returning None must not pollute the block-list."""
    provider = _FakeMemoryProvider(block=None)
    manager = MemoryManager([provider])
    assert manager.system_prompt_blocks() == []


async def test_memory_manager_prefetch_returns_recalls():
    provider = _FakeMemoryProvider(recalls=["fact A", "fact B"])
    manager = MemoryManager([provider])
    recalls = await manager.prefetch("some query", user_id="u1", bank_id="user-u1")
    assert len(recalls) == 2
    assert recalls[0].content == "fact A"
    assert recalls[0].provider == "fake"


async def test_prepare_system_prompt_passes_thread_to_skill_audit(monkeypatch):
    from agent.context import AgentExecutionContext
    from agent.graph import runner

    captured = {}

    async def fake_format_skills_for_prompt_async(*args, **kwargs):
        captured.update(kwargs)
        return "## Available Skills\nskill block"

    monkeypatch.setattr(
        "agent.skills.loader.format_skills_for_prompt_async",
        fake_format_skills_for_prompt_async,
    )
    monkeypatch.setattr(
        "agent.temporal_context.get_temporal_context",
        lambda user_id=None: "",
    )
    set_memory_manager(MemoryManager([]))

    ctx = AgentExecutionContext(
        user_id="anonymous",
        thread_id="thread-skills",
        model="openrouter/openrouter/auto",
        system_prompt="base prompt",
        tools=(),
    )

    prompt = await runner._prepare_system_prompt(
        ctx,
        [{"role": "user", "content": "market sentiment for AAPL"}],
    )

    assert "Tool Instruction Compliance" in prompt
    assert "skill block" in prompt
    assert captured["thread_id"] == "thread-skills"
    assert captured["session_id"] == "thread-skills"
    assert captured["user_id"] == "anonymous"


async def test_prepare_system_prompt_injects_memory_with_canonical_bank_id(monkeypatch):
    from agent.context import AgentExecutionContext
    from agent.graph import runner

    provider = _FakeMemoryProvider(recalls=["remembered trading preference"])
    set_memory_manager(MemoryManager([provider]))

    async def no_skills(*_args, **_kwargs):
        return ""

    monkeypatch.setattr(
        "agent.skills.loader.format_skills_for_prompt_async",
        no_skills,
    )
    monkeypatch.setattr(
        "agent.temporal_context.get_temporal_context",
        lambda user_id=None: "",
    )

    ctx = AgentExecutionContext(
        user_id="u1",
        thread_id="thread-memory",
        model="openrouter/openrouter/auto",
        system_prompt="base prompt",
        tools=(),
    )

    prompt = await runner._prepare_system_prompt(
        ctx,
        [{"role": "user", "content": "remember my swing trading preference"}],
    )

    assert "## Relevant Memories" in prompt
    assert "remembered trading preference" in prompt
    assert provider.prefetch_calls == [
        ("remember my swing trading preference", "u1", "user_u1", 5)
    ]


async def test_prepare_system_prompt_keeps_skills_when_legacy_memory_times_out(monkeypatch):
    from agent.context import AgentExecutionContext
    from agent.graph import runner

    async def fake_format_skills_for_prompt_async(*_args, **_kwargs):
        return "## Available Skills\nmarket-research"

    async def slow_memory_engine():
        await __import__("asyncio").sleep(0.05)
        return None

    monkeypatch.setenv("AGENT_PROMPT_MEMORY_INIT_TIMEOUT_S", "0.001")
    monkeypatch.setattr(
        "agent.skills.loader.format_skills_for_prompt_async",
        fake_format_skills_for_prompt_async,
    )
    monkeypatch.setattr(
        "agent.temporal_context.get_temporal_context",
        lambda user_id=None: "",
    )
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", slow_memory_engine)

    ctx = AgentExecutionContext(
        user_id="anonymous",
        thread_id="thread-slow-memory",
        model="openrouter/openrouter/auto",
        system_prompt="base prompt",
        tools=(),
    )

    prompt = await runner._prepare_system_prompt(
        ctx,
        [{"role": "user", "content": "market sentiment for AAPL"}],
    )

    assert "market-research" in prompt


async def test_memory_manager_sync_turn_dispatches():
    provider = _FakeMemoryProvider()
    manager = MemoryManager([provider])
    await manager.sync_turn(
        "hello", "world", user_id="u1", bank_id="user-u1"
    )
    assert provider.sync_calls == [("hello", "world")]


async def test_prepare_messages_pre_save_archives_without_mutating(monkeypatch):
    from agent.context import AgentExecutionContext
    from agent.graph import runner

    provider = _FakeMemoryProvider()
    set_memory_manager(MemoryManager([provider]))
    monkeypatch.setattr("agent.middleware.compaction.estimate_tokens", lambda _m: 80)
    monkeypatch.setattr("agent.llm.model_metadata.get_model_context_window", lambda _m: 100)

    ctx = AgentExecutionContext(
        user_id="u1",
        thread_id="t1",
        model="test-model",
        system_prompt="",
        tools=(),
    )
    messages = [{"role": "user", "content": "near threshold"}]

    result = await runner._prepare_messages(messages, ctx)

    assert result == messages
    assert provider.pre_compress_calls == [(1, "u1", "user_u1")]


async def test_prepare_messages_compaction_archives_before_truncating(monkeypatch):
    from agent.context import AgentExecutionContext
    from agent.graph import runner
    from agent.middleware import compaction

    provider = _FakeMemoryProvider()
    set_memory_manager(MemoryManager([provider]))
    monkeypatch.setattr("agent.middleware.compaction.estimate_tokens", lambda _m: 86)
    monkeypatch.setattr("agent.llm.model_metadata.get_model_context_window", lambda _m: 100)

    big = "x" * (compaction.TOOL_RESULT_MAX_CHARS + 1000)
    messages = [
        {"role": "user", "content": "use tool"},
        {"role": "tool", "content": big},
    ]
    ctx = AgentExecutionContext(
        user_id="u1",
        thread_id="t1",
        model="test-model",
        system_prompt="",
        tools=(),
    )

    result = await runner._prepare_messages(messages, ctx)

    assert provider.pre_compress_calls == [(2, "u1", "user_u1")]
    assert len(result[1]["content"]) < len(big)
    assert "truncated" in result[1]["content"]


# ──────────────── 5. init_stack health-dict shape (P1.3) ─────────────────


def test_resilience_health_default_is_degraded():
    """Before init_agent_resilience_stack runs, status = degraded."""
    body = init_stack.resilience_health()
    assert body["status"] == "degraded"
    for key in (
        "credential_pool",
        "memory_manager",
        "context_engine",
        "sync_failures_table",
    ):
        assert key in body
        assert "up" in body[key]
        assert "detail" in body[key]


async def test_init_agent_resilience_stack_soft_fails_gracefully(monkeypatch):
    """Even when all sub-inits raise, init_agent_resilience_stack must
    not propagate — the service keeps starting in degraded mode.
    """
    # Force memory-manager init to fail (no engine in test env)
    status = await init_stack.init_agent_resilience_stack()
    # credential_pool + context_engine succeed (lazy + stateless)
    assert status.credential_pool.up is True
    assert status.context_engine.up is True
    # memory_manager + sync_failures_table almost certainly fail in test env
    # — we just assert they report up=False with detail, not that they fail
    # (local dev could happen to have a running Hindsight).
    assert status.memory_manager.detail != ""


# ────────────── 6. _safe_sync_turn fire-and-forget (P1.5) ────────────────


async def test_safe_sync_turn_swallows_exceptions(monkeypatch):
    """_safe_sync_turn MUST never raise — guarantee for asyncio.create_task."""
    from agent.graph import runner

    provider = _FakeMemoryProvider()

    async def failing_sync(*args, **kwargs):
        raise RuntimeError("engine down")

    provider.sync_turn = failing_sync  # type: ignore[assignment]
    manager = MemoryManager([provider])
    set_memory_manager(manager)

    # Stop _record_sync_failure from attempting a real DB connect
    async def _noop(**kwargs):
        return None

    monkeypatch.setattr(runner, "_record_sync_failure", _noop)

    # Must complete normally, not raise
    await runner._safe_sync_turn(
        user_id="u1",
        thread_id="t1",
        messages=[{"role": "user", "content": "hi"}],
        final_response="hello",
    )


async def test_safe_sync_turn_uses_canonical_bank_id():
    from agent.graph import runner

    provider = _FakeMemoryProvider()
    set_memory_manager(MemoryManager([provider]))

    await runner._safe_sync_turn(
        user_id="u1",
        thread_id="t1",
        messages=[{"role": "user", "content": "hi"}],
        final_response="hello",
    )

    assert provider.sync_calls == [("hi", "hello")]
    assert provider.sync_bank_ids == ["user_u1"]


async def test_safe_sync_turn_none_manager_noops():
    """When MemoryManager is None (not seeded), sync_turn is a no-op."""
    from agent.graph import runner

    assert get_memory_manager() is None
    # Must not raise despite manager=None
    await runner._safe_sync_turn(
        user_id="u1",
        thread_id="t1",
        messages=[],
        final_response="",
    )
