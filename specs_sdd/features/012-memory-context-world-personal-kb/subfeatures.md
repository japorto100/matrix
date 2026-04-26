---
title: Memory Umbrella Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
feature_id: 012
---

# Subfeatures

## 012.1 Personal Raw Evidence

Status: partially built.

Scope:

- chat turns, tool outputs and scratch notes as evidence.
- raw user input marked as evidence source, not truth.
- agent output marked secondary artifact.
- verbatim evidence surface through `memory_fusion`.

Open:

- durable `verbatim_store` schema.
- async write/latency optimization.
- PII/deletion path across hot/warm/cold tiers.

## 012.2 Personal Derived Memory

Status: partially built.

Scope:

- observations, preferences and mental models.
- Hindsight retain/recall/reflect/consolidate.
- `memory_fusion` derived objects with provenance/source backlinks.
- coherence handling for multi-agent writes.

Open:

- explicit DB-level source attribution/status fields.
- contradiction detection and promotion workflow.
- MemoryAccessPolicy by agent/consumer.

## 012.3 Memory Evaluation And Fusion

Status: active.

Scope:

- Hindsight runner.
- MemPalace runner.
- shared corpus/queries.
- `memory_ab` persistence.
- `memory_fusion` Postgres runtime path.
- long-context smoke with summary/verbatim/fusion routes.

Open:

- no productive hybrid fallback until eval on real data is complete.
- public benchmark adapters need real dataset downloads.
- four-layer metric stack: task, retrieval quality, efficiency, governance.

## 012.4 Runtime Context

Status: partially built.

Scope:

- prompt block order: stable policy/tools/skills before dynamic context.
- model-relative thresholds: 80% pre-save, 85% compaction, 95% emergency.
- `pre_compression` event contract.
- ContextTab and runtime inspector metadata.
- provider prompt cache via LiteLLM and sticky-routing consideration.

Open:

- per-model thresholds via harness/meta-regression.
- full visible provenance/degradation flags in Agent Chat message body.
- prompt-layout regression against cache-hit/cost metrics.

## 012.5 Global World Evidence And Claim Inputs

Status: planned.

Scope:

- global evidence records.
- claim input records before KG promotion.
- world degradation flags.
- evidence-joined answer-time adjudication.
- handoff contract to Feature 017 for bitemporal KG claims, graph projection,
  status machine and decay retrieval.

Open:

- evidence/claim source schema.
- claim proposal contract into Feature 017.
- IE pipeline adapted from Researchwatcher to trading/geopolitics/macro.
- validator contract before KG promotion.

## 012.6 Personal Knowledgebase

Status: planned.

Scope:

- saved articles, PDFs, webclips, transcripts, notes, highlights.
- KB inbox/library/document/note surfaces.
- KB-specific retrieval policy.
- Recall/Trilium-inspired capture and curation patterns.

Open:

- KB namespace/store.
- capture/import flows.
- annotation/link schema.
- bridge rules to memory and world entities.

## 012.7 Control Surfaces

Status: partial.

Scope:

- MemoryHealthCards.
- MemoryRuntimeInspector.
- ContextTab.
- API BFFs for memory/control.

Open:

- Personal KB detail surfaces.
- World claim/status/conflict surfaces.
- live verify that UI uses backend responses, not mock fallbacks.
