"""Cross-cutting HTTP clients (Go Storage Gateway, KG Pipeline)."""

from ingestion.clients.go_storage import GoStorageClient
from ingestion.clients.kg_pipeline import KGPipelineClient

__all__ = ["GoStorageClient", "KGPipelineClient"]
