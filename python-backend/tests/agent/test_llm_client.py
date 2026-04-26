from __future__ import annotations

from agent import llm_client


def test_litellm_client_timeout_default(monkeypatch):
    monkeypatch.delenv("AGENT_LLM_TIMEOUT_S", raising=False)
    llm_client.get_litellm_client.cache_clear()

    client = llm_client.get_litellm_client()

    assert client.timeout == 45.0


def test_litellm_client_timeout_env_clamps_low_values(monkeypatch):
    monkeypatch.setenv("AGENT_LLM_TIMEOUT_S", "1")
    llm_client.get_litellm_client.cache_clear()

    client = llm_client.get_litellm_client()

    assert client.timeout == 5.0
