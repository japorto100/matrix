"""A2uiEmitter — agent-side helper for emitting Ansatz-X SSE packets.

Replaces dict-envelope construction in agent code with a typed surface.
The emitter delegates validation to the official SDK's
``A2uiSchemaManager`` + ``A2uiValidator`` so our trees stay spec-
compliant, then yields our project-local ``streaming.py`` packets.

Usage (happy path):

    from agent.a2ui import A2uiEmitter
    from agent.streaming import sse

    emitter = A2uiEmitter(surface_id="main")
    emitter.begin(components={"type": "Card", "children": []}, data_model={"price": 42})
    emitter.patch_data_model([{"op": "replace", "path": "/price", "value": 43}])
    emitter.end()

    # Each emitted packet is a streaming.py dataclass — wrap with sse()
    # at the SSE layer (runner's stream-emitter).
    for packet in emitter.drain():
        yield sse(packet)

Validation is opt-in per call — callers that stream from a trusted
LLM response (already validated by ``A2uiStreamParser``) can skip it
with ``validate=False``. In practice the runner does one validation
pass per surface at ``begin()`` time and skips for incremental
patches.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.schema.validator import A2uiValidator

from agent.streaming import (
    A2uiDeleteSurfacePacket,
    A2uiSurfaceEndPacket,
    A2uiSurfaceStartPacket,
    A2uiSurfaceUpdatePacket,
    A2uiUpdateDataModelPacket,
)

A2UI_VERSION = "0.9"
SYSTEM_PROMPT_ROLE_DEFAULT = (
    "a trading-focused agent that renders quantitative UI widgets"
)


@lru_cache(maxsize=1)
def get_shared_catalog():
    """Process-wide singleton for the basic catalog v0.9.

    The SDK's ``BasicCatalog.get_config("0.9").provider.load()`` reads
    bundled JSON schemas on first access; caching avoids repeated disk
    I/O across agent turns.
    """
    bc = BasicCatalog()
    cfg = bc.get_config(A2UI_VERSION)
    mgr = A2uiSchemaManager(version=A2UI_VERSION, catalogs=[cfg])
    return mgr.get_selected_catalog()


@lru_cache(maxsize=1)
def get_shared_schema_manager() -> A2uiSchemaManager:
    """Process-wide singleton for the schema manager (used for system-prompt
    generation + schema introspection). Separate from catalog cache because
    manager holds loaded schemas + catalog configs together."""
    bc = BasicCatalog()
    cfg = bc.get_config(A2UI_VERSION)
    return A2uiSchemaManager(version=A2UI_VERSION, catalogs=[cfg])


def build_system_prompt(role_description: str = SYSTEM_PROMPT_ROLE_DEFAULT) -> str:
    """Return the canonical A2UI system prompt to append to the agent's
    system message when widget emission is active. Output includes the
    JSON-schema reference + tag delimiter rules + top-down ordering
    requirement the streaming parser relies on.
    """
    return get_shared_schema_manager().generate_system_prompt(
        role_description=role_description
    )


def _validator() -> A2uiValidator:
    # Cheap — A2uiValidator is a thin wrapper over the catalog's
    # compiled JSON schema. Fresh instance per call keeps thread-safety
    # simple; if this ever shows up in profiling, memoise.
    return A2uiValidator(catalog=get_shared_catalog())


def validate_protocol_messages(messages: list[dict]) -> None:
    """Validate a list of A2UI v0.9 protocol messages against the SDK schema.

    Shape is the 3-step form used by the official SDK + the streaming
    parser: ``[{version, createSurface: {surfaceId, catalogId}},
    {version, updateComponents: {surfaceId, components}},
    {version, updateDataModel: {surfaceId, patches}}]``. Call this when
    you're emitting canonical v0.9 messages (e.g. forwarding parser
    output), not for our ergonomic combined Ansatz-X packets — those
    don't map 1:1 to a single protocol message.

    Raises ``ValueError`` on schema violation (propagated from SDK).
    """
    _validator().validate(messages)


def translate_sdk_message(
    msg: dict,
    *,
    surface_id: str,
) -> (
    A2uiSurfaceStartPacket
    | A2uiSurfaceUpdatePacket
    | A2uiUpdateDataModelPacket
    | A2uiSurfaceEndPacket
    | A2uiDeleteSurfacePacket
    | None
):
    """Map an SDK-parsed A2UI protocol message to the matching wire packet.

    The SDK's streaming parser yields messages shaped like::

        {"createSurface": {"surfaceId": ..., "components": [...], "dataModel": ...}}
        {"updateComponents": {"surfaceId": ..., "patch": [...]}}
        {"updateDataModel": {"surfaceId": ..., "patch": [...]}}
        {"endSurface": {"surfaceId": ...}}
        {"deleteSurface": {"surfaceId": ...}}

    We flatten those to the corresponding Ansatz-X packet. When a
    message carries no ``surfaceId`` (older v0.8 shapes) we fall back
    to the caller-provided default.
    """
    if "createSurface" in msg:
        payload = msg["createSurface"]
        return A2uiSurfaceStartPacket(
            surface_id=payload.get("surfaceId", surface_id),
            components=payload.get("components", payload.get("tree", [])),
            data_model=payload.get("dataModel", {}),
        )
    if "updateComponents" in msg:
        payload = msg["updateComponents"]
        return A2uiSurfaceUpdatePacket(
            surface_id=payload.get("surfaceId", surface_id),
            patch=payload.get("patch", []),
        )
    if "updateDataModel" in msg:
        payload = msg["updateDataModel"]
        return A2uiUpdateDataModelPacket(
            surface_id=payload.get("surfaceId", surface_id),
            patch=payload.get("patch", []),
        )
    if "endSurface" in msg:
        payload = msg["endSurface"]
        return A2uiSurfaceEndPacket(surface_id=payload.get("surfaceId", surface_id))
    if "deleteSurface" in msg:
        payload = msg["deleteSurface"]
        return A2uiDeleteSurfacePacket(surface_id=payload.get("surfaceId", surface_id))
    return None


class A2uiEmitter:
    """Stateful helper that queues packets for one logical surface-stream."""

    def __init__(self, surface_id: str) -> None:
        if not surface_id or not isinstance(surface_id, str):
            raise ValueError("surface_id must be a non-empty string")
        self.surface_id = surface_id
        self._queue: list[object] = []
        self._started = False

    def begin(
        self,
        *,
        components: list | dict,
        data_model: dict | None = None,
        validate: bool = False,
    ) -> None:
        """Open the surface with an initial components tree + data model.

        ``components`` is either a v0.9 flat list (``[{id, component,
        ...}, ...]`` with ``root`` entry) or our ergonomic nested shape
        — the frontend adapter (``features/agent/lib/a2ui-packets.ts``)
        translates in both directions.

        ``validate=True`` runs the payload through the SDK validator as
        a canonical 3-step v0.9 protocol message pair (createSurface +
        updateComponents + updateDataModel). Only enable this when you
        know your ``components`` is the v0.9 flat-list shape; otherwise
        the validator will reject the convenience nesting. Default is
        off — the streaming parser upstream already validates LLM
        output, and downstream rendering errors are caught by the
        frontend renderer.
        """
        if self._started:
            raise RuntimeError(f"surface {self.surface_id!r} already started")
        data_model = data_model or {}
        if validate:
            catalog_id = get_shared_catalog().catalog_id
            proto_msgs: list[dict[str, Any]] = [
                {
                    "version": f"v{A2UI_VERSION}",
                    "createSurface": {
                        "surfaceId": self.surface_id,
                        "catalogId": catalog_id,
                    },
                },
                {
                    "version": f"v{A2UI_VERSION}",
                    "updateComponents": {
                        "surfaceId": self.surface_id,
                        "components": components,
                    },
                },
            ]
            if data_model:
                proto_msgs.append(
                    {
                        "version": f"v{A2UI_VERSION}",
                        "updateDataModel": {
                            "surfaceId": self.surface_id,
                            "patches": [
                                {"path": "/" + k, "value": v}
                                for k, v in data_model.items()
                            ],
                        },
                    }
                )
            _validator().validate(proto_msgs)
        self._queue.append(
            A2uiSurfaceStartPacket(
                surface_id=self.surface_id,
                components=components,
                data_model=data_model,
            )
        )
        self._started = True

    def patch_components(self, patch: list[dict[str, Any]]) -> None:
        """Emit a JSON-Patch (RFC 6902) scoped to the components tree."""
        if not self._started:
            raise RuntimeError("begin() must be called before patch_components()")
        self._queue.append(
            A2uiSurfaceUpdatePacket(surface_id=self.surface_id, patch=patch)
        )

    def patch_data_model(self, patch: list[dict[str, Any]]) -> None:
        """Emit a JSON-Patch scoped to the data model (bound values)."""
        if not self._started:
            raise RuntimeError("begin() must be called before patch_data_model()")
        self._queue.append(
            A2uiUpdateDataModelPacket(surface_id=self.surface_id, patch=patch)
        )

    def end(self) -> None:
        """Signal the surface is done streaming."""
        if not self._started:
            raise RuntimeError("begin() must be called before end()")
        self._queue.append(A2uiSurfaceEndPacket(surface_id=self.surface_id))

    def delete(self) -> None:
        """Remove the surface from the client. Idempotent on the client side;
        emitter stays usable for re-begin afterwards."""
        self._queue.append(A2uiDeleteSurfacePacket(surface_id=self.surface_id))
        self._started = False

    def drain(self) -> list[object]:
        """Return queued packets and reset. Caller wraps each with sse()."""
        out, self._queue = self._queue, []
        return out
