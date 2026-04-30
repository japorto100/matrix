"""Agent-facing retrieval tool for provider-agnostic RAG/KG context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from agent.runtime_events import make_runtime_event
from agent.tools.base import TradingTool
from retrieval.api import retrieve

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class RetrieveContextInput(BaseModel):
    query: str = Field(
        min_length=1,
        description="User question or subtask to ground with Matrix retrieval context.",
    )
    mode: Literal["text", "graph", "hybrid", "temporal"] | None = Field(
        default=None,
        description="Optional retrieval mode. Omit to let the router infer intent.",
    )
    semantic_phrase: str = Field(
        default="",
        description="Optional semantic catalog phrase to fail-closed filter context.",
    )
    semantic_context: dict[str, Any] | None = Field(
        default=None,
        description="Compact semantic_lookup handoff metadata for exact terms.",
    )
    require_context_provenance: bool = Field(
        default=True,
        description="Require selected context to keep source/citation provenance.",
    )
    require_citations: bool = Field(
        default=False,
        description="Verify generated_answer citations when an answer is supplied.",
    )
    generated_answer: str = Field(
        default="",
        description="Optional draft answer to verify against selected context.",
    )
    max_hits: int = Field(default=8, ge=1, le=20)
    token_budget: int = Field(default=1600, ge=200, le=12000)
    source_candidate_limit: int = Field(default=20, ge=0, le=50)
    use_vector_store: bool = Field(default=True)
    use_kg_store: bool = Field(default=True)


class RetrieveContextTool(TradingTool):
    """Retrieve source-grounded context for agent answers and subagent tasks."""

    input_model = RetrieveContextInput

    @property
    def name(self) -> str:
        return "retrieve_context"

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Retrieve Matrix RAG/KG context before answering source-grounded, "
                "document, graph, semantic or provenance questions. Returns selected "
                "context, compact references, runtime events and downstream artifact "
                "metadata. Use semantic_lookup first when the question names a metric "
                "or controlled semantic term."
            ),
            "input_schema": RetrieveContextInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict[str, Any], ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = RetrieveContextInput(**tool_input)
        semantic_filter = _semantic_filter_from_context(params.semantic_context)
        result = await retrieve(
            params.query,
            mode=params.mode,
            semantic_phrase=params.semantic_phrase or None,
            semantic_filter=semantic_filter,
            require_context_provenance=params.require_context_provenance,
            require_citations=params.require_citations,
            generated_answer=params.generated_answer or None,
            max_hits=params.max_hits,
            token_budget=params.token_budget,
            source_candidate_limit=params.source_candidate_limit,
            use_vector_store=params.use_vector_store,
            use_kg_store=params.use_kg_store,
            thread_id=ctx.thread_id,
            session_id=ctx.thread_id,
            audit_runtime_events=True,
        )
        artifacts = _downstream_artifacts(result)
        runtime_events = list(result.runtime_events or [])
        if artifacts["files"]:
            runtime_events.append(
                make_runtime_event(
                    kind="artifact",  # type: ignore[arg-type]
                    status="completed",  # type: ignore[arg-type]
                    name="artifact.rag_kg_sources.ready",
                    summary="RAG/KG downstream artifacts are ready",
                    session_id=ctx.thread_id,
                    thread_id=ctx.thread_id,
                    metadata={
                        "artifact_files": [item["name"] for item in artifacts["files"]],
                        "source_count": artifacts["source_count"],
                        "kg_path_count": artifacts["kg_path_count"],
                    },
                )
            )
        return {
            "ok": True,
            "query": params.query,
            "intent": result.intent,
            "context": result.context,
            "hits": result.hits or [],
            "references": result.references or [],
            "source_candidates": result.source_candidates or [],
            "verification": result.verification,
            "degraded": result.degraded,
            "degraded_reasons": result.degraded_reasons or [],
            "files": artifacts["files"],
            "downstream_artifacts": artifacts,
            "runtime_events": runtime_events,
        }

    def to_model_output(self, result: dict[str, Any]) -> dict[str, Any]:
        references = [
            _compact_reference(item)
            for item in result.get("references") or []
            if isinstance(item, dict)
        ][:8]
        candidates = [
            _compact_source_candidate(item)
            for item in result.get("source_candidates") or []
            if isinstance(item, dict)
        ][:8]
        files = [
            {"name": str(item.get("name") or ""), "mime": str(item.get("mime") or "")}
            for item in result.get("files") or []
            if isinstance(item, dict)
        ]
        return {
            "status": "degraded" if result.get("degraded") else "ok",
            "intent": result.get("intent"),
            "context_excerpt": str(result.get("context") or "")[:2400],
            "references": references,
            "source_candidates": candidates,
            "verification": result.get("verification"),
            "degraded_reasons": result.get("degraded_reasons") or [],
            "artifact_files": files,
        }


def _semantic_filter_from_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None
    out: dict[str, Any] = {}
    for key in ("semantic_catalog_version", "semantic_term_ids", "metric_id"):
        value = context.get(key)
        if value not in (None, "", [], ()):
            out[key] = value
    return out or None


def _downstream_artifacts(result: Any) -> dict[str, Any]:
    sources = [
        _compact_source_item(item)
        for item in result.hits or []
        if isinstance(item, dict)
    ]
    references = [
        _compact_reference(item)
        for item in result.references or []
        if isinstance(item, dict)
    ]
    candidates = [
        _compact_source_candidate(item)
        for item in result.source_candidates or []
        if isinstance(item, dict)
    ]
    kg_paths = [
        _kg_path_item(item)
        for item in result.hits or []
        if isinstance(item, dict) and _kg_path_item(item)
    ]
    files = [
        {
            "name": "rag-kg-sources.json",
            "mime": "application/json",
            "content": {
                "sources": sources,
                "references": references,
                "source_candidates": candidates,
            },
        }
    ]
    if kg_paths:
        files.append(
            {
                "name": "kg-paths.json",
                "mime": "application/json",
                "content": {"paths": kg_paths},
            }
        )
    return {
        "files": files,
        "source_count": len(sources),
        "reference_count": len(references),
        "source_candidate_count": len(candidates),
        "kg_path_count": len(kg_paths),
    }


def _compact_source_item(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return {
        "id": str(item.get("id") or ""),
        "source": str(item.get("source") or ""),
        "source_uri": str(item.get("source_uri") or ""),
        "score": item.get("score"),
        "metadata": _metadata_subset(metadata),
    }


def _compact_reference(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return {
        "id": str(item.get("id") or ""),
        "source": str(item.get("source") or ""),
        "citation_ref": str(metadata.get("citation_ref") or item.get("citation_ref") or ""),
        "provenance_status": str(metadata.get("provenance_status") or ""),
        "metadata": _metadata_subset(metadata),
    }


def _compact_source_candidate(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return {
        "id": str(item.get("id") or ""),
        "source": str(item.get("source") or ""),
        "source_uri": str(item.get("source_uri") or ""),
        "retrieval_lane": str(item.get("retrieval_lane") or ""),
        "provenance_status": str(item.get("provenance_status") or ""),
        "metadata": _metadata_subset(metadata),
    }


def _kg_path_item(item: dict[str, Any]) -> dict[str, Any] | None:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    source = str(item.get("source") or "")
    has_kg_source = source == "kg" or "kg" in set(metadata.get("contributing_sources") or [])
    claim_id = str(metadata.get("claim_id") or (item.get("id") if has_kg_source else "") or "")
    if not has_kg_source and not metadata.get("claim_id"):
        return None
    path = metadata.get("kg_path") or metadata.get("path") or metadata.get("claim_path")
    if not isinstance(path, list | tuple):
        path = ()
    return {
        "claim_id": claim_id,
        "claim_type": str(metadata.get("claim_type") or ""),
        "path": [str(part) for part in path if str(part)],
        "citation_ref": str(metadata.get("citation_ref") or ""),
        "source_artifact_id": str(metadata.get("source_artifact_id") or ""),
        "semantic_term_ids": list(metadata.get("semantic_term_ids") or []),
    }


def _metadata_subset(metadata: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "source_artifact_id",
        "chunk_id",
        "chunk_hash",
        "citation_ref",
        "semantic_catalog_version",
        "semantic_term_ids",
        "metric_id",
        "claim_id",
        "claim_type",
        "valid_time_range",
        "retrieval_lane",
        "lane_score",
        "provenance_status",
    )
    return {key: metadata[key] for key in keys if metadata.get(key) not in (None, "")}
