"""Byte loaders (Phase 2 of pipeline)."""

from ingestion.loaders.base import Loader, LoadResult
from ingestion.loaders.http import HttpLoader
from ingestion.loaders.local import LocalLoader
from ingestion.loaders.registry import LoaderRegistry
from ingestion.loaders.seaweedfs import SeaweedFSLoader

__all__ = [
    "HttpLoader",
    "LoadResult",
    "Loader",
    "LoaderRegistry",
    "LocalLoader",
    "SeaweedFSLoader",
]
