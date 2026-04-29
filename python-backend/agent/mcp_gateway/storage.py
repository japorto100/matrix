"""Descriptor snapshot storage adapters for MCP catalog policy.

This is intentionally migration-neutral: production can back the same interface
with a database table, while tests and local Meta-Harness lanes use deterministic
in-memory or JSON-file stores.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent.mcp_gateway.policy import (
    McpToolDescriptorSnapshot,
    diff_descriptor_snapshots,
)


class McpDescriptorSnapshotStore(Protocol):
    def get(self, server_id: str, matrix_name: str) -> McpToolDescriptorSnapshot | None:
        """Return the last stored descriptor snapshot for a server/tool."""

    def upsert(self, snapshot: McpToolDescriptorSnapshot) -> McpToolDescriptorSnapshot | None:
        """Store snapshot and return the previous value when present."""


@dataclass(frozen=True)
class McpDescriptorSnapshotWrite:
    previous: McpToolDescriptorSnapshot | None
    current: McpToolDescriptorSnapshot
    diff: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "previous": self.previous.as_dict() if self.previous else None,
            "current": self.current.as_dict(),
            "diff": self.diff,
        }


class InMemoryMcpDescriptorSnapshotStore:
    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, str], McpToolDescriptorSnapshot] = {}

    def get(self, server_id: str, matrix_name: str) -> McpToolDescriptorSnapshot | None:
        return self._snapshots.get((server_id, matrix_name))

    def upsert(self, snapshot: McpToolDescriptorSnapshot) -> McpToolDescriptorSnapshot | None:
        key = (snapshot.server_id, snapshot.matrix_name)
        previous = self._snapshots.get(key)
        self._snapshots[key] = snapshot
        return previous


class JsonMcpDescriptorSnapshotStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, server_id: str, matrix_name: str) -> McpToolDescriptorSnapshot | None:
        payload = self._read()
        record = payload.get(_key(server_id, matrix_name))
        if not isinstance(record, dict):
            return None
        return _snapshot_from_dict(record)

    def upsert(self, snapshot: McpToolDescriptorSnapshot) -> McpToolDescriptorSnapshot | None:
        payload = self._read()
        key = _key(snapshot.server_id, snapshot.matrix_name)
        previous_payload = payload.get(key)
        previous = (
            _snapshot_from_dict(previous_payload)
            if isinstance(previous_payload, dict)
            else None
        )
        payload[key] = snapshot.as_dict()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return previous

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(key): value
            for key, value in payload.items()
            if isinstance(value, dict)
        }


def persist_descriptor_snapshot(
    store: McpDescriptorSnapshotStore,
    snapshot: McpToolDescriptorSnapshot,
) -> McpDescriptorSnapshotWrite:
    """Persist one snapshot and compute drift against the previous version."""

    previous = store.upsert(snapshot)
    diff = (
        diff_descriptor_snapshots(previous, snapshot)
        if previous is not None
        else {
            "changed": False,
            "changed_fields": [],
            "added_risk_flags": [],
            "risk_escalated": False,
            "requires_reapproval": False,
        }
    )
    return McpDescriptorSnapshotWrite(
        previous=previous,
        current=snapshot,
        diff=diff,
    )


def _key(server_id: str, matrix_name: str) -> str:
    return f"{server_id}:{matrix_name}"


def _snapshot_from_dict(payload: dict[str, object]) -> McpToolDescriptorSnapshot:
    return McpToolDescriptorSnapshot(
        server_id=str(payload.get("server_id") or ""),
        original_name=str(payload.get("original_name") or ""),
        matrix_name=str(payload.get("matrix_name") or ""),
        descriptor_hash=str(payload.get("descriptor_hash") or ""),
        first_seen=str(payload.get("first_seen") or ""),
        last_seen=str(payload.get("last_seen") or ""),
        description=str(payload.get("description") or ""),
        input_schema_hash=str(payload.get("input_schema_hash") or ""),
        output_template_hash=str(payload.get("output_template_hash") or ""),
        security_schemes=_tuple(payload.get("security_schemes")),
        resource_uris=_tuple(payload.get("resource_uris")),
        risk_flags=_tuple(payload.get("risk_flags")),
        approval_level=payload.get("approval_level") or "auto",  # type: ignore[arg-type]
        enabled=bool(payload.get("enabled", True)),
    )


def _tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    return ()
