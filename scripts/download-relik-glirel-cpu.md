# CPU-only notes for KG Pipeline models (Phase 2)

This repository keeps the KG pipeline (`python-backend/kg_pipeline/`) **disabled by default**
because it pulls in large deps (notably `torch==2.3.1`) and may require additional model downloads.

## Goal

Make it possible to run the KG pipeline on CPU, but only when explicitly enabled.

## What to do (opt-in)

1. Activate the KG pipeline venv:

```bash
cd python-backend/kg_pipeline
uv venv
uv sync
```

2. Install a small spaCy model (CPU):

```bash
python -m spacy download en_core_web_sm
```

3. Start the worker:

```bash
uv run uvicorn kg_pipeline.server:app --host 127.0.0.1 --port 8099
```

4. Enable ingestion forwarding:

Set (in `python-backend/.env` or `python-backend/ingestion/.env`):

```bash
KG_PIPELINE_ENABLED=true
KG_PIPELINE_URL=http://127.0.0.1:8099
```

## Notes

- The KG pipeline is designed to be **decoupled** (HTTP boundary). If it’s down, ingestion should still work.
- Prefer keeping this disabled on weak machines; run it in Cursor Cloud or a dedicated box if needed.

