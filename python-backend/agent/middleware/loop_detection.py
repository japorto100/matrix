"""Loop Detection Middleware (exec-10 Phase 5.1).

Erkennt wenn der Agent dieselben Tool-Calls wiederholt aufruft.
Pattern uebernommen von deer-flow LoopDetectionMiddleware.

Warnung nach 3x, Hard-Stop nach 5x (innerhalb sliding window von 20 Calls).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict, defaultdict

logger = logging.getLogger(__name__)


def _get_loop_config():
    """Get loop detection config from consent_policy.yaml with hardcoded fallbacks."""
    try:
        from agent.consent.config import get_consent_config

        return get_consent_config().rate_limits.loop_detection
    except Exception:
        return None


_lc = _get_loop_config()
WARN_THRESHOLD = _lc.warn_threshold if _lc else 3
HARD_LIMIT = _lc.hard_limit if _lc else 5
WINDOW_SIZE = _lc.window_size if _lc else 20

_WARNING_MSG = (
    "[LOOP DETECTED] You are repeating the same tool calls. "
    "Try a different approach or produce your final answer now."
)
_HARD_STOP_MSG = (
    "[LOOP HARD STOP] Repeated tool calls detected 5 times. "
    "Forcing final answer. Do not call any more tools."
)


def _hash_tool_calls(tool_calls: list[dict]) -> str:
    """Deterministischer Hash eines Sets von Tool-Calls (name + args)."""
    normalized = []
    for tc in tool_calls:
        normalized.append(
            {
                "name": tc.get("tool_name", tc.get("name", "")),
                "args": tc.get("tool_input", tc.get("args", {})),
            }
        )
    normalized.sort(
        key=lambda tc: (tc["name"], json.dumps(tc["args"], sort_keys=True, default=str))
    )
    blob = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.md5(blob.encode()).hexdigest()[:12]


class LoopDetector:
    """Erkennt repetitive Tool-Call Patterns pro Thread."""

    def __init__(
        self,
        warn_threshold: int = WARN_THRESHOLD,
        hard_limit: int = HARD_LIMIT,
        window_size: int = WINDOW_SIZE,
    ) -> None:
        self.warn_threshold = warn_threshold
        self.hard_limit = hard_limit
        self.window_size = window_size
        self._history: OrderedDict[str, list[str]] = OrderedDict()
        self._warned: dict[str, set[str]] = defaultdict(set)

    def check(self, thread_id: str, tool_calls: list[dict]) -> tuple[str | None, bool]:
        """Prueft Tool-Calls auf Loops.

        Returns:
            (warning_message | None, should_hard_stop)
        """
        if not tool_calls:
            return None, False

        call_hash = _hash_tool_calls(tool_calls)

        if thread_id not in self._history:
            self._history[thread_id] = []
        history = self._history[thread_id]
        history.append(call_hash)

        # Sliding window
        if len(history) > self.window_size:
            history[:] = history[-self.window_size :]

        count = history.count(call_hash)

        if count >= self.hard_limit:
            logger.warning(
                "Loop hard stop: thread=%s hash=%s count=%d",
                thread_id,
                call_hash,
                count,
            )
            return _HARD_STOP_MSG, True

        if count >= self.warn_threshold:
            warned = self._warned[thread_id]
            if call_hash not in warned:
                warned.add(call_hash)
                logger.info(
                    "Loop warning: thread=%s hash=%s count=%d",
                    thread_id,
                    call_hash,
                    count,
                )
                return _WARNING_MSG, False

        return None, False

    def clear(self, thread_id: str) -> None:
        """Resettet History fuer einen Thread."""
        self._history.pop(thread_id, None)
        self._warned.pop(thread_id, None)
