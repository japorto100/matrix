"""Tests for agent.resilience.credential_pool — exec-hermes §4.4.

ABC contract, SingleKey impl semantics, recovery-strategy dispatcher.
"""
from __future__ import annotations

import time

import pytest
from litellm.exceptions import (
    AuthenticationError,
    BadRequestError,
    BudgetExceededError,
    ContextWindowExceededError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from agent.resilience import credential_pool as cp_mod
from agent.resilience.credential_pool import (
    BILLING_COOLDOWN_SECONDS,
    RATE_LIMIT_COOLDOWN_SECONDS,
    SERVER_ERROR_COOLDOWN_SECONDS,
    Credential,
    CredentialPool,
    CredentialStatus,
    SingleKeyCredentialPool,
    apply_recovery,
    get_credential_pool,
    reset_credential_pool,
)
from agent.resilience.error_classifier import classify_error

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_credential_pool()
    yield
    reset_credential_pool()


def _make_get_key(key: str | None):
    async def _get(user_id: str, provider: str) -> str | None:
        return key
    return _get


def _make_pool(key: str | None = "sk-test-abc123") -> SingleKeyCredentialPool:
    return SingleKeyCredentialPool(get_key_fn=_make_get_key(key))


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------

def test_credential_pool_is_abstract():
    with pytest.raises(TypeError):
        CredentialPool()  # type: ignore[abstract]


def test_subclass_must_implement_all_abstract_methods():
    class _Partial(CredentialPool):
        async def acquire(self, user_id, provider):
            return None

    with pytest.raises(TypeError):
        _Partial()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Credential dataclass
# ---------------------------------------------------------------------------

def test_credential_is_usable_ok_status_no_exhaustion():
    cred = Credential(provider="openai", user_id="u1", key_id="abc", api_key="sk-")
    assert cred.is_usable is True


def test_credential_is_not_usable_when_status_auth_failed():
    cred = Credential(
        provider="openai", user_id="u1", key_id="abc", api_key="sk-",
        status=CredentialStatus.auth_failed,
    )
    assert cred.is_usable is False


def test_credential_is_not_usable_while_exhausted():
    cred = Credential(
        provider="openai", user_id="u1", key_id="abc", api_key="sk-",
        exhausted_until=time.time() + 60,
    )
    assert cred.is_usable is False


def test_credential_is_usable_after_exhaustion_ttl_expired():
    cred = Credential(
        provider="openai", user_id="u1", key_id="abc", api_key="sk-",
        exhausted_until=time.time() - 1,
    )
    assert cred.is_usable is True


# ---------------------------------------------------------------------------
# SingleKeyCredentialPool — acquire / mark_* semantics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_single_key_pool_acquire_returns_credential():
    pool = _make_pool("sk-abc123")
    cred = await pool.acquire("u1", "openai")
    assert cred is not None
    assert cred.user_id == "u1"
    assert cred.provider == "openai"
    assert cred.api_key == "sk-abc123"
    # key_id is a 16-char hash prefix — opaque identifier.
    assert len(cred.key_id) == 16
    assert cred.status is CredentialStatus.ok


@pytest.mark.asyncio
async def test_single_key_pool_acquire_returns_none_when_no_key():
    pool = _make_pool(None)
    cred = await pool.acquire("u1", "openai")
    assert cred is None


@pytest.mark.asyncio
async def test_mark_exhausted_blocks_acquire_until_ttl_expires(monkeypatch):
    pool = _make_pool("sk-abc")
    cred = await pool.acquire("u1", "openai")
    await pool.mark_exhausted(cred, reset_seconds=60)

    # Next acquire returns None — cooldown active.
    assert await pool.acquire("u1", "openai") is None

    # Simulate time passing past the TTL.
    fake_now = time.time() + 120
    monkeypatch.setattr(time, "time", lambda: fake_now)
    cred2 = await pool.acquire("u1", "openai")
    assert cred2 is not None


@pytest.mark.asyncio
async def test_mark_auth_failed_blocks_acquire_indefinitely():
    pool = _make_pool("sk-bad-key")
    cred = await pool.acquire("u1", "openai")
    await pool.mark_auth_failed(cred)
    # Even with no TTL advance, auth-fail blocks the key.
    assert await pool.acquire("u1", "openai") is None


@pytest.mark.asyncio
async def test_mark_success_clears_exhaustion():
    pool = _make_pool("sk-ok")
    cred = await pool.acquire("u1", "openai")
    await pool.mark_exhausted(cred, reset_seconds=3600)
    assert await pool.acquire("u1", "openai") is None

    await pool.mark_success(cred)
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_mark_success_clears_auth_failed():
    pool = _make_pool("sk-ok")
    cred = await pool.acquire("u1", "openai")
    await pool.mark_auth_failed(cred)
    await pool.mark_success(cred)
    # After recovery, key is usable again.
    fresh = await pool.acquire("u1", "openai")
    assert fresh is not None


@pytest.mark.asyncio
async def test_replacing_underlying_key_resets_state():
    """Scenario: user uploads a new key after the old one was marked
    auth_failed. The pool must NOT keep blocking on the new key."""
    old_key = "sk-old-invalid"
    new_key = "sk-fresh-valid"

    state = {"current": old_key}

    async def _get(user_id: str, provider: str) -> str | None:
        return state["current"]

    pool = SingleKeyCredentialPool(get_key_fn=_get)
    old_cred = await pool.acquire("u1", "openai")
    assert old_cred is not None
    await pool.mark_auth_failed(old_cred)
    # While the key is unchanged, acquire returns None.
    assert await pool.acquire("u1", "openai") is None

    # User uploads a new key.
    state["current"] = new_key
    new_cred = await pool.acquire("u1", "openai")
    assert new_cred is not None
    # Different key_id — the hash changed, so the pool treats it as fresh.
    assert new_cred.api_key == new_key
    assert new_cred.key_id != old_cred.key_id
    assert new_cred.status is CredentialStatus.ok


@pytest.mark.asyncio
async def test_per_user_isolation():
    """Alice's exhausted key does not block Bob's acquire on the same provider."""
    pool = _make_pool("sk-test")
    alice = await pool.acquire("alice", "openai")
    await pool.mark_exhausted(alice, reset_seconds=3600)
    # Bob is unaffected.
    bob = await pool.acquire("bob", "openai")
    assert bob is not None


@pytest.mark.asyncio
async def test_per_provider_isolation():
    pool = _make_pool("sk-test")
    oai = await pool.acquire("u1", "openai")
    await pool.mark_exhausted(oai, reset_seconds=3600)
    # Anthropic still acquirable for the same user.
    ant = await pool.acquire("u1", "anthropic")
    assert ant is not None


# ---------------------------------------------------------------------------
# apply_recovery — classification → pool-state mapping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_recovery_rate_limit_marks_exhausted_default_ttl(monkeypatch):
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = RateLimitError(message="slow down", llm_provider="openai", model="gpt-4")

    await apply_recovery(pool, cred, classify_error(exc))

    # TTL honoured — acquire returns None while cooldown is active.
    assert await pool.acquire("u1", "openai") is None
    # After the rate-limit-cooldown elapses, it should be back.
    fake_now = time.time() + RATE_LIMIT_COOLDOWN_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: fake_now)
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_apply_recovery_billing_marks_exhausted_long_ttl(monkeypatch):
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = BudgetExceededError(
        current_cost=100.0, max_budget=50.0, message="budget exhausted"
    )

    await apply_recovery(pool, cred, classify_error(exc))

    # Short TTL advance — still blocked (billing cooldown is 24h by default).
    fake_now_short = time.time() + RATE_LIMIT_COOLDOWN_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: fake_now_short)
    assert await pool.acquire("u1", "openai") is None
    # After billing-cooldown: usable again.
    fake_now_long = time.time() + BILLING_COOLDOWN_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: fake_now_long)
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_apply_recovery_auth_marks_auth_failed():
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = AuthenticationError(
        message="invalid key", llm_provider="openai", model="gpt-4",
    )

    await apply_recovery(pool, cred, classify_error(exc))
    # Auth-fail blocks regardless of TTL.
    assert await pool.acquire("u1", "openai") is None


@pytest.mark.asyncio
async def test_apply_recovery_overloaded_short_cooldown(monkeypatch):
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = ServiceUnavailableError(
        message="try later", llm_provider="openai", model="gpt-4",
    )

    await apply_recovery(pool, cred, classify_error(exc))
    fake_now = time.time() + SERVER_ERROR_COOLDOWN_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: fake_now)
    # Back to usable after the 5-min short cooldown.
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_apply_recovery_server_error_short_cooldown(monkeypatch):
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = InternalServerError(
        message="boom", llm_provider="openai", model="gpt-4",
    )

    await apply_recovery(pool, cred, classify_error(exc))
    fake_now = time.time() + SERVER_ERROR_COOLDOWN_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: fake_now)
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_apply_recovery_context_overflow_is_noop():
    """Context overflow isn't a credential problem — pool stays unchanged."""
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = ContextWindowExceededError(
        message="prompt too long", model="gpt-4", llm_provider="openai",
    )

    await apply_recovery(pool, cred, classify_error(exc))
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_apply_recovery_format_error_is_noop():
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = BadRequestError(
        message="tool_choice invalid", model="gpt-4", llm_provider="openai",
    )
    await apply_recovery(pool, cred, classify_error(exc))
    assert await pool.acquire("u1", "openai") is not None


@pytest.mark.asyncio
async def test_apply_recovery_timeout_is_noop():
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = Timeout(message="slow", model="gpt-4", llm_provider="openai")
    await apply_recovery(pool, cred, classify_error(exc))
    assert await pool.acquire("u1", "openai") is not None


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def test_get_credential_pool_returns_singleton():
    a = get_credential_pool()
    b = get_credential_pool()
    assert a is b


def test_reset_credential_pool_drops_singleton():
    first = get_credential_pool()
    reset_credential_pool()
    second = get_credential_pool()
    assert first is not second


def test_get_credential_pool_returns_single_key_impl_by_default():
    pool = get_credential_pool()
    assert isinstance(pool, SingleKeyCredentialPool)


# ---------------------------------------------------------------------------
# Custom cooldown overrides on apply_recovery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_recovery_honours_custom_cooldown(monkeypatch):
    pool = _make_pool("sk-x")
    cred = await pool.acquire("u1", "openai")
    exc = RateLimitError(message="x", llm_provider="openai", model="gpt-4")

    await apply_recovery(
        pool, cred, classify_error(exc), rate_limit_cooldown=5,
    )
    # Advance past the custom 5-second cooldown.
    fake_now = time.time() + 6
    monkeypatch.setattr(time, "time", lambda: fake_now)
    assert await pool.acquire("u1", "openai") is not None


# ---------------------------------------------------------------------------
# Module contract surface
# ---------------------------------------------------------------------------

def test_module_exports_expected_names():
    """Stable API surface — keep callers from importing private names."""
    assert set(cp_mod.__all__) >= {
        "CredentialStatus",
        "Credential",
        "CredentialPool",
        "SingleKeyCredentialPool",
        "apply_recovery",
        "get_credential_pool",
        "reset_credential_pool",
    }
