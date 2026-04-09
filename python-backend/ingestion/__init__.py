"""Matrix Ingestion Pipeline (Venv 2).

Phase-based document ingestion: detect → load → extract → normalize → chunk → embed → sink → track.

Decoupling rule (D17): this package may import `memory_engine.*` (shared data layer)
but MUST NOT import `agent.*`. Communication with main agent runtime is via HTTP only.
"""

__version__ = "0.1.0"
