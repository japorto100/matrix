"""Chunk embedders (Phase 6)."""

from ingestion.embedders.base import Embedder
from ingestion.embedders.registry import EmbedderRegistry
from ingestion.embedders.sentence_transformer import SentenceTransformerEmbedder

__all__ = ["Embedder", "EmbedderRegistry", "SentenceTransformerEmbedder"]
