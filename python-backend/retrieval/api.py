"""Retrieval public API (Phase 3 — currently NotImplementedError).

In Phase 3 this will be the entry point for `agent/graph/nodes/retrieval_node.py`
and the main orchestration of query → search → rerank → context.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievalResult:
    context: str = ""
    hits: list[dict] | None = None
    intent: str = ""


async def retrieve(query: str, **kwargs: object) -> RetrievalResult:
    """Run the full retrieval pipeline.

    Phase 3: composes understanders → searchers → rerankers → verifiers → composers.
    """
    raise NotImplementedError(
        "retrieval is a Phase 3 skeleton. See retrieval/README.md for the adoption map."
    )
