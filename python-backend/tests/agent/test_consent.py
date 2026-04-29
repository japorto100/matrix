from __future__ import annotations

import pytest

from agent.consent import check_consent
from agent.consent.config import (
    ConsentPolicyConfig,
    RateLimitsConfig,
    ToolConsentConfig,
    get_consent_config,
    reset_consent_config,
)
from agent.consent.provider import ConsentDecision, ConsentLevel
from agent.consent.rate_limiter import RateLimitResult


@pytest.mark.asyncio
async def test_check_consent_short_circuits_on_rate_limit(monkeypatch):
    async def _audit_log(**kwargs):
        _audit_log.calls.append(kwargs)

    _audit_log.calls = []

    def _limiter() -> object:
        class _FakeLimiter:
            def check(self, thread_id: str, tool_name: str) -> RateLimitResult:
                return RateLimitResult(allowed=False, reason="session limit reached")

        return _FakeLimiter()

    monkeypatch.setattr(
        "agent.consent.get_rate_limiter",
        lambda: _limiter(),
    )
    monkeypatch.setattr(
        "agent.consent.get_consent_config",
        lambda: ConsentPolicyConfig(rate_limits=RateLimitsConfig(max_tool_calls_total=1)),
    )
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent._get_provider",
        lambda: (_ for _ in ()).throw(AssertionError("provider must not run")),
    )

    decision = await check_consent(
        tool_name="sandbox_execute",
        tool_input={},
        thread_id="thread-rate-limit",
        user_role="analyst",
    )

    assert decision.needs_consent is True
    assert decision.level == ConsentLevel.DENY
    assert decision.policy_id == "rate_limit"
    assert decision.metadata["rate_limited"] is True
    assert _audit_log.calls[0]["action"].value == "rate_limit_hit"


@pytest.mark.asyncio
async def test_check_consent_respects_session_allow_cache(monkeypatch):
    async def _audit_log(**_kwargs) -> None:
        return None

    class _FakeCache:
        def get(self, _thread_id: str, _tool_name: str) -> str:
            return "allow"

        def grant(self, *_: object, **__: object) -> None:  # pragma: no cover
            raise AssertionError("grant must not be called on allow cache hit")

        def deny(self, *_: object, **__: object) -> None:  # pragma: no cover
            raise AssertionError("deny must not be called on allow cache hit")

        def revoke(self, *_: object, **__: object) -> None:  # pragma: no cover
            raise AssertionError("revoke must not be called on allow cache hit")

        def clear(self) -> None:  # pragma: no cover
            raise AssertionError("clear must not be called on allow cache hit")

    class _FakeLimiter:
        def check(self, _thread_id: str, _tool_name: str) -> RateLimitResult:
            return RateLimitResult(allowed=True)

    monkeypatch.setattr("agent.consent.get_consent_cache", lambda: _FakeCache())
    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: _FakeLimiter())
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent._get_provider",
        lambda: (_ for _ in ()).throw(
            AssertionError("provider must not run on session cache hit")
        ),
    )

    decision = await check_consent(
        tool_name="sandbox_execute",
        tool_input={},
        thread_id="thread-cache-allow",
        user_role="analyst",
    )

    assert decision.needs_consent is False
    assert decision.policy_id == "cache:session_allow"
    assert decision.metadata == {"cached": True}


@pytest.mark.asyncio
async def test_check_consent_respects_session_deny_cache(monkeypatch):
    async def _audit_log(**_kwargs) -> None:
        return None

    class _FakeCache:
        def get(self, _thread_id: str, _tool_name: str) -> str:
            return "deny"

        def grant(self, *_: object, **__: object) -> None:  # pragma: no cover
            raise AssertionError("grant must not be called on deny cache hit")

        def deny(self, *_: object, **__: object) -> None:  # pragma: no cover
            raise AssertionError("deny must not be called on deny cache hit")

        def revoke(self, *_: object, **__: object) -> None:  # pragma: no cover
            raise AssertionError("revoke must not be called on deny cache hit")

        def clear(self) -> None:  # pragma: no cover
            raise AssertionError("clear must not be called on deny cache hit")

    class _FakeLimiter:
        def check(self, _thread_id: str, _tool_name: str) -> RateLimitResult:
            return RateLimitResult(allowed=True)

    monkeypatch.setattr("agent.consent.get_consent_cache", lambda: _FakeCache())
    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: _FakeLimiter())
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent._get_provider",
        lambda: (_ for _ in ()).throw(
            AssertionError("provider must not run on session cache hit")
        ),
    )

    decision = await check_consent(
        tool_name="sandbox_execute",
        tool_input={},
        thread_id="thread-cache-deny",
        user_role="analyst",
    )

    assert decision.needs_consent is True
    assert decision.level == ConsentLevel.DENY
    assert decision.policy_id == "cache:session_deny"
    assert decision.metadata["cached"] is True
    assert decision.metadata["session_denied"] is True


@pytest.mark.asyncio
async def test_check_consent_preserves_grace_warning_metadata(monkeypatch):
    class _Provider:
        async def aevaluate(self, _request):
            return ConsentDecision(needs_consent=False, policy_id="yaml:default")

    provider = _Provider()

    class _FakeLimiter:
        def check(self, _thread_id: str, _tool_name: str) -> RateLimitResult:
            return RateLimitResult(
                allowed=True,
                reason="Warning: 1 iteration remaining before hard stop",
                is_grace_warning=True,
            )

    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: _FakeLimiter())
    monkeypatch.setattr(
        "agent.consent.get_consent_config",
        lambda: ConsentPolicyConfig(
            rate_limits=RateLimitsConfig(
                max_tool_calls_total=10,
                max_iterations=10,
            )
        ),
    )
    monkeypatch.setattr("agent.consent._get_provider", lambda: provider)
    monkeypatch.setattr("agent.consent.audit_log", lambda **kwargs: None)

    decision = await check_consent(
        tool_name="get_portfolio_summary",
        tool_input={},
        thread_id="thread-grace",
        user_role="viewer",
    )

    assert decision.needs_consent is False
    assert decision.metadata["grace_warning"] is True
    assert decision.metadata["grace_warning_reason"] == (
        "Warning: 1 iteration remaining before hard stop"
    )


