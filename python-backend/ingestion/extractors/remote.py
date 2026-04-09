"""Remote extractor wrappers — proxy to extraction_layout worker (Venv 3, Port 8101).

In Phase 1 the extraction_layout worker is a stub that returns 503 for /extract.
These wrappers sit in the registry as the "logical" docling/marker extractors —
when called, they POST to extraction_layout and parse the JSON response back to
an ExtractedDocument.

Phase 1: extract() raises ExtractionError("not yet activated").
Phase 2: extract() returns a real ExtractedDocument from the remote worker.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from loguru import logger

from ingestion.core.exceptions import ExtractionError
from ingestion.extractors.base import DocumentExtractor, ExtractedDocument


class RemoteLayoutExtractor(DocumentExtractor):
    """Base class for extractors that live in the extraction_layout venv."""

    backend_name: str = ""  # subclasses set this (docling | marker | mineru)

    def __init__(self) -> None:
        self.base_url = os.environ.get(
            "EXTRACTION_LAYOUT_URL", "http://127.0.0.1:8101"
        ).rstrip("/")
        self.enabled = os.environ.get("EXTRACTION_LAYOUT_ENABLED", "false").lower() == "true"
        self.timeout = float(os.environ.get("EXTRACTION_LAYOUT_TIMEOUT_S", "300"))

    def is_available(self) -> bool:
        """Always 'available' in the registry — actual reachability checked at extract time."""
        return True

    def extract(self, path: Path) -> ExtractedDocument:
        if not self.enabled:
            raise ExtractionError(
                f"{self.backend_name} extractor lives in extraction_layout (Venv 3, "
                "Phase 2). Set EXTRACTION_LAYOUT_ENABLED=true and start the worker."
            )

        # In Phase 2 this should:
        #   1. POST file (or signed URL) to {base_url}/extract with backend=self.backend_name
        #   2. Parse JSON response back to ExtractedDocument dataclass
        # For Phase 1 we keep this simple — raise so the caller falls back to pymupdf4llm.
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(
                    f"{self.base_url}/extract",
                    json={
                        "file_path": str(path),
                        "backend": self.backend_name,
                        "doc_id": "",
                    },
                )
                if r.status_code == 503:
                    raise ExtractionError(
                        f"extraction_layout worker returned 503 (skeleton). "
                        "Activate Phase 2 — see extraction_layout/README.md"
                    )
                r.raise_for_status()
                # TODO Phase 2: parse r.json() into ExtractedDocument
                raise ExtractionError(
                    f"{self.backend_name} extract returned {r.status_code} but "
                    "Phase 2 JSON-to-ExtractedDocument parsing is not yet implemented"
                )
        except httpx.HTTPError as e:
            raise ExtractionError(
                f"extraction_layout worker unreachable at {self.base_url}: {e}"
            ) from e


class DoclingExtractor(RemoteLayoutExtractor):
    """Docling extractor — runs in extraction_layout venv (Phase 2)."""

    name = "docling"
    backend_name = "docling"
    requires_model_download = True
    model_size_mb = 500


class MarkerExtractor(RemoteLayoutExtractor):
    """marker-pdf extractor — runs in extraction_layout venv (Phase 2)."""

    name = "marker"
    backend_name = "marker"
    requires_model_download = True
    model_size_mb = 300


class MineruExtractor(RemoteLayoutExtractor):
    """MinerU VLM extractor — runs in extraction_layout venv (Phase 2, optional)."""

    name = "mineru"
    backend_name = "mineru"
    requires_gpu = True
    requires_model_download = True
    model_size_mb = 2500
