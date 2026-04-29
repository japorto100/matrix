from __future__ import annotations

from agent.mcp_gateway.policy import McpServerConfig, snapshot_descriptor
from agent.mcp_gateway.storage import (
    InMemoryMcpDescriptorSnapshotStore,
    JsonMcpDescriptorSnapshotStore,
    persist_descriptor_snapshot,
)


def test_in_memory_snapshot_store_reports_descriptor_drift() -> None:
    server = McpServerConfig(server_id="external", transport="stdio", enabled=True)
    store = InMemoryMcpDescriptorSnapshotStore()
    before = snapshot_descriptor(server, {"name": "lookup", "description": "Read rows."})
    after = snapshot_descriptor(
        server,
        {"name": "lookup", "description": "Delete rows."},
        first_seen=before.first_seen,
    )

    first = persist_descriptor_snapshot(store, before)
    second = persist_descriptor_snapshot(store, after)

    assert first.previous is None
    assert first.diff["changed"] is False
    assert second.previous == before
    assert second.diff["changed"] is True
    assert second.diff["risk_escalated"] is True
    assert second.diff["requires_reapproval"] is True


def test_json_snapshot_store_round_trips_without_env_or_server_secrets(tmp_path) -> None:
    server = McpServerConfig(
        server_id="external",
        transport="streamable-http",
        enabled=True,
        env={"SECRET": "do-not-store"},
    )
    snapshot = snapshot_descriptor(server, {"name": "lookup", "description": "Read rows."})
    store = JsonMcpDescriptorSnapshotStore(tmp_path / "snapshots.json")

    write = persist_descriptor_snapshot(store, snapshot)
    loaded = store.get(snapshot.server_id, snapshot.matrix_name)
    saved = (tmp_path / "snapshots.json").read_text(encoding="utf-8")

    assert write.previous is None
    assert loaded == snapshot
    assert "do-not-store" not in saved
    assert snapshot.matrix_name in saved
