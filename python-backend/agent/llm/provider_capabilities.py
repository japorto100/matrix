"""Provider-agnostic model capability snapshots for harness/live gates."""

from __future__ import annotations

import os
from typing import Any

from agent.llm.model_metadata import get_model_info, normalize_model_id

KNOWN_PROVIDER_PREFIXES = frozenset(
    {
        "anthropic",
        "azure",
        "bedrock",
        "cohere",
        "deepseek",
        "gemini",
        "google",
        "groq",
        "llamacpp",
        "mistral",
        "ollama",
        "openai",
        "openrouter",
        "vertex_ai",
        "vllm",
    }
)

LOCAL_MODEL_CAPABILITY_OVERRIDES: dict[str, dict[str, Any]] = {
    "bonsai-8b": {
        "provider": "llamacpp",
        "max_input_tokens": 65536,
        "max_output_tokens": None,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_reasoning": False,
        "supports_reasoning_effort": False,
        "supports_structured_output": False,
        "supports_vision": False,
        "prompt_cost_per_token": 0.0,
        "completion_cost_per_token": 0.0,
    },
    "llamacpp/bonsai-8b": {
        "max_input_tokens": 65536,
        "max_output_tokens": None,
        "supports_tools": True,
        "supports_streaming": True,
        "supports_reasoning": False,
        "supports_reasoning_effort": False,
        "supports_structured_output": False,
        "supports_vision": False,
        "prompt_cost_per_token": 0.0,
        "completion_cost_per_token": 0.0,
    }
}

FAKE_PROVIDER_MARKERS = frozenset(
    {
        "deterministic",
        "fake",
        "fixture",
        "llm-mock",
        "mock",
    }
)

CHAT_API_KEY_ENV_NAMES = (
    "AGENT_LLM_API_KEY",
    "LITELLM_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "DEEPSEEK_API_KEY",
    "COHERE_API_KEY",
)

EMBEDDING_API_KEY_ENV_NAMES = (
    "EMBEDDER_API_KEY",
    "MEMORY_EMBEDDING_API_KEY",
    *CHAT_API_KEY_ENV_NAMES,
)


def env_first(*names: str, default: str = "") -> str:
    """Return the first non-empty environment variable value."""

    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


def provider_label_from_model(model: str | None) -> str:
    """Infer the transport/provider label from a LiteLLM model id."""

    normalized = normalize_model_id(model)
    local_override = LOCAL_MODEL_CAPABILITY_OVERRIDES.get(normalized.lower())
    if local_override is not None and local_override.get("provider"):
        return str(local_override["provider"])
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return "litellm"
    prefix = parts[0].lower()
    if prefix in KNOWN_PROVIDER_PREFIXES or prefix in FAKE_PROVIDER_MARKERS:
        return prefix
    return "litellm"


def is_deterministic_fake_config(
    *,
    model: str | None = None,
    provider: str | None = None,
    base_url: str | None = None,
) -> bool:
    """True when config points at deterministic test/mock infrastructure."""

    values = {
        "model": str(model or "").strip().lower(),
        "provider": str(provider or "").strip().lower(),
        "base_url": str(base_url or "").strip().lower(),
    }
    provider_parts = {
        part
        for value in (values["model"], values["provider"])
        for part in value.replace(":", "/").split("/")
        if part
    }
    if provider_parts & FAKE_PROVIDER_MARKERS:
        return True
    return any(
        marker in values["base_url"]
        for marker in ("llm-mock", "127.0.0.1:8095", "localhost:8095")
    )


