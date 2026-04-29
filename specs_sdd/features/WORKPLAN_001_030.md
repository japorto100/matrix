---
title: Feature Workplan 001-030
status: active
owner: filip
created: 2026-04-29
updated: 2026-04-29
---

# Feature Workplan 001-030

This is the operating queue for implementing Matrix SDD Features 001-030. The
feature directories remain the source of truth for detailed tasks, verify gates
and live-verify probes. This file defines execution order.

## Execution Rules

- Work backend/static/non-browser gates before browser/client live gates.
- Use real configured provider paths for live verification; deterministic fake
  providers are allowed only for unit/contract tests.
- Keep provider-specific SDK examples as references only. Core contracts remain
  provider-agnostic.
- Before dependency-sensitive work, check current releases and changelogs:
  `matrix-js-sdk`, Tuwunel, AI SDK, MCP packages, Element X and widget APIs.
- Use GitNexus before code edits and before commits. Re-run
  `npx gitnexus analyze` after commits/merges or when GitNexus reports stale
  index state.
- Do not promote GraphRAG, browser-RAG, visual memory, widget hosting or
  report publishing without matched verify gates and artifacts.

## Phase Order

| Phase | Features | Goal | First non-browser gates |
|---|---|---|---|
| 1 | 001-030 | Spec/backlog integrity | Feature count, task/gate counts, index/readme consistency |
| 2 | 007, 011, 013, 016, 020 | Agent harness core | provider capability metadata, approval fail-closed, runner parity |
| 3 | 008, 013, 014, 016, 024 | MCP gateway policy | descriptor snapshots, token denial, poisoned descriptor block |
| 4 | 012, 017, 018, 025 | Memory/KG/Semantic layer | semantic lookup, KG provenance, correction proposals |
| 5 | 019, 021, 022, 023, 026, 028 | RAG/Ingestion/Benchmark | source refs, canaries, holdout protection, candidate artifacts |
| 6 | 027, 028, 014, 016 | Reports and visual memory | citation manifest, layout evidence, visual recall/refusal |
| 7 | 010, 014, 024, 025, 027, 029 | Control backend surfaces | read models/endpoints before browser walkthrough |
| 8 | 005, 008, 024, 030 | Matrix widget service semantics | proposal, approval, room-state payload, fallback |
| 9 | 003, 005, 007, 010, 026, 030 | Browser/client live verify | Playwright/DevTools/Element X/FluffyChat compatibility |
| 10 | all | Full-stack promotion | Meta-Harness service mode and closeout artifacts |

## Immediate Queue

1. [x] Commit and push this workplan after static validation.
2. [x] Phase 2: harden provider/live-lane semantics so regular live verify no
   longer depends on `llm-mock`.
   - 2026-04-29: `provider-smoke` blocks deterministic fake lanes unless
     explicit, records provider capability snapshots and ADR-0009 captures the
     boundary.
3. [partial] Phase 2: expand runner parity and approval trace gates for
   `simple`, `langgraph` and `dispatcher`.
   - 2026-04-29: runtime now omits known unsupported `tools` and
     `reasoning_effort` request fields; broader runner-parity scenarios remain.
4. [x] Phase 3: implement MCP descriptor fixture and policy tests before any
   external server is exposed to agents.
   - 2026-04-29: MCP catalog policy primitives cover descriptor snapshots,
     token passthrough denial, poisoning scan, diff escalation and read-only
     Control catalog.
   - 2026-04-29: MCP policy now also blocks high-trust tool lookalikes,
     requires user-visible external-tool provenance, exposes an agent-facing
     visible-only catalog and supports expiry/audit-bound session grants.
   - 2026-04-29: `Z_Additional_For_Tool_Stuff.md` was corrected as broader
     than MCP. Normal builtin ToolRegistry tools now have catalog metadata for
     group, risk, approval, hashes and progressive disclosure through Feature
     016/010, while Feature 024 remains external-MCP-specific.
5. [x] Phase 4: add semantic catalog skeleton only after schema ownership is clear.
   - 2026-04-29: semantic catalog primitives and Control endpoints cover term
     and metric schema, ambiguity, permissions, KG/RAG mappings and correction
     proposal review state.
6. [x] Phase 6: add report publishing contract before renderer/live promotion.
   - 2026-04-29: report manifest, citation validation, safe fallback renderer
     and artifact writer are implemented; Quarkdown remains experimental until
     local CLI builds pass.
7. [partial] Phase 5: strengthen RAG/Ingestion/Benchmark source-ref and holdout
   gates using the semantic/report contracts.
   - 2026-04-29: Feature 022 canaries now cover semantic-term, visual-layout
     and report-grounding metadata/citation contracts. Remaining Phase 5 work:
     real parser/chunker candidates, browser-local retrieval lane, live
     pgvector/NornicDB/provider benchmarks and inner-loop search spaces.
   - 2026-04-29: Feature 023 RAG inner-loop candidates now emit bounded
     semantic, visual, report and tool-policy search spaces, with protected
     gates against tool/security relaxation.
   - 2026-04-29: Feature 021/023 extraction artifacts now expose parser
     profiles and chunker/metadata-enrichment candidate spaces for
     PyMuPDF4LLM, MarkItDown, Docling and MinerU without installing heavy
     optional dependencies.
   - 2026-04-29: `pdf-extraction-sweep` now writes one Meta-Harness candidate
     directory per available/requested parser profile and records skipped
     optional extractors.
   - 2026-04-29: Feature 022 now has
     `holdout-hierarchy-aware-parser-001`, a parser-derived dense baseline
     requiring hierarchy/page/table/citation metadata before graph promotion.
8. [next] Phase 5: connect extraction sweep artifacts to retrieval canary
   generation or move to the next non-browser agent surface if the artifact
   contract is sufficient for now.

## Dependency Watchlist

- `matrix-js-sdk`: repo currently uses `^41.2.0`; latest seen 2026-04-29 was
  `41.4.0`. Check release notes before chat/E2EE/widget work.
- Tuwunel: repo pins `v1.6.0`; GHCR tags currently show no newer stable tag.
  Check upstream issues before Matrix live gates.
- AI SDK: repo uses `ai ^6.0.134`, `@ai-sdk/react ^3.0.136`; latest seen
  2026-04-29 was `ai 6.0.170`, `@ai-sdk/react 3.0.172`.
- Matrix widgets: check Matrix Rust SDK widget driver, `matrix-widget-api`,
  Element X Android/iOS release notes and Element Web behavior before Feature
  030 live work.

## Completion Policy

A feature is not done until:

- tasks are marked with implementation evidence;
- verify gates have command/test evidence;
- live-verify gates are either passed with artifacts or explicitly deferred
  with owner and blocker;
- `closeout.md` summarizes accepted behavior, residual risk and next review.
