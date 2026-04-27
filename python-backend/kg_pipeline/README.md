# Matrix KG Extraction Pipeline (Venv 3)

**Status:** Lightweight extractor active. ML extractors remain opt-in.

## Purpose

Extract entity/relation candidates from text chunks and forward them toward
the global KG claim/projection pipeline. The first backend/projection target is
NornicDB/nonicdb, not FalkorDB. The base service uses a deterministic heuristic
extractor so it runs on weak local hardware without downloading large models.

## Why a separate venv?

Optional ReLiK/GLiREL/GraphMERT-style extractors pull large ML dependencies and
may pin different Torch versions. The base worker therefore stays separate and
lightweight, while ML extractors are optional extras.

## Architecture

```
text → preprocessors (section split, sentences)
     → extractors (heuristic now; relik+glirel/gliner+glirel later)
     → filters (confidence, type allow-list)
     → normalizers (predicate mapper, entity canonical)
     → sinks (claim proposal → Postgres source of truth → NornicDB projection)
```

Same Phase-based subfolder pattern as `ingestion/` and `retrieval/`.

## Adoption sources (paperwatcher)

| Target | Source |
|---|---|
| `extractors/relik_glirel.py` | `paperwatcher/kg-module/kg_module/extraction.py` |
| `preprocessors/section_splitter.py` | `paperwatcher/kg-module/kg_module/text_pipeline.py` |
| `normalizers/predicate_mapper.py` | `paperwatcher/kg-module/kg_module/predicate_mapper.py` |
| `core/config.py` | `paperwatcher/kg-module/kg_module/config.py` |
| `schema/` | `paperwatcher/kg-module/kg_module/schema.py` + `shared_schema.py` |

## Activation

```bash
cd python-backend/kg_pipeline
uv venv
uv sync

# In python-backend/ingestion/.env (or python-backend/.env):
# KG_PIPELINE_ENABLED=true

uv run uvicorn kg_pipeline.server:app --host 127.0.0.1 --port 8099
```

After activation, every chunk that the ingestion-worker processes is also
forwarded to this worker for entity/relation candidate extraction. Persisted
KG claims and the NornicDB projection are owned by Feature 017.

## Decoupling rules (D17)

- May import shared data contracts only when needed
- MUST NOT import `agent.*`, `ingestion.*`, `retrieval.*`
- Communication with main venv: HTTP only (called from `ingestion/sinks/kg_sink.py`)
