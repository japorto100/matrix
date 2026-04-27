"""Context Bubble composer for compact RAG prompt context."""

from __future__ import annotations

from collections.abc import Sequence

from retrieval.core.types import ContextBubble, RetrievalHit


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used for deterministic context-budget tests."""

    return max(1, len(text) // 4)


def build_context_bubble(
    hits: Sequence[RetrievalHit],
    *,
    token_budget: int = 1600,
    max_hits: int = 8,
) -> ContextBubble:
    """Build a source-attributed context block under a rough token budget."""

    selected: list[RetrievalHit] = []
    references: list[dict[str, object]] = []
    lines: list[str] = []
    used_tokens = 0

    for idx, hit in enumerate(hits[:max_hits], start=1):
        content = " ".join(hit.content.split())
        if not content:
            continue
        label = f"[{idx}] {hit.source}"
        if hit.source_uri:
            label = f"{label} {hit.source_uri}"
        block = f"{label}\n{content}"
        cost = estimate_tokens(block)
        if selected and used_tokens + cost > token_budget:
            break
        selected.append(hit)
        lines.append(block)
        used_tokens += cost
        references.append(
            {
                "id": hit.id,
                "source": hit.source,
                "source_uri": hit.source_uri,
                "score": hit.score,
                "metadata": hit.metadata,
            }
        )

    return ContextBubble(
        text="\n\n".join(lines),
        hits=tuple(selected),
        references=tuple(references),
    )
