"""KG Pipeline FastAPI Worker (Port 8099) — Phase 2 STUB.

In Phase 1 this server returns 503 on all extract calls. To activate, follow
the instructions in pyproject.toml.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Matrix KG Pipeline Worker",
    description="(Phase 2 SKELETON — see kg_pipeline/README.md)",
    version="0.1.0",
)


class ExtractRequest(BaseModel):
    text: str
    doc_id: str = ""


@app.get("/health")
async def health() -> dict:
    return {
        "status": "skeleton",
        "phase": "1",
        "message": "kg_pipeline is a skeleton — see kg_pipeline/README.md to activate Phase 2",
    }


@app.post("/extract")
async def extract(req: ExtractRequest) -> dict:
    raise HTTPException(
        status_code=503,
        detail=(
            "kg_pipeline not yet activated. See kg_pipeline/README.md for "
            "Phase 2 activation steps."
        ),
    )
