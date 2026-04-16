"""Postgres-first memory fusion over summary + verbatim Hindsight routes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from memory_fusion.mempalace.query_sanitizer import sanitize_query
from memory_fusion.providers import create_hindsight_engine, normalize_ref
from memory_fusion.semantics import (
    PERSONAL_DERIVED_LAYER,
    classify_item_semantics,
    enrich_metadata_with_semantics,
)
from memory_fusion.summary_builder import build_summary_item, build_verbatim_item

SUMMARY_ROUTE = "summary"
VERBATIM_ROUTE = "verbatim"
FUSION_ROUTE = "fusion"
RRF_K = 60


@dataclass
class FusionResult:
    ref: str
    text: str
    score: float
    providers: list[str]
    metadata: dict[str, Any]


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class FusionMemoryEngine:
    """Hindsight-compatible fusion engine with semantic + evidence routes."""

    def __init__(
        self,
        *,
        summary_engine: Any,
        verbatim_engine: Any,
        summary_llm_provider: str,
        verbatim_llm_provider: str,
        summary_extraction_mode: str,
        verbatim_extraction_mode: str,
    ):
        self.summary_engine = summary_engine
        self.verbatim_engine = verbatim_engine
        self.summary_llm_provider = summary_llm_provider
        self.verbatim_llm_provider = verbatim_llm_provider
        self.summary_extraction_mode = summary_extraction_mode
        self.verbatim_extraction_mode = verbatim_extraction_mode

    @classmethod
    async def create(
        cls,
        *,
        db_url: str | None,
        palace_path: str | None = None,  # noqa: ARG003 - compatibility with older callers
    ) -> FusionMemoryEngine:
        summary_provider = os.environ.get("MEMORY_FUSION_SUMMARY_LLM_PROVIDER", "inherit").strip() or "inherit"
        if summary_provider == "inherit":
            summary_provider = os.environ.get("HINDSIGHT_API_LLM_PROVIDER") or "none"

        verbatim_provider = os.environ.get("MEMORY_FUSION_VERBATIM_LLM_PROVIDER", "inherit").strip() or "inherit"
        if verbatim_provider == "inherit":
            verbatim_provider = summary_provider if summary_provider != "none" else "none"

        summary_extraction_mode = os.environ.get("MEMORY_FUSION_SUMMARY_EXTRACTION_MODE", "concise").strip() or "concise"
        default_verbatim_mode = "verbatim" if verbatim_provider != "none" else "chunks"
        verbatim_extraction_mode = (
            os.environ.get("MEMORY_FUSION_VERBATIM_EXTRACTION_MODE", default_verbatim_mode).strip()
            or default_verbatim_mode
        )

        summary_engine = await create_hindsight_engine(
            db_url=db_url,
            llm_provider=summary_provider,
            retain_extraction_mode=summary_extraction_mode,
            enable_observations=_env_bool("MEMORY_FUSION_SUMMARY_ENABLE_OBSERVATIONS", True),
            retain_default_strategy=os.environ.get("MEMORY_FUSION_SUMMARY_STRATEGY"),
        )
        verbatim_engine = await create_hindsight_engine(
            db_url=db_url,
            llm_provider=verbatim_provider,
            retain_extraction_mode=verbatim_extraction_mode,
            enable_observations=_env_bool("MEMORY_FUSION_VERBATIM_ENABLE_OBSERVATIONS", False),
            retain_default_strategy=os.environ.get("MEMORY_FUSION_VERBATIM_STRATEGY"),
        )
        return cls(
            summary_engine=summary_engine,
            verbatim_engine=verbatim_engine,
            summary_llm_provider=summary_provider,
            verbatim_llm_provider=verbatim_provider,
            summary_extraction_mode=summary_extraction_mode,
            verbatim_extraction_mode=verbatim_extraction_mode,
        )

    @staticmethod
    def summary_bank_id(bank_id: str) -> str:
        return f"{bank_id}__summary"

    @staticmethod
    def verbatim_bank_id(bank_id: str) -> str:
        return f"{bank_id}__verbatim"

    @staticmethod
    def _base_bank_id(bank_id: str) -> str:
        if bank_id.endswith("__summary"):
            return bank_id[: -len("__summary")]
        if bank_id.endswith("__verbatim"):
            return bank_id[: -len("__verbatim")]
        return bank_id

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                out.append(value)
        return out

    @staticmethod
    def _route_from_kwargs(kwargs: dict[str, Any]) -> str:
        route = str(kwargs.pop("route", kwargs.pop("fusion_route", FUSION_ROUTE)) or FUSION_ROUTE).lower()
        if route not in {SUMMARY_ROUTE, VERBATIM_ROUTE, FUSION_ROUTE}:
            return FUSION_ROUTE
        return route

    @staticmethod
    def _annotate_route(item: dict[str, Any], route: str, *, bank_id: str | None = None) -> dict[str, Any]:
        annotated = dict(item)
        metadata = enrich_metadata_with_semantics(
            dict(annotated.get("metadata") or {}),
            fact_type=str(annotated.get("fact_type") or ""),
        )
        metadata["fusion_route"] = route
        annotated["metadata"] = metadata
        annotated["memory_layer"] = metadata.get("memory_layer")
        annotated["source_type"] = metadata.get("source_type")
        annotated["artifact_type"] = metadata.get("artifact_type")
        if bank_id is not None:
            annotated["bank_id"] = bank_id
        return annotated

    @staticmethod
    def _annotate_document(item: dict[str, Any], route: str, *, bank_id: str) -> dict[str, Any]:
        annotated = dict(item)
        annotated["bank_id"] = bank_id
        annotated["fusion_route"] = route
        document_metadata = enrich_metadata_with_semantics(dict(annotated.get("document_metadata") or {}))
        document_metadata["fusion_route"] = route
        annotated["document_metadata"] = document_metadata
        annotated["memory_layer"] = document_metadata.get("memory_layer")
        annotated["source_type"] = document_metadata.get("source_type")
        annotated["artifact_type"] = document_metadata.get("artifact_type")
        return annotated

    def _route_bank_id(self, bank_id: str, route: str) -> str:
        base = self._base_bank_id(bank_id)
        if route == SUMMARY_ROUTE:
            return self.summary_bank_id(base)
        if route == VERBATIM_ROUTE:
            return self.verbatim_bank_id(base)
        raise ValueError(f"Unsupported route: {route}")

    def _engine_for_route(self, route: str) -> Any:
        if route == SUMMARY_ROUTE:
            return self.summary_engine
        if route == VERBATIM_ROUTE:
            return self.verbatim_engine
        raise ValueError(f"Unsupported route: {route}")

    def _normalize_query(self, query: str) -> str:
        result = sanitize_query(query)
        return str(result.get("clean_query") or query)

    @staticmethod
    def _prefer_verbatim_text(query: str) -> bool:
        lowered = query.lower()
        return any(token in lowered for token in ("exact", "quote", "verbatim", "wording", "source text", "beleg"))

    @staticmethod
    def _is_ungrounded_derived(metadata: dict[str, Any]) -> bool:
        return (
            str(metadata.get("memory_layer") or "") == PERSONAL_DERIVED_LAYER
            and str(metadata.get("derived_without_evidence") or "").lower() == "true"
        )

    def _prepare_contents(self, contents: list[dict[str, Any]], route: str, *, bank_id: str | None = None) -> list[dict[str, Any]]:
        if route not in {SUMMARY_ROUTE, VERBATIM_ROUTE}:
            raise ValueError(f"Unsupported route: {route}")
        prepared: list[dict[str, Any]] = []
        for item in contents:
            semantics = classify_item_semantics(item, dict(item.get("metadata") or {}))
            if not semantics.allow_default_memory_write:
                raise ValueError(
                    f"memory_fusion retain path rejected {semantics.memory_layer} item "
                    f"({semantics.artifact_type}); route it to the dedicated KB/world path instead"
                )
            target_bank_id = bank_id or self._base_bank_id(str(item.get("bank_id") or "")) or None
            prepared.append(
                build_summary_item(item, bank_id=target_bank_id)
                if route == SUMMARY_ROUTE
                else build_verbatim_item(item, bank_id=target_bank_id)
            )
        return prepared

    def _recall_fusion_text(self, query: str, metadata: dict[str, Any], fallback_text: str) -> str:
        if self._prefer_verbatim_text(query):
            return str(metadata.get("verbatim_text") or metadata.get("summary_text") or fallback_text)
        return str(metadata.get("summary_text") or metadata.get("verbatim_text") or fallback_text)

    def _fact_metadata(self, metadata: dict[str, Any], *, route: str, fact_type: str | None = None) -> dict[str, Any]:
        enriched = enrich_metadata_with_semantics(metadata, fact_type=fact_type)
        enriched["fusion_route"] = route
        return enriched

    def _should_surface_item(self, item: dict[str, Any]) -> bool:
        metadata = dict(item.get("metadata") or item.get("document_metadata") or {})
        fact_type = str(item.get("fact_type") or "")
        return not self._is_ungrounded_derived(enrich_metadata_with_semantics(metadata, fact_type=fact_type))

    def _normalized_route_results(self, facts: list[Any], route: str, *, n_results: int) -> list[FusionResult]:
        normalized: list[FusionResult] = []
        for rank, fact in enumerate(facts, start=1):
            result = self._result_from_fact(fact, route, rank)
            if self._is_ungrounded_derived(result.metadata):
                continue
            normalized.append(result)
            if len(normalized) >= n_results:
                break
        return normalized

    def _filter_tags(
        self,
        tags: list[str] | None,
        *,
        wing: str | None = None,
        room: str | None = None,
        hall: str | None = None,
        closet: str | None = None,
        drawer: str | None = None,
    ) -> list[str] | None:
        merged = list(tags or [])
        if wing:
            merged.append(f"wing:{wing}")
        if room:
            merged.append(f"room:{room}")
        if hall:
            merged.append(f"hall:{hall}")
        if closet:
            merged.append(f"closet:{closet}")
        if drawer:
            merged.append(f"drawer:{drawer}")
        merged = self._dedupe_strings(merged)
        return merged or None

    @staticmethod
    def _matches_loci_filters(item: dict[str, Any], *, wing: str | None, room: str | None, hall: str | None, closet: str | None, drawer: str | None) -> bool:
        metadata = dict(item.get("metadata") or item.get("document_metadata") or {})
        checks = {
            "wing": wing,
            "room": room,
            "hall": hall,
            "closet_id": closet,
            "drawer_id": drawer,
        }
        for key, expected in checks.items():
            if expected is None:
                continue
            if str(metadata.get(key) or "").strip() != str(expected).strip():
                return False
        return True

    def _route_tags(self, document_tags: list[str] | None, route: str) -> list[str]:
        tags = list(document_tags or [])
        tags.append(f"fusion:{route}")
        return self._dedupe_strings(tags)

    async def _delegate_route(self, route: str, method: str, /, *args: Any, **kwargs: Any) -> Any:
        engine = self._engine_for_route(route)
        return await getattr(engine, method)(*args, **kwargs)

    async def _primary_then_secondary(
        self,
        primary: str,
        secondary: str,
        method: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        try:
            return await self._delegate_route(primary, method, *args, **kwargs)
        except Exception:
            return await self._delegate_route(secondary, method, *args, **kwargs)

    def _result_from_fact(self, fact: Any, route: str, rank: int) -> FusionResult:
        metadata = dict(getattr(fact, "metadata", {}) or {})
        document_id = getattr(fact, "document_id", None)
        chunk_id = getattr(fact, "chunk_id", None)
        if document_id is not None:
            metadata.setdefault("document_id", str(document_id))
        if chunk_id is not None:
            metadata.setdefault("chunk_id", str(chunk_id))
        metadata = self._fact_metadata(
            metadata,
            route=route,
            fact_type=str(getattr(fact, "fact_type", "") or ""),
        )

        text = str(getattr(fact, "text", "") or "")
        ref = normalize_ref(metadata)
        if route == SUMMARY_ROUTE:
            metadata.setdefault("summary_text", text)
        else:
            metadata.setdefault("verbatim_text", text)

        return FusionResult(
            ref=ref,
            text=text,
            score=1.0 / (RRF_K + rank),
            providers=[route],
            metadata=metadata,
        )

    def _merge_ranked_results(
        self,
        summary_facts: list[Any],
        verbatim_facts: list[Any],
        *,
        n_results: int,
    ) -> list[FusionResult]:
        merged: dict[str, FusionResult] = {}

        for route, facts in ((SUMMARY_ROUTE, summary_facts), (VERBATIM_ROUTE, verbatim_facts)):
            for rank, fact in enumerate(facts[:n_results], start=1):
                result = self._result_from_fact(fact, route, rank)
                if self._is_ungrounded_derived(result.metadata):
                    continue
                existing = merged.get(result.ref)
                if existing is None:
                    merged[result.ref] = result
                    continue

                existing.score += result.score
                existing.providers = self._dedupe_strings(existing.providers + result.providers)
                for key, value in result.metadata.items():
                    if value not in (None, "", [], {}):
                        existing.metadata[key] = value
                if route == VERBATIM_ROUTE and result.text:
                    existing.text = result.text
                existing.metadata.setdefault("summary_text", existing.text if route == VERBATIM_ROUTE else result.text)
                existing.metadata.setdefault("verbatim_text", existing.text if route == SUMMARY_ROUTE else result.text)

        return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:n_results]

    @staticmethod
    def _merge_entities(*entity_maps: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for entity_map in entity_maps:
            for key, value in dict(entity_map or {}).items():
                merged.setdefault(key, value)
        return merged

    @staticmethod
    def _merge_chunks(*chunk_maps: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for chunk_map in chunk_maps:
            merged.update(dict(chunk_map or {}))
        return merged

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def health_check(self) -> dict[str, Any]:
        summary_status = await self.summary_engine.health_check()
        verbatim_status = await self.verbatim_engine.health_check()
        return {
            "provider": FUSION_ROUTE,
            "healthy": bool(summary_status) and bool(verbatim_status),
            "summary": summary_status,
            "verbatim": verbatim_status,
            "summary_llm_provider": self.summary_llm_provider,
            "verbatim_llm_provider": self.verbatim_llm_provider,
            "summary_extraction_mode": self.summary_extraction_mode,
            "verbatim_extraction_mode": self.verbatim_extraction_mode,
        }

    async def status(self) -> dict[str, Any]:
        return await self.health_check()

    async def retain_batch_async(
        self,
        *,
        bank_id: str,
        contents: list[dict[str, Any]],
        request_context: Any,
        document_tags: list[str] | None = None,
        strategy: str | None = None,
        **kwargs: Any,
    ) -> list[list[str]]:
        route = self._route_from_kwargs(kwargs)
        base_bank_id = self._base_bank_id(bank_id)
        if route in {SUMMARY_ROUTE, VERBATIM_ROUTE}:
            return await self._delegate_route(
                route,
                "retain_batch_async",
                bank_id=self._route_bank_id(bank_id, route),
                contents=self._prepare_contents(contents, route, bank_id=base_bank_id),
                request_context=request_context,
                document_tags=self._route_tags(document_tags, route),
                strategy=strategy,
            )

        summary_ids = await self.summary_engine.retain_batch_async(
            bank_id=self.summary_bank_id(bank_id),
            contents=self._prepare_contents(contents, SUMMARY_ROUTE, bank_id=base_bank_id),
            request_context=request_context,
            document_tags=self._route_tags(document_tags, SUMMARY_ROUTE),
            strategy=strategy,
        )
        verbatim_ids = await self.verbatim_engine.retain_batch_async(
            bank_id=self.verbatim_bank_id(bank_id),
            contents=self._prepare_contents(contents, VERBATIM_ROUTE, bank_id=base_bank_id),
            request_context=request_context,
            document_tags=self._route_tags(document_tags, VERBATIM_ROUTE),
            strategy=strategy,
        )

        merged: list[list[str]] = []
        for idx in range(max(len(summary_ids), len(verbatim_ids))):
            merged.append(
                list(summary_ids[idx] if idx < len(summary_ids) else [])
                + list(verbatim_ids[idx] if idx < len(verbatim_ids) else [])
            )
        return merged

    async def submit_async_retain(
        self,
        bank_id: str,
        contents: list[dict[str, Any]],
        *,
        request_context: Any,
        document_tags: list[str] | None = None,
        strategy: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        route = self._route_from_kwargs(kwargs)
        base_bank_id = self._base_bank_id(bank_id)
        if route in {SUMMARY_ROUTE, VERBATIM_ROUTE}:
            return await self._delegate_route(
                route,
                "submit_async_retain",
                self._route_bank_id(bank_id, route),
                self._prepare_contents(contents, route, bank_id=base_bank_id),
                request_context=request_context,
                document_tags=self._route_tags(document_tags, route),
                strategy=strategy,
            )

        summary_op = await self.summary_engine.submit_async_retain(
            self.summary_bank_id(bank_id),
            self._prepare_contents(contents, SUMMARY_ROUTE, bank_id=base_bank_id),
            request_context=request_context,
            document_tags=self._route_tags(document_tags, SUMMARY_ROUTE),
            strategy=strategy,
        )
        verbatim_op = await self.verbatim_engine.submit_async_retain(
            self.verbatim_bank_id(bank_id),
            self._prepare_contents(contents, VERBATIM_ROUTE, bank_id=base_bank_id),
            request_context=request_context,
            document_tags=self._route_tags(document_tags, VERBATIM_ROUTE),
            strategy=strategy,
        )
        return {
            "operation_id": summary_op.get("operation_id"),
            "items_count": summary_op.get("items_count", len(contents)),
            "operation_ids": {
                SUMMARY_ROUTE: summary_op.get("operation_id"),
                VERBATIM_ROUTE: verbatim_op.get("operation_id"),
            },
            "routes": [SUMMARY_ROUTE, VERBATIM_ROUTE],
        }

    async def recall(
        self,
        *,
        bank_id: str,
        query: str,
        fact_type: list[str] | None = None,
        n_results: int = 10,
        request_context: Any,
        route: str = FUSION_ROUTE,
        tags: list[str] | None = None,
        wing: str | None = None,
        room: str | None = None,
        hall: str | None = None,
        closet: str | None = None,
        drawer: str | None = None,
    ) -> list[FusionResult]:
        clean_query = self._normalize_query(query)
        tags = self._filter_tags(tags, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)

        if route == SUMMARY_ROUTE:
            result = await self.summary_engine.recall_async(
                self.summary_bank_id(bank_id),
                clean_query,
                fact_type=fact_type,
                request_context=request_context,
                tags=tags,
            )
            return self._normalized_route_results(result.results, SUMMARY_ROUTE, n_results=n_results)

        if route == VERBATIM_ROUTE:
            result = await self.verbatim_engine.recall_async(
                self.verbatim_bank_id(bank_id),
                clean_query,
                fact_type=fact_type,
                include_chunks=True,
                request_context=request_context,
                tags=tags,
            )
            return self._normalized_route_results(result.results, VERBATIM_ROUTE, n_results=n_results)

        summary_result = await self.summary_engine.recall_async(
            self.summary_bank_id(bank_id),
            clean_query,
            fact_type=fact_type,
            request_context=request_context,
            tags=tags,
        )
        verbatim_result = await self.verbatim_engine.recall_async(
            self.verbatim_bank_id(bank_id),
            clean_query,
            fact_type=fact_type,
            include_chunks=True,
            request_context=request_context,
            tags=tags,
        )
        return self._merge_ranked_results(summary_result.results, verbatim_result.results, n_results=n_results)

    async def recall_async(
        self,
        *,
        bank_id: str,
        query: str,
        budget: Any = None,
        max_tokens: int = 4096,
        enable_trace: bool = False,
        fact_type: list[str] | None = None,
        question_date: Any = None,
        include_entities: bool = False,
        max_entity_tokens: int = 500,
        include_chunks: bool = False,
        max_chunk_tokens: int = 8192,
        include_source_facts: bool = False,
        max_source_facts_tokens: int = 4096,
        max_source_facts_tokens_per_observation: int = -1,
        request_context: Any = None,
        tags: list[str] | None = None,
        tags_match: Any = "any",
        tag_groups: list[Any] | None = None,
        **kwargs: Any,
    ):
        from hindsight_api.engine.response_models import ChunkInfo, MemoryFact, RecallResult  # noqa: I001

        route = self._route_from_kwargs(kwargs)
        wing = kwargs.pop("wing", None)
        room = kwargs.pop("room", None)
        hall = kwargs.pop("hall", None)
        closet = kwargs.pop("closet", None)
        drawer = kwargs.pop("drawer", None)
        tags = self._filter_tags(tags, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
        clean_query = self._normalize_query(query)

        if route in {SUMMARY_ROUTE, VERBATIM_ROUTE}:
            delegated = await self._delegate_route(
                route,
                "recall_async",
                self._route_bank_id(bank_id, route),
                clean_query,
                budget=budget,
                max_tokens=max_tokens,
                enable_trace=enable_trace,
                fact_type=fact_type,
                question_date=question_date,
                include_entities=include_entities,
                max_entity_tokens=max_entity_tokens,
                include_chunks=include_chunks,
                max_chunk_tokens=max_chunk_tokens,
                include_source_facts=include_source_facts,
                max_source_facts_tokens=max_source_facts_tokens,
                max_source_facts_tokens_per_observation=max_source_facts_tokens_per_observation,
                request_context=request_context,
                tags=tags,
                tags_match=tags_match,
                tag_groups=tag_groups,
            )
            normalized_results: list[MemoryFact] = []
            for fact in list(getattr(delegated, "results", []) or []):
                metadata = dict(getattr(fact, "metadata", {}) or {})
                document_id = getattr(fact, "document_id", None)
                chunk_id = getattr(fact, "chunk_id", None)
                if document_id is not None:
                    metadata.setdefault("document_id", str(document_id))
                if chunk_id is not None:
                    metadata.setdefault("chunk_id", str(chunk_id))
                metadata = self._fact_metadata(
                    metadata,
                    route=route,
                    fact_type=str(getattr(fact, "fact_type", "") or ""),
                )
                if self._is_ungrounded_derived(metadata):
                    continue
                normalized_results.append(
                    MemoryFact(
                        id=str(getattr(fact, "id", "")),
                        text=str(getattr(fact, "text", "") or ""),
                        fact_type=str(metadata.get("fact_type") or getattr(fact, "fact_type", "experience")),
                        entities=list(getattr(fact, "entities", []) or []),
                        context=getattr(fact, "context", None),
                        occurred_start=getattr(fact, "occurred_start", None),
                        occurred_end=getattr(fact, "occurred_end", None),
                        mentioned_at=getattr(fact, "mentioned_at", None),
                        document_id=document_id,
                        metadata=metadata,
                        chunk_id=str(chunk_id) if chunk_id is not None else None,
                        tags=list(getattr(fact, "tags", []) or []),
                        source_fact_ids=getattr(fact, "source_fact_ids", None),
                    )
                )
            return RecallResult(
                results=normalized_results,
                entities=dict(getattr(delegated, "entities", {}) or {}),
                chunks=dict(getattr(delegated, "chunks", {}) or {}),
            )

        summary_result = await self.summary_engine.recall_async(
            self.summary_bank_id(bank_id),
            clean_query,
            budget=budget,
            max_tokens=max_tokens,
            enable_trace=enable_trace,
            fact_type=fact_type,
            question_date=question_date,
            include_entities=include_entities,
            max_entity_tokens=max_entity_tokens,
            include_chunks=False,
            max_chunk_tokens=max_chunk_tokens,
            include_source_facts=include_source_facts,
            max_source_facts_tokens=max_source_facts_tokens,
            max_source_facts_tokens_per_observation=max_source_facts_tokens_per_observation,
            request_context=request_context,
            tags=tags,
            tags_match=tags_match,
            tag_groups=tag_groups,
        )
        verbatim_result = await self.verbatim_engine.recall_async(
            self.verbatim_bank_id(bank_id),
            clean_query,
            budget=budget,
            max_tokens=max_tokens,
            enable_trace=enable_trace,
            fact_type=fact_type,
            question_date=question_date,
            include_entities=include_entities,
            max_entity_tokens=max_entity_tokens,
            include_chunks=include_chunks,
            max_chunk_tokens=max_chunk_tokens,
            include_source_facts=include_source_facts,
            max_source_facts_tokens=max_source_facts_tokens,
            max_source_facts_tokens_per_observation=max_source_facts_tokens_per_observation,
            request_context=request_context,
            tags=tags,
            tags_match=tags_match,
            tag_groups=tag_groups,
        )
        fused = self._merge_ranked_results(summary_result.results, verbatim_result.results, n_results=10)

        results: list[MemoryFact] = []
        chunks: dict[str, ChunkInfo] = {}
        for idx, item in enumerate(fused):
            metadata = dict(item.metadata)
            chunk_id = metadata.get("chunk_id")
            document_id = metadata.get("document_id")
            fact_metadata = {
                "source_ref": str(item.ref),
                "providers": ",".join(item.providers),
                "summary_text": str(metadata.get("summary_text") or item.text),
                "verbatim_text": str(metadata.get("verbatim_text") or item.text),
                "chunk_id": str(chunk_id or ""),
                "document_id": str(document_id or ""),
                "fusion_route": FUSION_ROUTE,
                "memory_layer": str(metadata.get("memory_layer") or ""),
                "source_type": str(metadata.get("source_type") or ""),
                "artifact_type": str(metadata.get("artifact_type") or ""),
                "evidence_kind": str(metadata.get("evidence_kind") or ""),
                "provenance_ref": str(metadata.get("provenance_ref") or metadata.get("source_ref") or ""),
                "grounding_status": str(metadata.get("grounding_status") or ""),
                "derived_without_evidence": str(metadata.get("derived_without_evidence") or "false"),
            }
            results.append(
                MemoryFact(
                    id=f"fusion:{idx}:{item.ref}",
                    text=self._recall_fusion_text(clean_query, metadata, item.text),
                    fact_type=str(metadata.get("fact_type") or "experience"),
                    entities=[],
                    context=f"providers:{','.join(item.providers)}",
                    occurred_start=None,
                    occurred_end=None,
                    mentioned_at=metadata.get("filed_at") or metadata.get("event_date"),
                    document_id=document_id,
                    metadata=fact_metadata,
                    chunk_id=str(chunk_id) if chunk_id is not None else None,
                    tags=[],
                    source_fact_ids=None,
                )
            )

            if include_chunks and (verbatim_text := metadata.get("verbatim_text")):
                key = f"{document_id}_{chunk_id}" if document_id and chunk_id is not None else item.ref
                chunks[key] = ChunkInfo(
                    chunk_text=str(verbatim_text),
                    chunk_index=int(chunk_id) if str(chunk_id).isdigit() else idx,
                    truncated=False,
                )

        return RecallResult(
            results=results,
            entities=self._merge_entities(summary_result.entities, verbatim_result.entities),
            chunks=self._merge_chunks(verbatim_result.chunks, chunks) if include_chunks else {},
        )

    async def reflect_async(
        self,
        bank_id: str,
        query: str,
        *,
        request_context: Any,
        **kwargs: Any,
    ) -> Any:
        route = self._route_from_kwargs(kwargs)
        wing = kwargs.pop("wing", None)
        room = kwargs.pop("room", None)
        hall = kwargs.pop("hall", None)
        closet = kwargs.pop("closet", None)
        drawer = kwargs.pop("drawer", None)
        tags = self._filter_tags(kwargs.pop("tags", None), wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
        if route == VERBATIM_ROUTE:
            return await self.verbatim_engine.reflect_async(
                self.verbatim_bank_id(bank_id),
                self._normalize_query(query),
                request_context=request_context,
                tags=tags,
                **kwargs,
            )
        return await self.summary_engine.reflect_async(
            self.summary_bank_id(bank_id),
            self._normalize_query(query),
            request_context=request_context,
            tags=tags,
            **kwargs,
        )

    async def list_banks(self, *, request_context: Any) -> list[dict[str, Any]]:
        banks_by_id: dict[str, dict[str, Any]] = {}
        for route, banks in (
            (SUMMARY_ROUTE, await self.summary_engine.list_banks(request_context=request_context)),
            (VERBATIM_ROUTE, await self.verbatim_engine.list_banks(request_context=request_context)),
        ):
            for bank in banks:
                route_bank_id = str(bank.get("bank_id") or "")
                base_bank_id = self._base_bank_id(route_bank_id)
                merged = banks_by_id.setdefault(
                    base_bank_id,
                    {"bank_id": base_bank_id, "route_bank_ids": {}, "routes_present": []},
                )
                merged["route_bank_ids"][route] = route_bank_id
                merged["routes_present"] = self._dedupe_strings(list(merged["routes_present"]) + [route])
                if route == SUMMARY_ROUTE:
                    merged.update({k: v for k, v in bank.items() if k != "bank_id"})
                else:
                    for key, value in bank.items():
                        if key != "bank_id":
                            merged.setdefault(key, value)
        return list(banks_by_id.values())

    async def get_bank_profile(self, bank_id: str, *, request_context: Any) -> dict[str, Any]:
        summary_profile = await self.summary_engine.get_bank_profile(
            self.summary_bank_id(bank_id),
            request_context=request_context,
        )
        verbatim_profile = await self.verbatim_engine.get_bank_profile(
            self.verbatim_bank_id(bank_id),
            request_context=request_context,
        )
        return {
            **summary_profile,
            "bank_id": bank_id,
            "route_bank_ids": {
                SUMMARY_ROUTE: self.summary_bank_id(bank_id),
                VERBATIM_ROUTE: self.verbatim_bank_id(bank_id),
            },
            "routes_present": [SUMMARY_ROUTE, VERBATIM_ROUTE],
            "summary_profile": summary_profile,
            "verbatim_profile": verbatim_profile,
        }

    async def update_bank_disposition(
        self,
        bank_id: str,
        disposition: dict[str, Any],
        *,
        request_context: Any,
    ) -> dict[str, Any]:
        await self.summary_engine.update_bank_disposition(
            self.summary_bank_id(bank_id),
            disposition,
            request_context=request_context,
        )
        await self.verbatim_engine.update_bank_disposition(
            self.verbatim_bank_id(bank_id),
            disposition,
            request_context=request_context,
        )
        return await self.get_bank_profile(bank_id, request_context=request_context)

    async def set_bank_mission(self, bank_id: str, mission: str, *, request_context: Any) -> dict[str, Any]:
        await self.summary_engine.set_bank_mission(
            self.summary_bank_id(bank_id),
            mission,
            request_context=request_context,
        )
        await self.verbatim_engine.set_bank_mission(
            self.verbatim_bank_id(bank_id),
            mission,
            request_context=request_context,
        )
        return await self.get_bank_profile(bank_id, request_context=request_context)

    async def merge_bank_mission(self, bank_id: str, new_info: str, *, request_context: Any) -> dict[str, Any]:
        await self.summary_engine.merge_bank_mission(
            self.summary_bank_id(bank_id),
            new_info,
            request_context=request_context,
        )
        await self.verbatim_engine.merge_bank_mission(
            self.verbatim_bank_id(bank_id),
            new_info,
            request_context=request_context,
        )
        return await self.get_bank_profile(bank_id, request_context=request_context)

    async def update_bank(
        self,
        bank_id: str,
        *,
        name: str | None = None,
        mission: str | None = None,
        request_context: Any,
    ) -> dict[str, Any]:
        await self.summary_engine.update_bank(
            self.summary_bank_id(bank_id),
            name=name,
            mission=mission,
            request_context=request_context,
        )
        await self.verbatim_engine.update_bank(
            self.verbatim_bank_id(bank_id),
            name=name,
            mission=mission,
            request_context=request_context,
        )
        return await self.get_bank_profile(bank_id, request_context=request_context)

    async def delete_bank(self, bank_id: str, *, request_context: Any) -> dict[str, Any]:
        summary = await self.summary_engine.delete_bank(
            self.summary_bank_id(bank_id),
            request_context=request_context,
        )
        verbatim = await self.verbatim_engine.delete_bank(
            self.verbatim_bank_id(bank_id),
            request_context=request_context,
        )
        return {
            "success": bool(summary.get("success")) and bool(verbatim.get("success")),
            "bank_id": bank_id,
            "summary": summary,
            "verbatim": verbatim,
        }

    async def list_memory_units(
        self,
        *,
        bank_id: str,
        fact_type: str | None = None,
        search_query: str | None = None,
        limit: int = 50,
        offset: int = 0,
        request_context: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        route = self._route_from_kwargs(kwargs)
        wing = kwargs.pop("wing", None)
        room = kwargs.pop("room", None)
        hall = kwargs.pop("hall", None)
        closet = kwargs.pop("closet", None)
        drawer = kwargs.pop("drawer", None)
        tags = self._filter_tags(kwargs.pop("tags", None), wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
        if route in {SUMMARY_ROUTE, VERBATIM_ROUTE}:
            result = await self._delegate_route(
                route,
                "list_memory_units",
                self._route_bank_id(bank_id, route),
                fact_type=fact_type,
                search_query=search_query,
                limit=limit,
                offset=offset,
                request_context=request_context,
            )
            result["items"] = [self._annotate_route(item, route, bank_id=bank_id) for item in result.get("items", [])]
            result["items"] = [item for item in result["items"] if self._should_surface_item(item)]
            result["total"] = len(result["items"])
            if tags or any(value is not None for value in (wing, room, hall, closet, drawer)):
                result["items"] = [
                    item
                    for item in result["items"]
                    if (not tags or set(tags).issubset(set(item.get("tags") or [])))
                    and self._matches_loci_filters(item, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
                ]
                result["total"] = len(result["items"])
            return result

        summary_items = await self.summary_engine.list_memory_units(
            self.summary_bank_id(bank_id),
            fact_type=fact_type,
            search_query=search_query,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )
        verbatim_items = await self.verbatim_engine.list_memory_units(
            self.verbatim_bank_id(bank_id),
            fact_type=fact_type,
            search_query=search_query,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )
        items = [
            self._annotate_route(item, SUMMARY_ROUTE, bank_id=bank_id)
            for item in summary_items.get("items", [])
        ] + [
            self._annotate_route(item, VERBATIM_ROUTE, bank_id=bank_id)
            for item in verbatim_items.get("items", [])
        ]
        items = [item for item in items if self._should_surface_item(item)]
        if tags or any(value is not None for value in (wing, room, hall, closet, drawer)):
            items = [
                item
                for item in items
                if (not tags or set(tags).issubset(set(item.get("tags") or [])))
                and self._matches_loci_filters(item, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
            ]
        return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset}

    async def delete_memory_unit(self, bank_id: str, memory_unit_id: str, *, request_context: Any) -> dict[str, Any]:
        results = []
        errors = []
        for route in (SUMMARY_ROUTE, VERBATIM_ROUTE):
            try:
                results.append(
                    await self._delegate_route(
                        route,
                        "delete_memory_unit",
                        self._route_bank_id(bank_id, route),
                        memory_unit_id,
                        request_context=request_context,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{route}:{exc}")
        if not results:
            raise ValueError(f"Memory unit {memory_unit_id} not found in fusion bank {bank_id}: {'; '.join(errors)}")
        return {"bank_id": bank_id, "memory_unit_id": memory_unit_id, "routes": results, "errors": errors}

    async def get_graph_data(
        self,
        bank_id: str | None = None,
        fact_type: str | None = None,
        *,
        limit: int = 1000,
        q: str | None = None,
        tags: list[str] | None = None,
        tags_match: str = "all_strict",
        request_context: Any,
    ) -> dict[str, Any]:
        graph = await self.summary_engine.get_graph_data(
            self.summary_bank_id(bank_id) if bank_id else None,
            fact_type,
            limit=limit,
            q=q,
            tags=tags,
            tags_match=tags_match,
            request_context=request_context,
        )
        if bank_id:
            graph["bank_id"] = bank_id
        graph["routes_present"] = [SUMMARY_ROUTE, VERBATIM_ROUTE]
        return graph

    async def list_documents(
        self,
        bank_id: str,
        *,
        search_query: str | None = None,
        tags: list[str] | None = None,
        tags_match: Any = "any_strict",
        limit: int = 100,
        offset: int = 0,
        request_context: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        route = self._route_from_kwargs(kwargs)
        wing = kwargs.pop("wing", None)
        room = kwargs.pop("room", None)
        hall = kwargs.pop("hall", None)
        closet = kwargs.pop("closet", None)
        drawer = kwargs.pop("drawer", None)
        tags = self._filter_tags(tags, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
        if route in {SUMMARY_ROUTE, VERBATIM_ROUTE}:
            result = await self._delegate_route(
                route,
                "list_documents",
                self._route_bank_id(bank_id, route),
                search_query=search_query,
                tags=tags,
                tags_match=tags_match,
                limit=limit,
                offset=offset,
                request_context=request_context,
            )
            result["items"] = [
                self._annotate_document(item, route, bank_id=bank_id)
                for item in result.get("items", [])
            ]
            result["items"] = [item for item in result["items"] if self._should_surface_item(item)]
            result["total"] = len(result["items"])
            if any(value is not None for value in (wing, room, hall, closet, drawer)):
                result["items"] = [
                    item
                    for item in result["items"]
                    if self._matches_loci_filters(item, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
                ]
                result["total"] = len(result["items"])
            return result

        summary_docs = await self.summary_engine.list_documents(
            self.summary_bank_id(bank_id),
            search_query=search_query,
            tags=tags,
            tags_match=tags_match,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )
        verbatim_docs = await self.verbatim_engine.list_documents(
            self.verbatim_bank_id(bank_id),
            search_query=search_query,
            tags=tags,
            tags_match=tags_match,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )

        merged: dict[str, dict[str, Any]] = {}
        for route_name, result in ((SUMMARY_ROUTE, summary_docs), (VERBATIM_ROUTE, verbatim_docs)):
            for item in result.get("items", []):
                doc_id = str(item.get("id") or "")
                entry = merged.setdefault(
                    doc_id,
                    {
                        "id": doc_id,
                        "bank_id": bank_id,
                        "routes_present": [],
                        "route_documents": {},
                        "tags": [],
                        "memory_unit_count": 0,
                        "text_length": 0,
                    },
                )
                entry["routes_present"] = self._dedupe_strings(list(entry["routes_present"]) + [route_name])
                entry["route_documents"][route_name] = self._annotate_document(item, route_name, bank_id=bank_id)
                if not self._should_surface_item(entry["route_documents"][route_name]):
                    entry["route_documents"].pop(route_name, None)
                    if route_name in entry["routes_present"]:
                        entry["routes_present"] = [value for value in entry["routes_present"] if value != route_name]
                    continue
                entry["memory_unit_count"] = int(entry["memory_unit_count"]) + int(item.get("memory_unit_count") or 0)
                entry["text_length"] = max(int(entry["text_length"]), int(item.get("text_length") or 0))
                entry["tags"] = self._dedupe_strings(list(entry["tags"]) + list(item.get("tags") or []))
                for key in ("content_hash", "created_at", "updated_at", "retain_params", "document_metadata"):
                    if item.get(key) is not None and entry.get(key) in (None, [], {}, ""):
                        entry[key] = item.get(key)

        items = list(merged.values())
        items = [item for item in items if item.get("route_documents")]
        if any(value is not None for value in (wing, room, hall, closet, drawer)):
            items = [
                item
                for item in items
                if any(
                    self._matches_loci_filters(doc, wing=wing, room=room, hall=hall, closet=closet, drawer=drawer)
                    for doc in item.get("route_documents", {}).values()
                )
            ]
        return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset}

    async def get_document(self, document_id: str, bank_id: str, *, request_context: Any) -> dict[str, Any] | None:
        summary_doc = await self.summary_engine.get_document(
            document_id,
            self.summary_bank_id(bank_id),
            request_context=request_context,
        )
        verbatim_doc = await self.verbatim_engine.get_document(
            document_id,
            self.verbatim_bank_id(bank_id),
            request_context=request_context,
        )
        if summary_doc is None and verbatim_doc is None:
            return None

        primary = dict(summary_doc or verbatim_doc or {})
        primary["id"] = document_id
        primary["bank_id"] = bank_id
        primary["routes_present"] = [
            route
            for route, doc in ((SUMMARY_ROUTE, summary_doc), (VERBATIM_ROUTE, verbatim_doc))
            if doc is not None
        ]
        primary["route_documents"] = {
            route: self._annotate_document(doc, route, bank_id=bank_id)
            for route, doc in ((SUMMARY_ROUTE, summary_doc), (VERBATIM_ROUTE, verbatim_doc))
            if doc is not None
        }
        primary["route_documents"] = {
            route: doc for route, doc in primary["route_documents"].items() if self._should_surface_item(doc)
        }
        primary["routes_present"] = [
            route for route in primary["routes_present"] if route in primary["route_documents"]
        ]
        if not primary["route_documents"]:
            return None
        if verbatim_doc and verbatim_doc.get("original_text"):
            primary["original_text"] = verbatim_doc["original_text"]
        primary["memory_unit_count"] = sum(
            int((doc or {}).get("memory_unit_count") or 0) for doc in (summary_doc, verbatim_doc)
        )
        primary["tags"] = self._dedupe_strings(
            list((summary_doc or {}).get("tags") or []) + list((verbatim_doc or {}).get("tags") or [])
        )
        return primary

    async def delete_document(self, document_id: str, bank_id: str, *, request_context: Any) -> dict[str, int]:
        summary = await self.summary_engine.delete_document(
            document_id,
            self.summary_bank_id(bank_id),
            request_context=request_context,
        )
        verbatim = await self.verbatim_engine.delete_document(
            document_id,
            self.verbatim_bank_id(bank_id),
            request_context=request_context,
        )
        return {
            "documents_deleted": int(summary.get("documents_deleted", 0)) + int(verbatim.get("documents_deleted", 0)),
            "memory_units_deleted": int(summary.get("memory_units_deleted", 0)) + int(verbatim.get("memory_units_deleted", 0)),
            "links_deleted": int(summary.get("links_deleted", 0)) + int(verbatim.get("links_deleted", 0)),
            "observations_invalidated": int(summary.get("observations_invalidated", 0))
            + int(verbatim.get("observations_invalidated", 0)),
        }

    async def get_chunk(self, chunk_id: str, *, request_context: Any) -> dict[str, Any] | None:
        chunk = await self._primary_then_secondary(
            VERBATIM_ROUTE,
            SUMMARY_ROUTE,
            "get_chunk",
            chunk_id,
            request_context=request_context,
        )
        if chunk:
            chunk["bank_id"] = self._base_bank_id(str(chunk.get("bank_id") or ""))
            chunk["fusion_route"] = (
                VERBATIM_ROUTE if "__verbatim" in str(chunk.get("chunk_id") or "") else SUMMARY_ROUTE
            )
        return chunk

    async def list_entities(
        self,
        bank_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        request_context: Any,
    ) -> dict[str, Any]:
        return await self.summary_engine.list_entities(
            self.summary_bank_id(bank_id),
            limit=limit,
            offset=offset,
            request_context=request_context,
        )

    async def get_entity_state(
        self,
        bank_id: str,
        entity_id: str,
        entity_name: str,
        *,
        request_context: Any,
    ) -> Any:
        return await self.summary_engine.get_entity_state(
            self.summary_bank_id(bank_id),
            entity_id,
            entity_name,
            request_context=request_context,
        )

    async def get_bank_stats(self, bank_id: str, *, request_context: Any) -> dict[str, Any]:
        summary = await self.summary_engine.get_bank_stats(
            self.summary_bank_id(bank_id),
            request_context=request_context,
        )
        verbatim = await self.verbatim_engine.get_bank_stats(
            self.verbatim_bank_id(bank_id),
            request_context=request_context,
        )
        return {
            "bank_id": bank_id,
            "summary": summary,
            "verbatim": verbatim,
            "node_counts": {
                key: int(summary.get("node_counts", {}).get(key, 0)) + int(verbatim.get("node_counts", {}).get(key, 0))
                for key in set(summary.get("node_counts", {})) | set(verbatim.get("node_counts", {}))
            },
            "operations": {
                key: int(summary.get("operations", {}).get(key, 0)) + int(verbatim.get("operations", {}).get(key, 0))
                for key in set(summary.get("operations", {})) | set(verbatim.get("operations", {}))
            },
            "total_documents": int(summary.get("total_documents", 0)) + int(verbatim.get("total_documents", 0)),
            "pending_consolidation": int(summary.get("pending_consolidation", 0))
            + int(verbatim.get("pending_consolidation", 0)),
        }

    async def get_entity(self, bank_id: str, entity_id: str, *, request_context: Any) -> dict[str, Any] | None:
        return await self.summary_engine.get_entity(
            self.summary_bank_id(bank_id),
            entity_id,
            request_context=request_context,
        )

    async def list_operations(
        self,
        bank_id: str,
        *,
        status: str | None = None,
        task_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
        request_context: Any,
    ) -> dict[str, Any]:
        summary = await self.summary_engine.list_operations(
            self.summary_bank_id(bank_id),
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )
        verbatim = await self.verbatim_engine.list_operations(
            self.verbatim_bank_id(bank_id),
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )
        operations = []
        for route, payload in ((SUMMARY_ROUTE, summary), (VERBATIM_ROUTE, verbatim)):
            for operation in payload.get("operations", []):
                op = dict(operation)
                op["fusion_route"] = route
                operations.append(op)
        operations.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {"total": len(operations), "operations": operations[offset : offset + limit]}

    async def cancel_operation(
        self,
        bank_id: str,
        operation_id: str,
        *,
        request_context: Any,
    ) -> dict[str, Any]:
        results = []
        errors = []
        for route in (SUMMARY_ROUTE, VERBATIM_ROUTE):
            try:
                results.append(
                    await self._delegate_route(
                        route,
                        "cancel_operation",
                        self._route_bank_id(bank_id, route),
                        operation_id,
                        request_context=request_context,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{route}:{exc}")
        if not results:
            raise ValueError(f"Operation {operation_id} not found in fusion bank {bank_id}: {'; '.join(errors)}")
        return {"success": True, "bank_id": bank_id, "operation_id": operation_id, "routes": results, "errors": errors}

    async def list_mental_models_consolidated(
        self,
        *,
        bank_id: str,
        tags: list[str] | None = None,
        tags_match: str = "any",
        limit: int = 100,
        offset: int = 0,
        request_context: Any,
    ) -> list[dict[str, Any]]:
        return await self.summary_engine.list_mental_models_consolidated(
            bank_id=self.summary_bank_id(bank_id),
            tags=tags,
            tags_match=tags_match,
            limit=limit,
            offset=offset,
            request_context=request_context,
        )
