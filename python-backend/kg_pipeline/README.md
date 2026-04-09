# Matrix KG Extraction Pipeline (Venv 3)

**Status:** Skeleton (Phase 2 not yet activated). See `pyproject.toml` and
`specs/execution/exec-15-memory-control-ui.md` §5.7.

## Purpose

Extract entities and relations from text chunks using ReLiK (Entity Linking) +
GLiREL (Relation Extraction) and write them to the Kuzu Knowledge Graph
(via `memory_engine/kg_store.py`).

## Why a separate venv?

ReLiK pins `torch==2.3.1`. The main agent venv uses a newer torch via
sentence-transformers. Sharing a venv would cause dep conflicts.

## Architecture

```
text → preprocessors (section split, sentences)
     → extractors (relik+glirel, gliner+glirel)
     → filters (confidence, type allow-list)
     → normalizers (predicate mapper, entity canonical)
     → sinks (kuzu_sink → memory_engine/kg_store.py)
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

## Activation (Phase 2)

```bash
cd python-backend/kg_pipeline
uv venv
uv sync                                # ~2 GB download
python -m spacy download en_core_web_sm

# In python-backend/ingestion/.env (or python-backend/.env):
# KG_PIPELINE_ENABLED=true

uv run uvicorn kg_pipeline.server:app --host 127.0.0.1 --port 8099
```

After activation, every chunk that the ingestion-worker processes is also
forwarded to this worker for entity extraction. The extracted nodes/edges
land in Kuzu and become visible in the control-ui Trading KG view.

## Decoupling rules (D17)

- May import `memory_engine.*` (shared data layer)
- MUST NOT import `agent.*`, `ingestion.*`, `retrieval.*`
- Communication with main venv: HTTP only (called from `ingestion/sinks/kg_sink.py`)
