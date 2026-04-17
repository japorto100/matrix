"""Vendored from MemPalace: shared collection access helpers."""

from __future__ import annotations


def get_collection(
    palace_path: str,
    collection_name: str = "mempalace_drawers",
    create: bool = True,
):
    """Get the local MemPalace-style collection through the backend layer."""
    from memory_fusion.mempalace.backends.chroma import ChromaBackend

    backend = ChromaBackend()
    return backend.get_collection(
        palace_path,
        collection_name=collection_name,
        create=create,
    )
