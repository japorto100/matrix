"""KG Pipeline FastAPI Worker (Port 8099)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from kg_pipeline.extractors import extract_heuristic
from kg_pipeline.sinks.global_kg import proposals_from_extraction
from memory_engine.global_kg_store import create_global_kg_store
from pydantic import BaseModel, Field

app = FastAPI(
    title="Matrix KG Pipeline Worker",
    description="Lightweight KG candidate extraction for Matrix ingestion",
    version="0.1.0",
)


class ExtractRequest(BaseModel):
    text: str
    doc_id: str = ""


class ProposeRequest(ExtractRequest):
    source_uri: str | None = None
    persist: bool = False
    evidence_metadata_by_ref: dict[str, dict[str, object]] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "phase": "1.5",
        "extractor": "heuristic",
        "projection_target": "nornicdb",
    }


@app.post("/extract")
async def extract(req: ExtractRequest) -> dict:
    result = extract_heuristic(req.text, req.doc_id)
    return asdict(result)


@app.post("/propose")
async def propose(req: ProposeRequest) -> dict:
    result = extract_heuristic(req.text, req.doc_id)
    proposals = proposals_from_extraction(
        result,
        source_uri=req.source_uri,
        evidence_metadata_by_ref=req.evidence_metadata_by_ref,
    )
    persisted: list[str] = []
    degraded_reasons: list[str] = []

    if req.persist and proposals:
        try:
            store = create_global_kg_store()
            for proposal in proposals:
                persisted.append(store.propose_claim(proposal))
        except Exception as exc:  # noqa: BLE001
            degraded_reasons.append(f"GLOBAL_KG_STORE_UNAVAILABLE:{type(exc).__name__}")

    return {
        "doc_id": result.doc_id,
        "extractor": result.extractor,
        "proposal_count": len(proposals),
        "proposals": [proposal.projection_payload() for proposal in proposals],
        "persisted_claim_ids": persisted,
        "degraded": bool(degraded_reasons),
        "degraded_reasons": degraded_reasons,
    }
