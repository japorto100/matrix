"""Tests for agent.a2ui — the thin wrapper around a2ui-agent-sdk."""
from __future__ import annotations

import pytest

from agent.a2ui import (
    A2uiEmitter,
    build_system_prompt,
    get_shared_catalog,
    get_shared_schema_manager,
    translate_sdk_message,
)
from agent.streaming import (
    A2uiDeleteSurfacePacket,
    A2uiSurfaceEndPacket,
    A2uiSurfaceStartPacket,
    A2uiSurfaceUpdatePacket,
    A2uiUpdateDataModelPacket,
    sse,
)


def test_sdk_wrapper_does_not_pull_heavy_deps() -> None:
    """Importing agent.a2ui must not load google.adk / google.genai / a2a."""
    import sys

    # The fixture imports have already run; verify nothing heavy made it in.
    heavy = [
        m
        for m in sys.modules
        if m.startswith(("google.adk", "google.genai", "a2a."))
    ]
    assert heavy == [], f"heavy SDK modules unexpectedly loaded: {heavy}"


def test_shared_catalog_cached() -> None:
    assert get_shared_catalog() is get_shared_catalog()


def test_build_system_prompt_has_spec_refs() -> None:
    prompt = build_system_prompt(role_description="quant analyst")
    assert "quant analyst" in prompt
    # Key markers from the canonical A2UI v0.9 prompt
    assert "<a2ui-json>" in prompt
    assert "</a2ui-json>" in prompt
    assert "components" in prompt


def test_schema_manager_supports_v09() -> None:
    ids = get_shared_schema_manager().supported_catalog_ids
    assert any("v0_9" in cid or "0.9" in cid for cid in ids), ids


def test_emitter_happy_path_queues_three_packets() -> None:
    e = A2uiEmitter(surface_id="main")
    e.begin(
        components=[{"id": "root", "component": "Card", "child": "t1"},
                    {"id": "t1", "component": "Text", "text": "hello"}],
        data_model={"price": 42.0},
    )
    e.patch_data_model([{"op": "replace", "path": "/price", "value": 43}])
    e.end()

    packets = e.drain()
    assert len(packets) == 3
    assert isinstance(packets[0], A2uiSurfaceStartPacket)
    assert isinstance(packets[1], A2uiUpdateDataModelPacket)
    assert isinstance(packets[2], A2uiSurfaceEndPacket)
    # drain() resets
    assert e.drain() == []


def test_emitter_v09_validation_accepts_valid_tree() -> None:
    """With validate=True and a proper v0.9 flat-list tree, begin() succeeds."""
    e = A2uiEmitter(surface_id="main")
    e.begin(
        components=[
            {"id": "root", "component": "Card", "child": "t1"},
            {"id": "t1", "component": "Text", "text": "hello"},
        ],
        validate=True,
    )
    packets = e.drain()
    assert len(packets) == 1
    assert isinstance(packets[0], A2uiSurfaceStartPacket)


def test_emitter_patch_components_packet_shape() -> None:
    e = A2uiEmitter(surface_id="chat-abc")
    e.begin(components=[{"id": "root", "component": "Text", "text": "hi"}])
    e.patch_components([{"op": "add", "path": "/-", "value": {"id": "t2"}}])
    packets = e.drain()
    assert isinstance(packets[1], A2uiSurfaceUpdatePacket)
    assert packets[1].surface_id == "chat-abc"


def test_emitter_delete_standalone() -> None:
    e = A2uiEmitter(surface_id="main")
    e.delete()
    packets = e.drain()
    assert len(packets) == 1
    assert isinstance(packets[0], A2uiDeleteSurfacePacket)


def test_emitter_rejects_empty_surface_id() -> None:
    with pytest.raises(ValueError):
        A2uiEmitter(surface_id="")


def test_emitter_patch_before_begin_raises() -> None:
    e = A2uiEmitter(surface_id="main")
    with pytest.raises(RuntimeError):
        e.patch_data_model([])


def test_emitter_double_begin_raises() -> None:
    e = A2uiEmitter(surface_id="main")
    e.begin(components=[{"id": "root", "component": "Text", "text": "hi"}])
    with pytest.raises(RuntimeError):
        e.begin(components=[{"id": "root", "component": "Text", "text": "hi"}])


def test_emitter_validation_rejects_invalid_tree() -> None:
    """With validate=True, SDK catches schema violations at begin() time."""
    e = A2uiEmitter(surface_id="main")
    with pytest.raises(Exception):  # jsonschema.ValidationError or similar
        e.begin(components=[{"not": "a-valid-component"}], validate=True)


def test_translate_sdk_message_all_message_types() -> None:
    cases = [
        (
            {"createSurface": {"surfaceId": "s1", "components": [], "dataModel": {"x": 1}}},
            A2uiSurfaceStartPacket,
        ),
        (
            {"updateComponents": {"surfaceId": "s1", "patch": [{"op": "add"}]}},
            A2uiSurfaceUpdatePacket,
        ),
        (
            {"updateDataModel": {"surfaceId": "s1", "patch": [{"op": "replace"}]}},
            A2uiUpdateDataModelPacket,
        ),
        ({"endSurface": {"surfaceId": "s1"}}, A2uiSurfaceEndPacket),
        ({"deleteSurface": {"surfaceId": "s1"}}, A2uiDeleteSurfacePacket),
    ]
    for msg, expected in cases:
        pkt = translate_sdk_message(msg, surface_id="default")
        assert pkt is not None
        assert isinstance(pkt, expected), (msg, pkt)
        assert pkt.surface_id == "s1"


def test_translate_falls_back_to_default_surface_id() -> None:
    """Messages without an explicit surfaceId use the emitter default."""
    pkt = translate_sdk_message({"endSurface": {}}, surface_id="fallback")
    assert isinstance(pkt, A2uiSurfaceEndPacket)
    assert pkt.surface_id == "fallback"


def test_translate_unknown_message_returns_none() -> None:
    assert translate_sdk_message({"foo": "bar"}, surface_id="x") is None


def test_emitter_packets_sse_roundtrip() -> None:
    """End-to-end: emit → drain → sse() produces parseable wire frames."""
    import json

    e = A2uiEmitter(surface_id="main")
    e.begin(components=[{"id": "root", "component": "Text", "text": "hi"}])
    for pkt in e.drain():
        line = sse(pkt)
        assert line.startswith("data: ")
        payload = json.loads(line[len("data: ") : -2])
        # camelCase conversion via streaming._to_sse
        assert "surfaceId" in payload