def model_capabilities(model: str | None) -> dict[str, Any]:
    """Return non-secret model capability data derived from LiteLLM metadata."""

    normalized = normalize_model_id(model)
    provider = provider_label_from_model(normalized)
    local_override = LOCAL_MODEL_CAPABILITY_OVERRIDES.get(normalized.lower())
    if local_override is not None:
        override = dict(local_override)
        provider = str(override.pop("provider", provider))
        return {
            "model": normalized,
            "provider": provider,
            "source": "local_override",
            "known_to_litellm": True,
            **override,
        }
    info = get_model_info(normalized) if normalized else None
    params = _string_list(
        (info or {}).get("supported_openai_params")
        or (info or {}).get("supported_parameters")
    )
    return {
        "model": normalized,
        "provider": provider,
        "source": "litellm_model_info" if info else "unknown",
        "known_to_litellm": bool(info),
        "max_input_tokens": _first_positive_int(
            info,
            "max_input_tokens",
            "max_tokens",
        ),
        "max_output_tokens": _first_positive_int(info, "max_output_tokens"),
        "supports_tools": bool(
            (info or {}).get("supports_function_calling")
            or (info or {}).get("supports_tools")
            or "tools" in params
        ),
        "supports_streaming": _tri_bool((info or {}).get("supports_streaming")),
        "supports_reasoning": bool(
            (info or {}).get("supports_reasoning")
            or "reasoning" in params
            or "reasoning_effort" in params
            or "thinking" in params
        ),
        "supports_reasoning_effort": "reasoning_effort" in params,
        "supports_structured_output": bool(
            (info or {}).get("supports_response_schema")
            or "response_format" in params
            or "json_schema" in params
        ),
        "supports_vision": bool((info or {}).get("supports_vision")),
        "prompt_cost_per_token": _number_or_none(
            (info or {}).get("input_cost_per_token")
        ),
        "completion_cost_per_token": _number_or_none(
            (info or {}).get("output_cost_per_token")
        ),
    }


def configured_provider_snapshot(model: str | None = None) -> dict[str, Any]:
    """Capture non-secret provider config for harness artifacts and gates."""

    agent_model = normalize_model_id(
        model or env_first("AGENT_DEFAULT_MODEL", "AGENT_DEFAULT_UTILITY_MODEL")
    )
    llm_provider = env_first(
        "AGENT_LLM_PROVIDER",
        default=provider_label_from_model(agent_model),
    )
    capabilities = model_capabilities(agent_model)
    if llm_provider == "litellm" and capabilities.get("provider") not in {
        "",
        "litellm",
    }:
        llm_provider = str(capabilities["provider"])
    litellm_base_url = os.environ.get("LITELLM_BASE_URL", "")
    embedding_provider = env_first("EMBEDDER_PROVIDER", "MEMORY_EMBEDDING_PROVIDER")
    embedding_model = env_first("EMBEDDER_MODEL", "MEMORY_EMBEDDING_MODEL")
    embedding_dimension = env_first(
        "EMBEDDER_DIMENSION",
        "EMBEDDING_DIMENSION",
        "MEMORY_EMBEDDING_DIMENSION",
    )
    return {
        "llm_provider": llm_provider,
        "agent_model": agent_model,
        "litellm_base_url": litellm_base_url,
        "agent_max_output_tokens": os.environ.get("AGENT_MAX_OUTPUT_TOKENS", ""),
        "chat_api_key_present": any(
            bool(os.environ.get(name)) for name in CHAT_API_KEY_ENV_NAMES
        ),
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dimension,
        "embedding_api_key_present": any(
            bool(os.environ.get(name)) for name in EMBEDDING_API_KEY_ENV_NAMES
        ),
        "capabilities": capabilities,
        "deterministic_fake": is_deterministic_fake_config(
            model=agent_model,
            provider=llm_provider,
            base_url=litellm_base_url,
        ),
        "secrets_redacted": True,
    }


def provider_live_gate(
    snapshot: dict[str, Any],
    *,
    allow_deterministic_fake: bool = False,
) -> dict[str, Any]:
    """Fail closed for regular live lanes that still point at mock providers."""

    failures: list[str] = []
    warnings: list[str] = []
    if not snapshot.get("agent_model"):
        failures.append("missing-agent-model")
    if snapshot.get("deterministic_fake") and not allow_deterministic_fake:
        failures.append("deterministic-fake-provider-not-allowed")
    if not snapshot.get("chat_api_key_present") and not snapshot.get(
        "litellm_base_url"
    ):
        warnings.append("no-chat-api-key-env-or-litellm-base-url")
    capabilities = snapshot.get("capabilities")
    if isinstance(capabilities, dict) and not capabilities.get("known_to_litellm"):
        warnings.append("model-capabilities-unknown-to-litellm")
    return {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "allow_deterministic_fake": allow_deterministic_fake,
    }


def _first_positive_int(info: dict[str, Any] | None, *keys: str) -> int | None:
    if not info:
        return None
    for key in keys:
        value = info.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return None


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _tri_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
