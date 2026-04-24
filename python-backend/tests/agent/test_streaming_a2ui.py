"""Unit tests for A2UI Ansatz X SSE packet types (plan-v2 Phase-2 #32).

Verifies wire-format: camelCase keys, required type literal, and that
roundtrip via the shared ``sse()`` helper produces frontend-parseable
SSE lines. No live-stream integration — that lives in the runner tests
once a producer wires these up.
"""
from __future__ import annotations

import json

from agent.streaming import (
    A2uiDeleteSurfacePacket,
    A2uiSurfaceEndPacket,
    A2uiSurfaceStartPacket,
    A2uiSurfaceUpdatePacket,
    A2uiUpdateDataModelPacket,
    sse,
)


def _parse_sse(line: str) -> dict:
    # Strip "data: " prefix + "\n\n" suffix.
    assert line.startswith("data: "), line
    assert line.endswith("\n\n"), line
    payload = line[len("data: ") : -len("\n\n")]
    return json.loads(payload)


def test_a2ui_surface_start_wire_format() -> None:
    packet = A2uiSurfaceStartPacket(
        surface_id="main",
        components={"type": "Card", "children": []},
        data_model={"price": 42.0},
    )
    frame = _parse_sse(sse(packet))
    assert frame["type"] == "a2ui-surface-start"
    assert frame["surfaceId"] == "main"  # snake_case → camelCase
    assert frame["components"] == {"type": "Card", "children": []}
    assert frame["dataModel"] == {"price": 42.0}


def test_a2ui_update_components_patch_roundtrip() -> None:
    patch = [
        {"op": "add", "path": "/children/-", "value": {"type": "TextBlock", "text": "hi"}},
    ]
    packet = A2uiSurfaceUpdatePacket(surface_id="chat-abc", patch=patch)
    frame = _parse_sse(sse(packet))
    assert frame["type"] == "a2ui-update-components"
    assert frame["surfaceId"] == "chat-abc"
    assert frame["patch"] == patch


def test_a2ui_update_data_model_ticker_shape() -> None:
    patch = [{"op": "replace", "path": "/price", "value": 43.5}]
    packet = A2uiUpdateDataModelPacket(surface_id="main", patch=patch)
    frame = _parse_sse(sse(packet))
    assert frame["type"] == "a2ui-update-data-model"
    assert frame["surfaceId"] == "main"
    assert frame["patch"] == patch


def test_a2ui_surface_end_minimal() -> None:
    frame = _parse_sse(sse(A2uiSurfaceEndPacket(surface_id="main")))
    assert frame == {"type": "a2ui-surface-end", "surfaceId": "main"}


def test_a2ui_delete_surface_minimal() -> None:
    frame = _parse_sse(sse(A2uiDeleteSurfacePacket(surface_id="main")))
    assert frame == {"type": "a2ui-delete-surface", "surfaceId": "main"}


def test_all_packet_types_distinct() -> None:
    """No two packets share the same ``type`` literal — avoids frontend
    zod-union ambiguity."""
    types = {
        A2uiSurfaceStartPacket(surface_id="x", components=[], data_model={}).type,
        A2uiSurfaceUpdatePacket(surface_id="x", patch=[]).type,
        A2uiUpdateDataModelPacket(surface_id="x", patch=[]).type,
        A2uiSurfaceEndPacket(surface_id="x").type,
        A2uiDeleteSurfacePacket(surface_id="x").type,
    }
    assert len(types) == 5
