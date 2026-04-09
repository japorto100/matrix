"""HTTP URL loader (for link ingestion)."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from ingestion.core.exceptions import LoadError
from ingestion.loaders.base import LoadResult, Loader


class HttpLoader(Loader):
    """Load bytes from an HTTP URL (for link ingestion pipeline)."""

    name = "http"

    def __init__(self, timeout: float = 30.0, max_size: int = 50 * 1024 * 1024) -> None:
        self._timeout = timeout
        self._max_size = max_size

    async def load(self, identifier: str) -> LoadResult:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                r = await client.get(identifier)
                r.raise_for_status()
        except httpx.HTTPError as e:
            raise LoadError(f"Failed to fetch URL {identifier}: {e}") from e

        if len(r.content) > self._max_size:
            raise LoadError(
                f"URL response too large: {len(r.content)} > {self._max_size} bytes"
            )

        parsed = urlparse(identifier)
        filename = parsed.path.rsplit("/", 1)[-1] or parsed.netloc + ".html"
        if "." not in filename:
            filename = filename + ".html"

        return LoadResult(
            data=r.content,
            filename=filename,
            source="http",
            content_type=r.headers.get("content-type"),
            size=len(r.content),
        )
