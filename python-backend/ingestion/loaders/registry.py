"""Loader registry."""

from __future__ import annotations

from ingestion.clients.go_storage import GoStorageClient
from ingestion.loaders.base import Loader
from ingestion.loaders.http import HttpLoader
from ingestion.loaders.local import LocalLoader
from ingestion.loaders.seaweedfs import SeaweedFSLoader


class LoaderRegistry:
    """Get a Loader by name."""

    def __init__(self, go_storage_client: GoStorageClient | None = None) -> None:
        self._loaders: dict[str, Loader] = {
            "local": LocalLoader(),
            "http": HttpLoader(),
        }
        if go_storage_client is not None:
            self._loaders["seaweedfs"] = SeaweedFSLoader(go_storage_client)

    def get(self, name: str) -> Loader:
        if name not in self._loaders:
            raise ValueError(f"Unknown loader: {name}")
        return self._loaders[name]

    def has(self, name: str) -> bool:
        return name in self._loaders
