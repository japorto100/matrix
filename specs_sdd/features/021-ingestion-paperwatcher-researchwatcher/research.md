---
title: Ingestion Paperwatcher Research
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
---

# Research Notes

Researchwatcher is useful mostly as workflow evidence: it shows how a
paper-focused research product can combine download/search/synthesis/citation
flows and expose them through tests/API/MCP surfaces. Matrix should adopt the
workflow shape, not the whole product architecture.

The important design point is separation:

- ingestion preserves source truth.
- retrieval ranks chunks and citations.
- KG promotion creates bitemporal world/domain claims only after evidence
  gates.
- memory may reference user sessions and prior work, but it is not a document
  ingestion source of truth.

## 2026-04-27 Parser / Paper Pipeline Update

Researchwatcher/Paperwatcher is a useful workflow reference, but it is not the
whole SOTA ingestion answer anymore. Matrix should keep the paper workflow
shape and modernize the parser/chunking layer.

Primary parser candidates:

- PyMuPDF4LLM: current fast baseline and good enough for many text PDFs.
- Microsoft MarkItDown: lightweight document-to-Markdown baseline for broad
  Office/PDF/HTML/media inputs and LLM-oriented ingestion. It is attractive as
  a simple adapter and MCP-adjacent utility, but it must be benchmarked for
  layout, tables, formulas and citation anchors before replacing specialized
  parsers.
- Docling: first serious SOTA candidate for broad document parsing. It supports
  PDF/DOCX/PPTX/XLSX/HTML/images/audio/LaTeX/plain text, layout/reading order,
  tables, code, formulas, OCR, lossless JSON and MCP integration.
- MinerU: heavy candidate for complex/scanned PDFs and formula/layout-rich
  documents. Good to evaluate, but resource/latency constraints matter on this
  machine.

Important 2026 paper finding: `arXiv:2604.04948` reports that metadata
enrichment and hierarchy-aware chunking contributed more to downstream QA than
the parser choice alone. Therefore Feature 021 should not only swap extractors;
it must also preserve section hierarchy, page anchors,
table/figure/code/formula block types and citation metadata.

Date discipline:

- 2026 papers and current official project docs are decision evidence.
- 2025/2024 papers are method/tool references only unless current project
  releases and our benchmarks show they are still competitive.
- Current local SOTA evidence set includes `arXiv:2604.04948` and
  `arXiv:2602.11960`; older Docling, MinerU, LightRAG and AutoRAG papers must
  not be presented as 2026 SOTA by publication date.

For financial/trading sources, prefer structured formats when available:
XBRL/CSV/API payloads should not be degraded through PDF parsing unless the PDF
is the only source.

## 2026-04-29 Z_ Follow-Up

`Z_Chatgpt_Chronicles vs DeepseekOCRpaper.md` reinforces that layout and visual
coordinates are evidence, not decoration. Feature 021 should preserve source
artifact, page, block and coordinate metadata so Feature 028 visual memory and
Feature 019 retrieval can cite exact regions.

`Z_Tool_very interessting Quarkdown.md` adds a report-publishing consumer:
Feature 027 should reference ingestion artifacts instead of copying unverifiable
text into generated reports.
