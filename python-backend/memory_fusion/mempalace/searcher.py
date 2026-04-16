"""Vendored from MemPalace: tiny search helpers."""

from __future__ import annotations


def build_where_filter(wing: str | None = None, room: str | None = None) -> dict:
    """Build metadata filter for wing/room filtering."""
    if wing and room:
        return {"$and": [{"wing": wing}, {"room": room}]}
    if wing:
        return {"wing": wing}
    if room:
        return {"room": room}
    return {}
