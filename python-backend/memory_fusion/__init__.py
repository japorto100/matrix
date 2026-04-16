"""Memory fusion runtime.

Kopie von `agent/memory` als neue, erweiterbare Runtime-Basis.
Hier werden Hindsight-orientierte Summary-/Fact-Pfade mit einem lokalen
MemPalace-inspirierten Verbatim-Layer zusammengefuehrt, ohne `agent/memory`
anzufassen.
"""

from .engine import get_bank_id, get_memory_engine, get_memory_provider
from .fusion_engine import FusionMemoryEngine

__all__ = [
    "FusionMemoryEngine",
    "get_bank_id",
    "get_memory_engine",
    "get_memory_provider",
]
