"""Local filesystem loader (dev/testing)."""

from __future__ import annotations

from pathlib import Path

from ingestion.core.exceptions import LoadError
from ingestion.loaders.base import LoadResult, Loader


class LocalLoader(Loader):
    """Load bytes from a local filesystem path."""

    name = "local"

    async def load(self, identifier: str) -> LoadResult:
        path = Path(identifier)
        if not path.is_file():
            raise LoadError(f"File not found: {path}")
        data = path.read_bytes()
        return LoadResult(
            data=data,
            filename=path.name,
            source="local",
            size=len(data),
        )
