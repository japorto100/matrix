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

2026-04-29 implementation note: Feature 022 now carries static handoff canaries
for the Z-derived consumers:

- semantic handoff from `Z_Semantik_layer and so on.md`: catalog version, term
  ids and metric id must survive on selected references.
- visual handoff from `Z_Chatgpt_Chronicles vs DeepseekOCRpaper.md`: page,
  bbox, block type, OCR confidence and image checksum must survive.
- report handoff from `Z_Tool_very interessting Quarkdown.md`: report manifest
  id, output path and renderer must remain attached to citations.

These are metadata contracts for Matrix ingestion/retrieval. They do not make
Docling, MinerU, MarkItDown, Quarkdown or any LLM provider mandatory defaults.

2026-04-29 parser-candidate note: Meta-Harness extraction artifacts now expose
parser profiles and chunker candidate spaces directly. PyMuPDF4LLM is the
baseline, MarkItDown is an optional lightweight conversion candidate, Docling
is the layout-rich SOTA candidate, and MinerU is a heavy complex/scanned PDF
candidate. Promotion still depends on local benchmark evidence and resource
fit, not on project popularity.

## 2026-04-30 Ingestion Runtime Transfer

Inputs: Feature 033, Feature 019, Feature 027 and the Z_ source-grounding pass.

Ingestion runs should emit runtime events for parser selected, chunker version,
source artifact id, citation/page anchors, vector/KG projection and downstream
artifact readiness. This lets Agent Chat and Control UI show whether a document
is actually usable by RAG/KG/report flows instead of only showing "uploaded".

The event payload should link to manifests and source refs, not inline large
document content.
