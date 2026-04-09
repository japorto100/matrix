# Matrix Heavy Extractors (Venv 3)

**Status:** Skeleton (Phase 2 not yet activated). See `pyproject.toml`.

## Why a separate venv?

Heavy PDF extractors have transitive dependencies that conflict with
`hindsight-api-slim` (which lives in the ingestion venv):

- **marker-pdf** pins `pillow<11`, hindsight wants `pillow>=12.1.1`
- **docling** pulls in big torch/transformers stacks
- **mineru** needs ~2.5 GB VLM models
- **colpali** needs visual embedding models

Putting them in `python-backend/ingestion/.venv` would make the resolver
unsatisfiable (we hit this on first `uv sync` of ingestion). The clean
solution — same as paperwatcher's `layout-module/` — is a separate venv
that exposes an HTTP `/extract` endpoint. The ingestion-worker calls it
when a PDF needs a high-quality backend.

## Architecture

```
ingestion-worker (Venv 2, Port 8098)
    │
    ├─ pymupdf4llm (in-process, fast, default for most PDFs)
    │
    └─ POST /extract → extraction_layout (Venv 3, Port 8101)
                         │
                         ├─ docling
                         ├─ marker-pdf
                         ├─ mineru        (optional, ~2.5 GB VLM)
                         └─ colpali       (optional, visual indexing)
```

The HTTP boundary means each side has its own pillow/torch versions and
they never need to be unified.

## Adoption sources (paperwatcher)

| Target | Source |
|---|---|
| `extractors/docling_ext.py` | `paperwatcher/paperwatcher/core/doc_extractor/docling_ext.py` |
| `extractors/marker_ext.py` | `paperwatcher/paperwatcher/core/doc_extractor/marker_ext.py` |
| `extractors/mineru_ext.py` | `paperwatcher/paperwatcher/core/doc_extractor/mineru_ext.py` (optional) |
| `extractors/spacy_layout_chunker.py` | `paperwatcher/paperwatcher/core/doc_extractor/spacy_layout_chunker.py` |

## Activation (Phase 2)

```bash
cd python-backend/extraction_layout
uv venv
uv sync                                # 1-2 GB downloads
python -m spacy download en_core_web_sm

# In python-backend/ingestion/.env:
# EXTRACTION_LAYOUT_URL=http://127.0.0.1:8101
# EXTRACTION_LAYOUT_ENABLED=true

uv run uvicorn extraction_layout.worker:app --host 127.0.0.1 --port 8101
```

After activation, the ingestion-worker's extractor registry will route
specific mime types (or extractor names like `docling`/`marker`) to this
worker via HTTP.

## Decoupling rules (D17)

- May import: own modules + `memory_engine.*` (if writing directly to a sink)
- MUST NOT import: `agent.*`, `ingestion.*`, `retrieval.*`, `kg_pipeline.*`
- Communication: HTTP only
