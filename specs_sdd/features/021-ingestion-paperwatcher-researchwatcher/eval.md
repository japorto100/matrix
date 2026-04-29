---
title: Ingestion Paperwatcher Eval
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Eval

## Parser Candidates

- PyMuPDF4LLM: fast baseline.
- Microsoft MarkItDown: lightweight broad-format Markdown baseline.
- Docling: primary SOTA candidate.
- MinerU: complex/scanned PDF candidate if resources allow.

## Metrics

- Text token recall against ground-truth Markdown.
- Heading hierarchy preservation.
- Page anchor/citation correctness.
- Source artifact/chunk citation correctness.
- Table extraction and table-boundary preservation.
- Figure/image reference preservation.
- Formula/code-block preservation.
- Parser latency and memory footprint.

## Promotion Rule

A parser/chunking config can become default only if it improves retrieval QA or
source/citation quality, not merely raw text extraction.

2026 decision evidence has priority. Older parser papers can justify a
candidate, but the default must be chosen by current official repo state and
Matrix benchmark results.
