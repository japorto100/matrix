# Extension hook registry — Phase 22g
# AgentZero-pattern: on_tool_before/after, on_stream_chunk, on_response_end
# All hooks are optional no-ops by default; extensions register callbacks.

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

# Hook signatures (all async)
OnStreamChunkHook = Callable[[str, str], Awaitable[None]]  # (thread_id, text_delta)
OnToolBeforeHook = Callable[[str, str, dict], Awaitable[None]]  # (thread_id, tool_name, input)
OnToolAfterHook = Callable[[str, str, dict, dict], Awaitable[None]]  # (thread_id, tool_name, input, result)
OnResponseEndHook = Callable[[str, dict], Awaitable[None]]  # (thread_id, final_message)


class ExtensionRegistry:
    """Singleton registry for agent loop extension hooks."""

    def __init__(self) -> None:
        self._on_stream_chunk: list[OnStreamChunkHook] = []
        self._on_tool_before: list[OnToolBeforeHook] = []
        self._on_tool_after: list[OnToolAfterHook] = []
        self._on_response_end: list[OnResponseEndHook] = []

    def register_on_stream_chunk(self, hook: OnStreamChunkHook) -> None:
        self._on_stream_chunk.append(hook)

    def register_on_tool_before(self, hook: OnToolBeforeHook) -> None:
        self._on_tool_before.append(hook)

    def register_on_tool_after(self, hook: OnToolAfterHook) -> None:
        self._on_tool_after.append(hook)

    def register_on_response_end(self, hook: OnResponseEndHook) -> None:
        self._on_response_end.append(hook)

    async def fire_stream_chunk(self, thread_id: str, delta: str) -> None:
        for hook in self._on_stream_chunk:
            try:
                await hook(thread_id, delta)
            except Exception:
                pass  # hooks must not crash the loop

    async def fire_tool_before(self, thread_id: str, tool_name: str, tool_input: dict) -> None:
        for hook in self._on_tool_before:
            try:
                await hook(thread_id, tool_name, tool_input)
            except Exception:
                pass

    async def fire_tool_after(
        self, thread_id: str, tool_name: str, tool_input: dict, result: dict
    ) -> None:
        for hook in self._on_tool_after:
            try:
                await hook(thread_id, tool_name, tool_input, result)
            except Exception:
                pass

    async def fire_response_end(self, thread_id: str, final_message: Any) -> None:
        for hook in self._on_response_end:
            try:
                await hook(thread_id, final_message)
            except Exception:
                pass


# Process-global registry — import and use directly
_registry = ExtensionRegistry()


def get_extension_registry() -> ExtensionRegistry:
    return _registry
