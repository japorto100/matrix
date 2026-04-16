"""Vendored MemPalace base collection interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCollection(ABC):
    """Smallest collection contract the local MemPalace layer relies on."""

    @abstractmethod
    def add(
        self,
        *,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert(
        self,
        *,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError
