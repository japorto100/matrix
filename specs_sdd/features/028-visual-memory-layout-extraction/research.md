---
title: Visual Memory Layout Extraction Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 028
---

# Research

## Local Z Reference

Derived from `Z_Chatgpt_Chronicles vs DeepseekOCRpaper.md`.

## Working Judgement

Two ideas must stay separate:

- Screen/document images as evidence for building textual memories.
- Optical compression as an experimental representation for old context.

Matrix should implement the first with strong provenance and treat the second
as research-only until local benchmarks prove recall, cost and safety.

## Source Check 2026-04-29

- DeepSeek-OCR / Contexts Optical Compression argues that text rendered as
  images can sometimes be represented with fewer vision tokens and discusses
  old-context compression/forgetting. This is interesting, but not a production
  memory store by itself.
- Chronicle-like workflows show a practical pattern: capture screen context,
  extract/OCR/summarize, then store local text memory with provenance.
- Existing document-layout tools remain necessary because tables, formulas and
  coordinates matter for RAG/KG citation quality.

## Design Consequence

Start with evidence-backed visual memory:

```text
capture -> OCR/layout -> source-linked blocks -> summary -> memory/RAG search
  -> optional KG claim proposal
```

Optical compression can be a candidate in Feature 023/Meta-Harness later, not a
default memory format.
