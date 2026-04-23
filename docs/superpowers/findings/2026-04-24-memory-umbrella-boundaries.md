# Memory-Umbrella Boundary Review — 4 specs cross-checked

**Date:** 2026-04-24
**Task:** `#55` exec-world-model + exec-personal-kb + exec-context umbrella
**Scope:** Verify that the four memory-area execs have clean, non-overlapping ownership boundaries. No impl work — this is a spec-consistency audit.

## The four specs

| Spec | Owner for | NOT owner for |
|---|---|---|
| **`exec-memory.md`** | Personal Raw Evidence (chat turns, tool outputs, scratch notes), Personal Derived Memory (observations, preferences, mental models). Hindsight read/write, MemPalace verbatim archive contract. | Global world model, user-curated KB, compaction/prompt-economics, claim adjudication. |
| **`exec-world-model.md`** | Global World Evidence, Claim Layer, Global World KG, adjudication rules between evidence/claims/compaction. | Session-near Personal Memory, Hindsight/MemPalace read/write, compaction, personal KB. |
| **`exec-personal-kb.md`** | User-curated knowledgebase (saved articles, webclips, private PDFs, YouTube/podcast transcripts). Heavy-ingestion pathway. | Personal memory (raw/derived), global sources, prompt-caching. |
| **`exec-context.md`** | Runtime prompt assembly, compaction orchestration, prompt-economics, token-budget, `pre_compression` event contract. **Operative owner** for things `exec-memory.md` and `exec-world-model.md` consume but don't run. | Memory write/read semantics, KB ingestion, claim adjudication. |

## Cross-reference density

- `exec-memory.md` → 19 cross-refs to the other three
- `exec-world-model.md` → 11 cross-refs
- `exec-personal-kb.md` → 8 cross-refs
- `exec-context.md` → 22 cross-refs (highest — operative owner)

All four specs include an explicit §0 "Warum ein eigenes Exec" plus a "Nicht Owner" list. No cross-ownership conflicts detected.

## Key ownership seams (already documented, verified)

1. **Chat-turn / tool-output** → Personal Raw Evidence (exec-memory), **NOT** Personal KB (exec-personal-kb) despite both dealing with "user content". Rule: interaction-near = memory, curation-near = KB.
2. **Compaction trigger + threshold** → exec-context (operative), **NOT** exec-memory (which defines what's preserved). exec-memory §3h says "Verbatim vor Compaction gesichert; Schwellen modellrelativ — **exec-context**".
3. **`pre_compression` event + MemoryManager hook** → exec-context §11 defines the contract, exec-memory §3h defines the MemPalace/Hindsight consumers.
4. **Global world claim** → exec-world-model (NOT exec-memory even if it travels through a chat turn).
5. **Saved article / webclip** → exec-personal-kb (NOT exec-memory; KB has heavier ingestion, memory has session-near semantics).
6. **Prompt cache + reordering** → exec-context (NOT exec-memory).

## Open follow-ups (not part of this review)

These are known items in the individual specs — listed here for visibility, not resolved by this boundary review:

- **exec-memory §X:648** — `verbatim_store` Postgres schema design (separate ADR candidate).
- **exec-memory §X:668** — Latency-Optimierung (Async Writes, Progressive Retrieval, Dynamic Routing).
- **exec-world-model** — `Global World KG` backend decision (NornicDB vs FalkorDB/Neo4j).
- **exec-personal-kb** — Implementation-Checkliste §6 partial (heavy ingestion pipeline for PDFs/webclips).
- **exec-context §9** — Offene Punkte (TBD per next context-engineering session).

## Conclusion

**No inconsistencies found.** The four specs form a coherent umbrella: each owns a distinct slice (session-memory vs curated-KB vs global-evidence vs runtime-assembly) with explicit hand-off points. Cross-refs are numerous and bidirectional. The Personal-Raw-Evidence + Personal-Derived-Memory + Compaction-Trigger contract (exec-memory §3h × exec-context §11) is a clean example of the operative-owner pattern in action.

Recommendation: treat this umbrella as **stable** and move impl items off to their respective specs. No umbrella-level ADR needed.

---

| Datum | Event |
|---|---|
| 2026-04-13 → 2026-04-16 | exec-memory + exec-world-model + exec-personal-kb + exec-context created with explicit Owner/Not-Owner sections |
| 2026-04-24 | This boundary-review confirms no overlap; follow-ups deferred to individual specs. |
