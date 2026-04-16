"""Vendored minimal MemPalace pieces used by memory_fusion.

Importe bleiben absichtlich lazy, damit der produktive Postgres/Fusion-Pfad
kein `chromadb` braucht, solange der reine Parity-Adapter nicht verwendet wird.
"""

from __future__ import annotations

from typing import Any

from .query_sanitizer import sanitize_query
from .searcher import build_where_filter


def get_collection(*args: Any, **kwargs: Any):
    from .palace import get_collection as _get_collection

    return _get_collection(*args, **kwargs)


__all__ = ["build_where_filter", "get_collection", "sanitize_query"]