@pytest.mark.asyncio
async def test_check_consent_enforces_per_tool_rate_limit(monkeypatch):
    async def _audit_log(**_kwargs) -> None:
        return None

    class _Provider:
        async def aevaluate(self, _request):
            return ConsentDecision(needs_consent=False, policy_id="yaml:default")

    from agent.consent.rate_limiter import SessionRateLimiter

    limiter = SessionRateLimiter()
    config = ConsentPolicyConfig(
        rate_limits=RateLimitsConfig(
            per_tool={"file_analyze": {"max_calls": 1}},
            max_tool_calls_total=50,
        )
    )

    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.rate_limiter.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.rate_limiter.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent._get_provider", lambda: _Provider())
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)

    decision = await check_consent(
        tool_name="file_analyze",
        tool_input={},
        thread_id="thread-tool-limit",
        user_role="analyst",
    )
    assert decision.needs_consent is False
    assert decision.policy_id == "yaml:default"

    limiter.record_tool_call("thread-tool-limit", "file_analyze")

    decision = await check_consent(
        tool_name="file_analyze",
        tool_input={},
        thread_id="thread-tool-limit",
        user_role="analyst",
    )
    assert decision.needs_consent is True
    assert decision.level == ConsentLevel.DENY
    assert decision.reason == "Tool 'file_analyze' call limit reached (1)"


@pytest.mark.asyncio
async def test_check_consent_denies_insufficient_user_role(monkeypatch):
    async def _audit_log(**_kwargs) -> None:
        return None

    config = ConsentPolicyConfig(
        tools={
            "place_order": ToolConsentConfig(
                level=ConsentLevel.CONFIRM,
                min_role="trader",
            )
        }
    )

    from agent.consent.rate_limiter import SessionRateLimiter

    limiter = SessionRateLimiter()
    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.rate_limiter.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.provider.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.rate_limiter.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)

    decision = await check_consent(
        tool_name="place_order",
        tool_input={},
        thread_id="thread-role",
        user_role="viewer",
    )

    assert decision.needs_consent is True
    assert decision.level == ConsentLevel.DENY
    assert decision.reason == "Tool 'place_order' requires role 'trader', user has 'viewer'"


@pytest.mark.asyncio
async def test_check_consent_denies_sandbox_browser_for_viewer(monkeypatch):
    async def _audit_log(**_kwargs) -> None:
        return None

    config = ConsentPolicyConfig(
        tools={
            "sandbox_browser": ToolConsentConfig(
                level=ConsentLevel.CONFIRM,
                min_role="analyst",
            )
        }
    )

    from agent.consent.rate_limiter import SessionRateLimiter

    limiter = SessionRateLimiter()
    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.rate_limiter.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.provider.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.rate_limiter.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)

    decision = await check_consent(
        tool_name="sandbox_browser",
        tool_input={},
        thread_id="thread-role-browser",
        user_role="viewer",
    )

    assert decision.needs_consent is True
    assert decision.level == ConsentLevel.DENY
    assert decision.reason == (
        "Tool 'sandbox_browser' requires role 'analyst', user has 'viewer'"
    )


@pytest.mark.asyncio
async def test_check_consent_allows_sandbox_browser_for_analyst(monkeypatch):
    async def _audit_log(**_kwargs) -> None:
        return None

    config = ConsentPolicyConfig(
        tools={
            "sandbox_browser": ToolConsentConfig(
                level=ConsentLevel.CONFIRM,
                min_role="analyst",
            )
        }
    )

    from agent.consent.rate_limiter import SessionRateLimiter

    limiter = SessionRateLimiter()
    monkeypatch.setattr("agent.consent.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.rate_limiter.get_rate_limiter", lambda: limiter)
    monkeypatch.setattr("agent.consent.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.provider.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.rate_limiter.get_consent_config", lambda: config)
    monkeypatch.setattr("agent.consent.audit_log", _audit_log)

    decision = await check_consent(
        tool_name="sandbox_browser",
        tool_input={},
        thread_id="thread-role-browser-ok",
        user_role="analyst",
    )

    assert decision.needs_consent is True
    assert decision.level == ConsentLevel.CONFIRM
    assert decision.policy_id == "yaml:tool:sandbox_browser"


def test_default_consent_policy_marks_sandbox_tools_confirm_and_analyst_only():
    reset_consent_config()
    config = get_consent_config()

    execute_cfg = config.tools["sandbox_execute"]
    browser_cfg = config.tools["sandbox_browser"]

    assert execute_cfg.level == ConsentLevel.CONFIRM
    assert execute_cfg.min_role == "analyst"
    assert execute_cfg.allow_session_cache is False
    assert browser_cfg.level == ConsentLevel.CONFIRM
    assert browser_cfg.min_role == "analyst"
    assert browser_cfg.allow_session_cache is False

    assert config.rate_limits.per_tool["sandbox_execute"].max_calls == 5
    assert config.rate_limits.per_tool["sandbox_browser"].max_calls == 3
