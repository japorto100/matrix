"""Integration smoke test for the resilience bundle (Ralph Phase 4).

Verifies that the three Phase 1–3 modules coexist in the matrix harness:
import cleanly, have no circular dependencies, and can be composed into
one end-to-end flow (LiteLLM error → classify → pick recovery strategy →
capture rate-limit from a response, alongside an orthogonal skills-guard
scan).
"""
from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Imports resolve
# ---------------------------------------------------------------------------

def test_all_three_modules_importable():
    """The exact imports the harness is expected to rely on must all succeed."""
    from agent.security.skills_guard import scan_skill  # noqa: F401
    from agent.resilience.error_classifier import (  # noqa: F401
        classify_error,
        FailoverReason,
    )
    from agent.resilience.rate_limit_tracker import (  # noqa: F401
        RateLimitBucket,
        RateLimitRegistry,
    )


# ---------------------------------------------------------------------------
# End-to-end fake flow
# ---------------------------------------------------------------------------

def test_end_to_end_fake_flow():
    """Simulate the resilience path: error → classify → recovery → track."""
    from litellm.exceptions import RateLimitError

    from agent.resilience.error_classifier import (
        FailoverReason,
        RecoveryStrategy,
        classify_error,
    )
    from agent.resilience.rate_limit_tracker import RateLimitRegistry
    from agent.security.skills_guard import scan_skill

    # ── Step 1: LiteLLM call fails with rate-limit → classify ──
    exc = RateLimitError(
        message="rate limit hit — retry after 30s",
        llm_provider="openai",
        model="gpt-4o-mini",
    )
    classification = classify_error(exc)

    assert classification.reason is FailoverReason.rate_limit
    assert classification.recovery is RecoveryStrategy.backoff_then_rotate
    assert classification.retryable is True
    assert classification.status_code == 429

    # ── Step 2: Recovery succeeds, capture headers from the new response ──
    response = SimpleNamespace(
        _hidden_params={
            "additional_headers": {
                "x-ratelimit-limit-requests": "100",
                "x-ratelimit-remaining-requests": "5",
                "x-ratelimit-reset-requests": "28",
                "x-ratelimit-limit-tokens": "10000",
                "x-ratelimit-remaining-tokens": "1500",
                "x-ratelimit-reset-tokens": "60",
            }
        }
    )
    registry = RateLimitRegistry()
    captured = registry.capture_from_response(
        response, user_id="u1", provider_key_id="openai-1", provider="openai"
    )

    # All four windows materialised (missing 1h headers produce zero buckets).
    assert len(captured) == 4

    rpm = registry.get("u1", "openai-1", "requests")
    assert rpm is not None
    assert rpm.limit == 100
    assert rpm.remaining == 5
    assert rpm.usage_pct == 95.0

    tpm = registry.get("u1", "openai-1", "tokens")
    assert tpm is not None and tpm.limit == 10000 and tpm.remaining == 1500

    # Prometheus export has the labels and metrics the monitoring layer needs.
    export = rpm.to_prometheus_dict()
    assert export["labels"]["user_id"] == "u1"
    assert export["labels"]["provider"] == "openai"
    assert export["labels"]["window"] == "requests"
    assert export["metrics"]["usage_pct"] == 95.0

    # ── Step 3: Skills-guard is orthogonal but lives in the same bundle ──
    # A safe agent-generated skill must pass install with the matrix-official
    # trust level; a dangerous one must not unconditionally install.
    safe_skill = {
        "name": "demo",
        "files": {"SKILL.md": "# demo\n\nJust a greeting."},
    }
    safe_result = scan_skill(safe_skill, source="matrix-official")
    assert safe_result.verdict == "safe"
    assert safe_result.trust_level == "matrix-official"

    dangerous_skill = {
        "name": "bad",
        "files": {"run.sh": "#!/bin/bash\nrm -rf /\n"},
    }
    dangerous_result = scan_skill(dangerous_skill, source="matrix-official")
    assert dangerous_result.verdict == "dangerous"


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------

def test_no_circular_imports():
    """`python -c "import agent; import agent.security; import agent.resilience"`
    must succeed. Any circular-import or side-effect-on-import regression
    shows up here immediately."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import agent; import agent.security; import agent.resilience",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"import failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
