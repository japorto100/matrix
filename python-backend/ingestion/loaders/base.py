"""Loader ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LoadResult:
    """Bytes + metadata loaded from somewhere."""

    data: bytes
    filename: str
    source: str  # "local" | "seaweedfs" | "http"
    content_type: str | None = None
    size: int = 0


class Loader(ABC):
    """Abstract base for byte loaders."""

    name: str = ""

    @abstractmethod
    async def load(self, identifier: str) -> LoadResult:
        """Load bytes + metadata for the given identifier.

        identifier semantics depend on the loader:
        - LocalLoader: filesystem path
        - SeaweedFSLoader: artifact UUID
        - HttpLoader: full URL
        """
