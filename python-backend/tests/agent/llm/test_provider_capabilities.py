from __future__ import annotations

from agent.llm import provider_capabilities as pc


def test_provider_label_from_model_prefers_transport_prefix():
    assert (
        pc.provider_label_from_model("openrouter/anthropic/claude-test") == "openrouter"
    )
    assert pc.provider_label_from_model("openai:gpt-4o") == "openai"
    assert pc.provider_label_from_model("llamacpp/bonsai-8b") == "llamacpp"
    assert pc.provider_label_from_model("bonsai-8b") == "llamacpp"
    assert pc.provider_label_from_model("plain-model") == "litellm"


def test_deterministic_fake_config_detects_mock_lane():
    assert pc.is_deterministic_fake_config(model="mock/provider")
    assert pc.is_deterministic_fake_config(base_url="http://127.0.0.1:8095")
    assert not pc.is_deterministic_fake_config(model="openrouter/test-model")


def test_provider_live_gate_blocks_fake_without_opt_in(monkeypatch):
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "mock/provider")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:8095")

    snapshot = pc.configured_provider_snapshot()
    gate = pc.provider_live_gate(snapshot)

    assert gate["passed"] is False
    assert "deterministic-fake-provider-not-allowed" in gate["failures"]
    assert (
        pc.provider_live_gate(snapshot, allow_deterministic_fake=True)["passed"] is True
    )


def test_model_capabilities_unknown_model_is_explicit():
    caps = pc.model_capabilities("provider/not-a-real-model-xyz")

    assert caps["source"] == "unknown"
    assert caps["known_to_litellm"] is False
    assert "supports_tools" in caps


def test_model_capabilities_local_bonsai_floor_is_explicit():
    caps = pc.model_capabilities("llamacpp/bonsai-8b")

    assert caps["source"] == "local_override"
    assert caps["provider"] == "llamacpp"
    assert caps["known_to_litellm"] is True
    assert caps["max_input_tokens"] == 65536
    assert caps["supports_tools"] is True
    assert caps["prompt_cost_per_token"] == 0.0

    alias_caps = pc.model_capabilities("bonsai-8b")
    assert alias_caps["source"] == "local_override"
    assert alias_caps["provider"] == "llamacpp"


def test_configured_provider_snapshot_uses_local_override_provider(monkeypatch):
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "bonsai-8b")
    monkeypatch.delenv("AGENT_LLM_PROVIDER", raising=False)

    snapshot = pc.configured_provider_snapshot()

    assert snapshot["llm_provider"] == "llamacpp"
    assert snapshot["capabilities"]["provider"] == "llamacpp"
