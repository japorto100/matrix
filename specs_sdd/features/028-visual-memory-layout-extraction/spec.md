---
title: Visual Memory Layout Extraction
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 028
---

# Visual Memory Layout Extraction

## Current State / Ist

Matrix has memory providers, KG claims, ingestion and RAG pipelines, but visual
context is treated mostly as screenshots, OCR input or future multimodal work.
The Z_ notes highlight a deeper possibility: screen/document history can be
converted into structured memories, and optical compression can become an
experimental memory representation.

## Target State / Soll

Feature 028 owns visual memory and layout extraction:

- screenshot/document image capture as evidence, not automatic truth;
- OCR/layout extraction into markdown, blocks, tables and coordinates;
- visual memory summaries linked to source frames and paths;
- optional optical-compression experiments for old context;
- decay/forgetting policy that reduces detail while retaining provenance;
- Meta-Harness scenarios that verify visual memory does not hallucinate hidden
  state.

## Boundaries

- Feature 012 owns personal memory/context.
- Feature 017 owns promoted global/domain KG claims.
- Feature 021 owns ingestion and parser pipelines.
- Feature 019 owns answer-time retrieval.

Feature 028 owns visual/screen/layout memory extraction and compression
experiments.

## Closeout Criteria

- Visual captures have consent, retention and provenance.
- OCR/layout outputs retain source coordinates and confidence.
- Visual memories are searchable without becoming unsourced KG claims.
- Optical compression remains experimental behind explicit gates.
- Meta-Harness covers visual recall, stale visual memory and unsupported claim
  cases.
