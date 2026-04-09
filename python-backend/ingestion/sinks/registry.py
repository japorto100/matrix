"""Sink registry."""

from __future__ import annotations

from ingestion.clients.go_storage import GoStorageClient
from ingestion.clients.kg_pipeline import KGPipelineClient
from ingestion.sinks.base import Sink
from ingestion.sinks.hindsight_sink import HindsightSink
from ingestion.sinks.kg_sink import KGSink
from ingestion.sinks.storage_sink import StorageSink


class SinkRegistry:
    """Get a Sink by name."""

    def __init__(
        self,
        go_storage_client: GoStorageClient | None = None,
        kg_client: KGPipelineClient | None = None,
        hindsight_db_url: str | None = None,
    ) -> None:
        self._sinks: dict[str, Sink] = {
            "hindsight": HindsightSink(db_url=hindsight_db_url),
        }
        if go_storage_client is not None:
            self._sinks["storage"] = StorageSink(go_storage_client)
        if kg_client is not None:
            self._sinks["kg"] = KGSink(kg_client)

    def get(self, name: str) -> Sink:
        if name not in self._sinks:
            raise ValueError(f"Unknown sink: {name}")
        return self._sinks[name]

    def has(self, name: str) -> bool:
        return name in self._sinks

    def all(self) -> list[Sink]:
        return list(self._sinks.values())
