"""Output sinks (Phase 7)."""

from ingestion.sinks.base import Sink, SinkResult
from ingestion.sinks.hindsight_sink import HindsightSink
from ingestion.sinks.kg_sink import KGSink
from ingestion.sinks.registry import SinkRegistry
from ingestion.sinks.storage_sink import StorageSink

__all__ = [
    "HindsightSink",
    "KGSink",
    "Sink",
    "SinkRegistry",
    "SinkResult",
    "StorageSink",
]
