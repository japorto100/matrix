"""Heavy Extraction FastAPI Worker (Port 8101) — Phase 2 STUB.

In Phase 1 this server returns 503 on all extract calls. To activate, follow
the instructions in pyproject.toml.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Matrix Heavy Extraction Worker",
    description="(Phase 2 SKELETON — see extraction_layout/pyproject.toml)",
    version="0.1.0",
)


class ExtractRequest(BaseModel):
    file_url: str  # signed URL from Go Storage Gateway
    backend: str = "docling"  # docling | marker | mineru
    doc_id: str = ""


@app.get("/health")
async def health() -> dict:
    return {
        "status": "skeleton",
        "phase": "1",
        "available_backends": [],
        "message": "extraction_layout is a skeleton — see pyproject.toml to activate Phase 2",
    }


@app.post("/extract")
async def extract(req: ExtractRequest) -> dict:
    raise HTTPException(
        status_code=503,
        detail=(
            "extraction_layout not yet activated. See extraction_layout/pyproject.toml "
            "for Phase 2 activation steps."
        ),
    )
