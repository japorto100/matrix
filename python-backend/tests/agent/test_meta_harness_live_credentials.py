from __future__ import annotations

from agent.app import AgentChatRequest, _meta_harness_api_key


def test_meta_harness_api_key_requires_run_id(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://example")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    req = AgentChatRequest(
        message="hi",
        model="openrouter/openrouter/auto",
        metaHarnessApiKey="test-openrouter-key",
    )

    assert _meta_harness_api_key(req, "openrouter/openrouter/auto") is None


def test_meta_harness_api_key_accepts_matching_env_key(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://example")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.delenv("META_HARNESS_ALLOW_ENV_CREDENTIALS", raising=False)
    req = AgentChatRequest(
        message="hi",
        model="openrouter/openrouter/auto",
        metaHarnessRunId="run-live",
        metaHarnessApiKey="test-openrouter-key",
    )

    assert _meta_harness_api_key(req, "openrouter/openrouter/auto") == (
        "test-openrouter-key"
    )


def test_meta_harness_api_key_rejects_mismatched_key(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://example")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    req = AgentChatRequest(
        message="hi",
        model="openrouter/openrouter/auto",
        metaHarnessRunId="run-live",
        metaHarnessApiKey="different",
    )

    assert _meta_harness_api_key(req, "openrouter/openrouter/auto") is None


def test_meta_harness_api_key_can_be_disabled(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://example")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("META_HARNESS_ALLOW_ENV_CREDENTIALS", "false")
    req = AgentChatRequest(
        message="hi",
        model="openrouter/openrouter/auto",
        metaHarnessRunId="run-live",
        metaHarnessApiKey="test-openrouter-key",
    )

    assert _meta_harness_api_key(req, "openrouter/openrouter/auto") is None
