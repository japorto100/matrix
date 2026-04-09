"""KG Pipeline HTTP Client (Phase 2 — currently a stub).

In Phase 1 the kg_pipeline worker is not running. This client returns a skip
response without making any HTTP call. When Phase 2 is activated:
1. uv sync in python-backend/kg_pipeline/
2. Set KG_PIPELINE_ENABLED=true
3. Start kg-pipeline-worker on Port 8099
4. This client begins forwarding extract requests
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger


class KGPipelineClient:
    """Thin HTTP client for the kg_pipeline worker (Port 8099)."""

    def __init__(self, base_url: str, enabled: bool = False, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled
        self._timeout = timeout

    async def extract(self, text: str, doc_id: str) -> dict[str, Any]:
        """Extract entities + relations from text.

        Returns {"entities": [...], "relations": [...], "skipped": bool}.
        """
        if not self.enabled:
            logger.debug("kg_pipeline disabled — skipping extract for {}", doc_id)
            return {"entities": [], "relations": [], "skipped": True, "reason": "disabled"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    f"{self.base_url}/extract",
                    json={"text": text, "doc_id": doc_id},
                )
                if r.status_code == 503:
                    logger.warning("kg_pipeline returned 503 (not yet activated)")
                    return {
                        "entities": [],
                        "relations": [],
                        "skipped": True,
                        "reason": "not_activated",
                    }
                r.raise_for_status()
                return r.json()
        except httpx.HTTPError as e:
            logger.warning("kg_pipeline call failed: {}", e)
            return {
                "entities": [],
                "relations": [],
                "skipped": True,
                "reason": f"http_error: {e}",
            }

    async def health(self) -> bool:
        """Check if the worker is reachable."""
        if not self.enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/health")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
