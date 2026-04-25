---
title: Observability Harness Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 014
migrated_from:
  - specs/execution/exec-17-observability-harness-traces.md
  - specs/execution/exec-harness.md
  - docs/superpowers/findings/2026-04-24-observability-tier-strategy.md
---

# Sources

## Normative Local Sources

- `specs/execution/exec-17-observability-harness-traces.md` — OTel, span
  taxonomy, OpenObserve, Langfuse/MCP trace plan.
- `specs/execution/exec-harness.md` — AutoResearch vs Meta-Harness,
  evaluator gaps, Pareto/candidate model.
- `specs/execution/exec-eval.md` — infra/runtime-gated verify workpacks.
- `docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md`
  — decision that tracing and audit stay parallel.
- `docs/superpowers/findings/2026-04-24-observability-tier-strategy.md` —
  OTel/OpenObserve role split and 3-tier frontend observability model.
- `docs/superpowers/findings/2026-04-23-harness-mode-analysis.md` and `.csv`
  — evidence artifact for harness/routing mode analysis.
- `main_docs/root/AGENT_HARNESS.md` — harness principles, complete mediation,
  sandboxing, observability and regression gates.

## Papers / Research

- Meta-Harness, arXiv `2603.28052` — full execution traces are high-value
  inputs for harness optimization; trace access outperforms score-only inputs.
- Meta-Harness artifact — Stanford IRIS lab benchmark implementation patterns.
- EvoSkill, arXiv `2603.02766` — 5-stage loop; useful mainly for Evaluator
  Stage-4 pattern.
- Feedback Descent, arXiv `2511.07919` — optional pairwise scoring mode for
  low-noise evaluator comparisons.
- AutoResearch / AutoRAG optimizer examples — lightweight component tuning
  pattern without full Meta-Harness loop.

## Product / Protocol Docs

- OpenTelemetry Python and Go docs — SDK/instrumentation source.
- OpenTelemetry OTLP exporter spec — vendor-neutral exporter/auth-header model.
- OpenObserve docs — current storage/UI backend.
- Langfuse docs — LLM-specific observability candidate.
- Next.js OpenTelemetry guide — `@vercel/otel` Tier-2 BFF pattern.
- OpenTelemetry browser/client-apps docs — Tier-3 RUM context.

## SDD Rule

Do not drop source context when migrating observability work. If a task derives
from a paper, name the paper and the adopted idea. If a task derives from a
product doc, state whether it is a normative implementation target or only a
reference.
