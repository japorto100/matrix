"""ContextEngine ABC + DefaultContextEngine (exec-hermes §3.1).

Abstract contract for a "context engine" — the component that decides
**when** compaction-related events fire relative to the model's context
window, and **how** the final prompt is assembled.

Backed by the rules in :file:`specs/execution/exec-context.md` §6.1:

    | Stage       | Condition (share of current window) | Action                          |
    |-------------|-------------------------------------|----------------------------------|
    | Pre-Save    | ≥ 80%                               | Verbatim retain / session-persist|
    | Compaction  | ≥ 85%                               | Rolling summary of older turns   |
    | Emergency   | ≥ 95%                               | Minimal system + short history   |

The :class:`ContextEngine` ABC exposes threshold predicates and a
``stage_for`` classifier so callers (runner, llm_node, memory layer) don't
re-invent the wheel. :class:`DefaultContextEngine` implements it with the
canonical 0.80 / 0.85 / 0.95 thresholds, configurable for per-model tuning.

This module does **not** own compaction algorithms themselves — those live
in ``context/merge.py`` (referenced in exec-context §5). The engine tells
the caller "you should trigger pre-save now"; the caller (or memory layer)
does the actual work.
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass

__all__ = [
    "ContextStage",
    "ContextEngine",
    "ContextEngineConfig",
    "DefaultContextEngine",
    "get_context_engine",
    "reset_context_engine",
]


class ContextStage(enum.Enum):
    """Canonical stages along the context-fill gradient."""

    normal = "normal"          # < pre_save threshold
    pre_save = "pre_save"      # ≥ 80% — trigger verbatim retain
    compaction = "compaction"  # ≥ 85% — rolling summary
    emergency = "emergency"    # ≥ 95% — minimal prompt


@dataclass(frozen=True)
class ContextEngineConfig:
    """Thresholds as fractions of the current model's context window.

    Defaults match exec-context §6.1. Per-model overrides are easy (pass a
    custom config to :class:`DefaultContextEngine`). Thresholds must satisfy
    ``0 < pre_save ≤ compaction ≤ emergency < 1``.
    """

    pre_save: float = 0.80
    compaction: float = 0.85
    emergency: float = 0.95

    def __post_init__(self) -> None:
        if not (0.0 < self.pre_save <= self.compaction <= self.emergency < 1.0):
            raise ValueError(
                f"invalid thresholds: pre_save={self.pre_save} "
                f"compaction={self.compaction} emergency={self.emergency} — "
                "must be 0 < pre_save ≤ compaction ≤ emergency < 1"
            )


class ContextEngine(ABC):
    """Abstract base class for context-window orchestration.

    Subclasses implement the threshold rules. The default stage-transition
    contract is:

    - ``stage_for(tokens, window) -> ContextStage``: classify current fill.
    - ``should_verbatim_retain(...)``: true iff stage is pre_save or higher.
    - ``should_compact(...)``: true iff stage is compaction or higher.
    - ``should_emergency_compact(...)``: true iff stage is emergency.

    Implementations MUST return ``ContextStage.normal`` when ``window <= 0``
    (unknown window — classifier can't compare).
    """

    @abstractmethod
    def stage_for(self, *, tokens: int, window: int) -> ContextStage:
        """Classify the current context fill ratio into a stage."""

    def should_verbatim_retain(self, *, tokens: int, window: int) -> bool:
        """True iff callers should trigger verbatim-retain (Pre-Save)."""
        return self.stage_for(tokens=tokens, window=window) in (
            ContextStage.pre_save,
            ContextStage.compaction,
            ContextStage.emergency,
        )

    def should_compact(self, *, tokens: int, window: int) -> bool:
        """True iff callers should run rolling-summary compaction."""
        return self.stage_for(tokens=tokens, window=window) in (
            ContextStage.compaction,
            ContextStage.emergency,
        )

    def should_emergency_compact(self, *, tokens: int, window: int) -> bool:
        """True iff callers should switch to the emergency minimal prompt."""
        return self.stage_for(tokens=tokens, window=window) is ContextStage.emergency


class DefaultContextEngine(ContextEngine):
    """exec-context §6.1 defaults: 80 / 85 / 95 thresholds.

    Usage::

        engine = DefaultContextEngine()
        if engine.should_verbatim_retain(tokens=150_000, window=200_000):
            await memory_manager.on_pre_compress(messages, ...)
        if engine.should_compact(...):
            # run rolling-summary compactor
            ...
    """

    def __init__(self, config: ContextEngineConfig | None = None) -> None:
        self._cfg = config or ContextEngineConfig()

    @property
    def config(self) -> ContextEngineConfig:
        return self._cfg

    def stage_for(self, *, tokens: int, window: int) -> ContextStage:
        if window <= 0 or tokens < 0:
            return ContextStage.normal
        ratio = tokens / window
        if ratio >= self._cfg.emergency:
            return ContextStage.emergency
        if ratio >= self._cfg.compaction:
            return ContextStage.compaction
        if ratio >= self._cfg.pre_save:
            return ContextStage.pre_save
        return ContextStage.normal

    def stage_for_model(self, *, tokens: int, model: str) -> ContextStage:
        """Convenience wrapper: resolve ``model → window`` via LiteLLM then classify.

        Phase-B P5 addition (Contrarian-2 CRITICAL-1 safe): the ABC
        :meth:`stage_for(tokens, window)` signature stays permanently
        stable — this method is additive on :class:`DefaultContextEngine`
        only. Callers that already have the window (tests, custom engines)
        keep using ``stage_for``; callers that just have a model id can
        use this helper.
        """
        from agent.llm.model_metadata import get_model_context_window

        window = get_model_context_window(model) if model else 0
        return self.stage_for(tokens=tokens, window=window)


# ---------------------------------------------------------------------------
# Module-level accessor (mirror of get_credential_pool in resilience/)
# ---------------------------------------------------------------------------

_engine: ContextEngine | None = None


def get_context_engine() -> ContextEngine:
    """Return the process-wide :class:`ContextEngine` singleton (lazy).

    Seeded by ``agent.resilience.init_stack._init_agent_resilience_stack``
    at FastAPI startup, but callable before that for early imports — the
    first call builds a :class:`DefaultContextEngine` with canonical
    thresholds, subsequent calls return the same instance.
    """
    global _engine
    if _engine is None:
        _engine = DefaultContextEngine()
    return _engine


def reset_context_engine() -> None:
    """Testing helper — drop the singleton so the next call rebuilds."""
    global _engine
    _engine = None
