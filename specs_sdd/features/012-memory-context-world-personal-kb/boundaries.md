---
title: Memory Umbrella Boundaries
status: stable
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
migrated_from:
  - docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md
  - specs/execution/exec-memory.md
  - specs/execution/exec-context.md
  - specs/execution/exec-world-model.md
  - specs/execution/exec-personal-kb.md
---

# Boundaries

## Ownership Table

| Subfeature | Owns | Does Not Own |
|---|---|---|
| Personal Memory | chat turns, tool outputs, scratch notes, personal raw evidence, observations, preferences, mental models, Hindsight/memory_fusion read/write | global evidence, curated KB, prompt economics, world claim adjudication |
| Runtime Context | prompt block order, compaction triggers, provider prompt cache, KV-cache evaluation, context metadata, degradation surfacing | memory write semantics, KB ingestion, world claim promotion |
| Global World Model | global evidence, claim layer, global KG, adjudication, status/freshness/conflict rules | session memory, KB artifacts, compaction |
| Personal KB | saved articles, webclips, PDFs, transcripts, notes, highlights, labels, library/inbox | chat turns, global sources, world truth, prompt caching |

## Default Routing Rules

| Artifact | Default Destination | Rule |
|---|---|---|
| Chat turn | Personal Raw Evidence | interaction-near evidence |
| Tool output | Personal Raw Evidence | primary evidence, later may produce derived memory |
| Session scratch note | Personal Raw Evidence | interaction-near |
| Observation/preference/mental model | Personal Derived Memory | only with source/evidence backlinks |
| Saved article/webclip | Personal KB | curated artifact, not session memory |
| Private PDF | Personal KB | heavy ingestion first |
| YouTube/podcast transcript | Personal KB | KB first, optional bridge later |
| Global news/filing/report | Global World Evidence | not personal memory |
| World/market claim | Global World KG/Claim Layer | claim status required |

## Runtime Merge Rules

- Personal derived memory must carry evidence/source backlinks.
- World KG hits must include status, freshness and provenance.
- Personal KB hits must not be presented as world truth.
- Missing world/KB/memory layers must emit degradation flags instead of silent
  fallback.
- Context owns how these blocks enter the prompt; each storage layer owns what
  the blocks mean.

## Stable Decision

The 2026-04-24 boundary review found no ownership conflicts. Treat the umbrella
boundary as stable; move implementation tasks to the relevant subfeature instead
of reopening the umbrella unless a new artifact type appears.
