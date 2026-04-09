"""Go Storage Gateway HTTP Client (D12 capability-based access).

This client never has direct SeaweedFS credentials. It fetches HMAC-signed URLs
from the Go appservice and uses them to PUT/GET bytes directly to SeaweedFS.

Endpoints used (from go-appservice/internal/handlers/http/artifact_handler.go):
- POST /api/v1/storage/artifacts/upload-url   → returns {url, fields, expires_at}
- POST /api/v1/storage/artifacts/{id}/mark-ready
- GET  /api/v1/storage/artifacts/{id}         → returns metadata
- GET  /api/v1/storage/artifacts/{id}/download → returns signed download URL
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from loguru import logger


class GoStorageClient:
    """Thin httpx wrapper around Go Storage Gateway endpoints."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_metadata(self, file_id: UUID | str) -> dict[str, Any]:
        """Fetch artifact metadata (mime, size, name, hash)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(f"{self.base_url}/api/v1/storage/artifacts/{file_id}")
            r.raise_for_status()
            return r.json()

    async def get_download_url(self, file_id: UUID | str) -> str:
        """Get a short-lived signed URL to GET the file bytes from SeaweedFS."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self.base_url}/api/v1/storage/artifacts/{file_id}/download"
            )
            r.raise_for_status()
            data = r.json()
            url = data.get("url") or data.get("download_url")
            if not url:
                raise ValueError(
                    f"Go gateway returned no signed URL for {file_id}: {data}"
                )
            return url

    async def download_bytes(self, file_id: UUID | str) -> bytes:
        """Convenience: fetch signed URL + GET bytes."""
        signed_url = await self.get_download_url(file_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(signed_url)
            r.raise_for_status()
            logger.debug(f"downloaded {len(r.content)} bytes for {file_id}")
            return r.content

    async def patch_metadata(
        self, file_id: UUID | str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        """Update artifact metadata (e.g. ingestion_status, chunk_count)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.patch(
                f"{self.base_url}/api/v1/storage/artifacts/{file_id}",
                json=patch,
            )
            r.raise_for_status()
            return r.json()
