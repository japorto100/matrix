"""Deterministic CPU embedder (no model download).

Use this when running in lightweight mode or when no local ML models should be
downloaded. Produces stable embeddings for the same text, suitable for dev.
"""

from __future__ import annotations

import hashlib

from ingestion.embedders.base import Embedder


class DeterministicEmbedder(Embedder):
    name = "deterministic"

    def __init__(self, dim: int = 384) -> None:
        self.dim = int(dim)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for t in texts:
            digest = hashlib.md5((t or "").encode()).digest()
            base = [((b / 255.0) * 2.0 - 1.0) for b in digest]
            vec = (base * ((self.dim // len(base)) + 1))[: self.dim]
            out.append(vec)
        return out

