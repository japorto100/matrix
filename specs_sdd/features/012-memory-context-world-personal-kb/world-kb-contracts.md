---
title: World Model and Personal KB Contracts
status: accepted
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 012
---

# World Model and Personal KB Contracts

This file closes the active design tasks that must be clear before code work:
IE types, claim status, promotion/demotion, answer-time flow and Personal KB
capture/import/annotation surfaces.

## World IE Types

Entity types for the first trading/geopolitics/macro slice:

- `asset`: ticker, ISIN, crypto symbol, commodity, index.
- `organization`: company, exchange, central bank, regulator, government body.
- `person`: executive, policymaker, analyst, fund manager.
- `event`: earnings, macro release, policy decision, geopolitical event,
  corporate action, exploit/outage.
- `place`: country, region, exchange venue, supply-chain location.
- `indicator`: CPI, payrolls, PMI, rates, yields, volatility, liquidity,
  on-chain metric.

Relation types:

- `mentions`: weak extraction link from evidence span to entity.
- `supports`: evidence supports a normalized claim.
- `contradicts`: evidence contradicts a normalized claim.
- `updates`: newer evidence supersedes prior evidence or claim state.
- `causes_or_influences`: explicit causal or influence relation with source.
- `located_in`, `issued_by`, `affects`, `reports_value`.

Source types:

- `filing`, `official_release`, `news`, `market_data`, `research_note`,
  `transcript`, `social`, `user_note`, `agent_analysis`.

Every extracted entity/relation/source record carries `source_ref`,
`provenance_ref`, `extractor`, `extracted_at`, `confidence` and raw span
coordinates where available.

## Claim Status Machine

Allowed claim statuses:

- `candidate`: extracted but not trusted for LLM answers without caveat.
- `supported`: at least one reliable evidence link supports the claim and no
  stronger contradiction is active.
- `contested`: supported and contradicted evidence both exist.
- `deprecated`: newer evidence or policy marks the claim obsolete.
- `retracted`: source-level retraction or explicit correction exists.

Degradation flags:

- `NO_WORLD_EVIDENCE`: answer has no world evidence layer.
- `NO_WORLD_KG`: no structured KG/entity support was available.
- `WORLD_CLAIM_CANDIDATE_ONLY`: only candidate claims were available.
- `WORLD_CLAIM_CONFLICT`: contested or contradictory evidence was available.
- `WORLD_CLAIM_STALE`: latest supporting evidence is outside freshness policy.
- `WORLD_SOURCE_LOW_CONFIDENCE`: source confidence below answer threshold.

## Promotion/Demotion Gate

Promotion to `supported` requires:

- normalized claim text and stable entity keys.
- at least one `supports` evidence link with `source_confidence >= 0.6`.
- source timestamp, source type and provenance reference present.
- no active `contradicts` link from a higher-confidence source.

Demotion rules:

- `supported -> contested` when a contradiction with comparable confidence is
  linked.
- `supported|contested -> deprecated` when newer evidence supersedes the claim.
- `any -> retracted` when source correction/retraction exists.

Audit trail:

- every transition records previous status, next status, reason,
  `evidence_ids`, actor (`extractor`, `agent`, `human`) and timestamp.
- answer-time composition must expose degradation flags instead of silently
  hiding contested/degraded context.

## Answer-Time Flow

The answer path is:

1. `Retrieve`: pull personal memory, Personal KB, world evidence and world KG
   candidates under context policy caps.
2. `Normalize`: map aliases, entity ids, source refs and status fields into
   canonical context blocks.
3. `Adjudicate`: apply claim status, evidence confidence, freshness and
   contradiction rules; produce degradation flags.
4. `Compose`: render answer context with provenance labels and caveats. Candidate
   or contested claims may inform uncertainty, but cannot be stated as facts
   without status disclosure.

## Personal KB Capture Flows

YouTube/podcast transcript capture:

- input: URL, optional title/channel/date, transcript text or transcript fetcher
  result.
- store as `kb_document.source_type = transcript`, with chunks carrying time
  offsets when available.
- retrieval layer: `bridge_personal_kb`; never default personal memory.
- evidence bridge: selected transcript spans may support world evidence only via
  explicit extraction/promotion.

Markdown/PKM/bookmark import:

- input: local Markdown tree, exported bookmark file or PKM note directory.
- preserve frontmatter/tags/backlinks/source path.
- store one `kb_document` per note/bookmark target and stable chunk ids based on
  path + heading/span.
- conflicting duplicates stay as separate sources until user merges.

Annotations/highlights/labels/pins:

- `kb_annotation`: `document_id`, optional `chunk_id`, `span_start`,
  `span_end`, `highlight_text`, `note`, `labels[]`, `pinned`, `created_by`,
  `created_at`, `updated_at`.
- annotations are curation metadata, not memory facts.
- pinned annotations increase retrieval priority but do not bypass provenance
  or world-claim status rules.

## Control Surface Coordination

Feature 010 owns generic shell/tabs/actions. Feature 012 owns domain semantics:

- Inbox: new KB documents and unreviewed transcript/bookmark imports.
- Library: searchable KB documents/chunks with source and status filters.
- Document: source preview, chunks, annotations, extraction state.
- Note: user-authored note or annotation editor.

Control UI may show healthy empty states, but mock KB/world data must be labeled
or removed before live verify.
