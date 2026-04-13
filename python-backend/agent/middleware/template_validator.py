# Prompt Template Validator — exec-12 Phase 2.5
# Validates user-defined prompt templates against an allowlist of variables.
# Prevents template injection: {{db_password}}, {{system_prompt}}, etc.
#
# Pattern: pentagi validator.go (AST-based, allowlist-only)
# Python equivalent: parse f-string/Jinja2/mustache-style templates.

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Allowed Variables ────────────────────────────────────────────────────────

# Variables that user-defined templates may reference.
# Grouped by category for clarity.
ALLOWED_VARIABLES: dict[str, set[str]] = {
    # Context about the current session
    "session": {
        "user_name",
        "user_id",
        "thread_id",
        "timestamp",
        "date",
        "time",
        "agent_class",
        "agent_role",
    },
    # Market/trading context
    "market": {
        "symbol",
        "ticker",
        "asset",
        "timeframe",
        "interval",
        "price",
        "volume",
        "market_cap",
        "portfolio_summary",
        "positions",
        "balances",
    },
    # Agent behavior
    "agent": {
        "role_name",
        "role_description",
        "language",
        "tone",
        "max_tokens",
        "reasoning_effort",
    },
    # Memory context
    "memory": {
        "memories",
        "recent_memories",
        "relevant_context",
    },
    # Custom user-defined variables (injected at runtime)
    "custom": {
        "custom_1",
        "custom_2",
        "custom_3",
        "custom_4",
        "custom_5",
        "instruction",
        "goal",
        "focus_area",
        "constraints",
    },
}

# Flatten to a single set for fast lookup
ALL_ALLOWED: frozenset[str] = frozenset(
    var for group in ALLOWED_VARIABLES.values() for var in group
)

# ── Dangerous patterns (always blocked, even if variable name matches) ──────

_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\{\{.*?(password|secret|key|token|credential|api_key|auth).*?\}\}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\{\{.*?(env|environ|os\.|sys\.|import|eval|exec|__\w+__).*?\}\}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\{\{.*?(system_prompt|instructions|config|database|db_url|connection).*?\}\}",
        re.IGNORECASE,
    ),
    # Code execution attempts
    re.compile(r"\{%.*?%\}", re.DOTALL),  # Jinja2 {% %} blocks
    re.compile(r"\{\{.*?\(.*?\).*?\}\}"),  # Function calls inside templates
]

# ── Variable extraction ──────────────────────────────────────────────────────

# Matches: {{var}}, {{ var }}, {{var|filter}}, {var}
_TEMPLATE_VAR_PATTERN = re.compile(
    r"\{\{?\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*(?:\|[^}]*)?\}?\}"
)


@dataclass
class ValidationResult:
    """Result of template validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    variables_found: list[str] = field(default_factory=list)
    unauthorized_variables: list[str] = field(default_factory=list)


def extract_variables(template: str) -> list[str]:
    """Extract all variable names from a template string.

    Supports: {{var}}, {{ var }}, {var}, {{var|filter}}
    """
    matches = _TEMPLATE_VAR_PATTERN.findall(template)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        # Handle dotted access: {{user.name}} → "user"
        root = m.split(".")[0]
        if root not in seen:
            seen.add(root)
            result.append(root)
    return result


def validate_template(
    template: str,
    *,
    extra_allowed: set[str] | None = None,
    context: str = "unknown",
) -> ValidationResult:
    """Validate a user-defined prompt template.

    Checks:
    1. No dangerous patterns (code execution, secret access)
    2. All variables are in the allowlist
    3. Template is not empty
    4. Template is not excessively long

    Args:
        template: The template string to validate
        extra_allowed: Additional variable names to allow (for custom contexts)
        context: Description of where this template is used (for logging)
    """
    result = ValidationResult(valid=True)

    if not template or not template.strip():
        result.valid = False
        result.errors.append("Template is empty")
        return result

    # Length check (prevent DoS via huge templates)
    if len(template) > 10_000:
        result.valid = False
        result.errors.append(f"Template too long ({len(template)} chars, max 10000)")
        return result

    # Check dangerous patterns
    for pattern in _DANGEROUS_PATTERNS:
        match = pattern.search(template)
        if match:
            result.valid = False
            result.errors.append(f"Dangerous pattern detected: '{match.group()}'")
            logger.warning(
                "Template validation BLOCKED dangerous pattern in '%s': %s",
                context,
                match.group(),
            )

    if not result.valid:
        return result

    # Extract and validate variables
    variables = extract_variables(template)
    result.variables_found = variables

    allowed = set(ALL_ALLOWED)
    if extra_allowed:
        allowed |= extra_allowed

    unauthorized = [v for v in variables if v not in allowed]
    result.unauthorized_variables = unauthorized

    if unauthorized:
        result.valid = False
        result.errors.append(
            f"Unauthorized variables: {', '.join(unauthorized)}. "
            f"Allowed: {', '.join(sorted(allowed))}"
        )
        logger.warning(
            "Template validation REJECTED '%s': unauthorized vars %s",
            context,
            unauthorized,
        )

    return result


# ── Template rendering (safe) ────────────────────────────────────────────────


def render_template(
    template: str,
    variables: dict[str, Any],
    *,
    extra_allowed: set[str] | None = None,
    context: str = "unknown",
) -> str | None:
    """Validate and render a template. Returns None if validation fails.

    Only renders variables from the allowlist. Unknown variables are left as-is.
    """
    validation = validate_template(
        template, extra_allowed=extra_allowed, context=context
    )
    if not validation.valid:
        logger.error("Template render refused for '%s': %s", context, validation.errors)
        return None

    # Simple mustache-style rendering: {{var}} → value
    def replacer(match: re.Match) -> str:
        var_name = match.group(1).strip().split(".")[0]
        if var_name in variables:
            return str(variables[var_name])
        return match.group(0)  # Leave unknown vars as-is

    return _TEMPLATE_VAR_PATTERN.sub(replacer, template)
