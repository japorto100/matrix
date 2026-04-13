"""Document deduplication via sha256 content hash.

Two levels:
- Document-level (full file): used for skip-if-already-ingested check
- Chunk-level (per ExtractedChunk): used for incremental reindex (Cursor IDE
  / paperwatcher merkle pattern). Only changed chunks are re-embedded.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingestion.core.types import ExtractedChunk


class DocumentHasher:
    """Compute sha256 of document bytes / chunk text for deduplication."""

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_chunk(chunk: ExtractedChunk) -> str:
        """Per-chunk content hash for incremental reindex.

        Used by smart_reindex() to determine which chunks have changed since
        the last ingest. Only chunks whose hash differs are re-embedded.
        """
        return hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
