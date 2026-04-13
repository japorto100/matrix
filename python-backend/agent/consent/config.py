# Consent Config — exec-12 Phase 2.2 + 2.3
# Pydantic models + YAML loader + dynamic class import (deer-flow pattern).
# Single source of truth: consent_policy.yaml (ENV values are fallbacks).

from __future__ import annotations

import importlib
import logging
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_POLICY_PATH = Path(__file__).resolve().parent.parent / "consent_policy.yaml"


# ── Enums ──────────────────────────────────────────────────────────────────


class ConsentLevel(StrEnum):
    NONE = "none"  # No consent needed, auto-allow
    INFORM = "inform"  # Log but don't block
    CONFIRM = "confirm"  # Require explicit user consent
    DENY = "deny"  # Hard block, no way around it


class ConsentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Pydantic Models ───────────────────────────────────────────────────────


class ToolConsentConfig(BaseModel):
    level: ConsentLevel = ConsentLevel.NONE
    severity: ConsentSeverity = ConsentSeverity.MEDIUM
    reason: str = ""
    allow_session_cache: bool = True
    roles: list[str] = []  # Empty = applies to all roles. ["advisory"] = only advisory.
    min_role: str = ""  # Minimum user role required (viewer/analyst/trader/admin). Empty = no check.


# Role hierarchy level for min_role checks (matches tradeview-fusion proxy.ts)
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "analyst": 2,
    "trader": 3,
    "admin": 4,
}


def role_meets_minimum(user_role: str, min_role: str) -> bool:
    """Check if user_role meets the min_role requirement."""
    if not min_role:
        return True
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    min_level = ROLE_HIERARCHY.get(min_role, 0)
    return user_level >= min_level


class CategoryConsentConfig(BaseModel):
    level: ConsentLevel = ConsentLevel.NONE
    severity: ConsentSeverity = ConsentSeverity.MEDIUM


class ProviderConfig(BaseModel):
    use: str = "agent.consent.provider:YamlPolicyProvider"
    config: dict[str, Any] = {}


class PerToolRateLimit(BaseModel):
    max_calls: int = 0  # 0 = unlimited


class LoopDetectionConfig(BaseModel):
    warn_threshold: int = 3
    hard_limit: int = 5
    window_size: int = 20


class RateLimitsConfig(BaseModel):
    max_iterations: int = 0  # 0 = use ENV fallback
    max_tool_calls_total: int = 50
    max_tokens_per_session: int = 0  # 0 = unlimited
    tool_timeout_sec: float = 0  # 0 = use ENV fallback
    grace_iterations: int = 3
    loop_detection: LoopDetectionConfig = LoopDetectionConfig()
    per_tool: dict[str, PerToolRateLimit] = {}

    def get_max_iterations(self) -> int:
        if self.max_iterations > 0:
            return self.max_iterations
        return int(os.environ.get("AGENT_MAX_ITERATIONS", "10"))

    def get_tool_timeout(self) -> float:
        if self.tool_timeout_sec > 0:
            return self.tool_timeout_sec
        return float(os.environ.get("AGENT_TOOL_TIMEOUT_SEC", "30"))


class ConsentPolicyConfig(BaseModel):
    defaults: CategoryConsentConfig = CategoryConsentConfig()
    fail_closed: bool = True
    provider: ProviderConfig = ProviderConfig()
    tools: dict[str, ToolConsentConfig] = {}
    categories: dict[str, CategoryConsentConfig] = {}
    rate_limits: RateLimitsConfig = RateLimitsConfig()


# ── Singleton ──────────────────────────────────────────────────────────────

_config: ConsentPolicyConfig | None = None


def get_consent_config() -> ConsentPolicyConfig:
    """Get or load the singleton consent policy config."""
    global _config
    if _config is None:
        _config = _load_config()
    return _config


def reset_consent_config() -> None:
    """Reset config singleton (for testing)."""
    global _config
    _config = None


def _load_config() -> ConsentPolicyConfig:
    """Load consent policy from YAML file. Falls back to defaults."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed, using default consent policy")
        return ConsentPolicyConfig()

    if not _POLICY_PATH.exists():
        logger.info("No consent_policy.yaml found at %s, using defaults", _POLICY_PATH)
        return ConsentPolicyConfig()

    try:
        with open(_POLICY_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ConsentPolicyConfig.model_validate(data)
    except Exception as e:
        logger.warning("Failed to load consent_policy.yaml: %s — using defaults", e)
        return ConsentPolicyConfig()


# ── Dynamic Class Import (deer-flow pattern) ──────────────────────────────


def resolve_provider_class(dotted_path: str) -> type:
    """Import a class from 'module.path:ClassName' notation.

    Example: 'agent.consent.provider:YamlPolicyProvider'
    """
    if ":" not in dotted_path:
        raise ValueError(
            f"Provider path must be 'module:ClassName', got '{dotted_path}'"
        )
    module_path, class_name = dotted_path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls
