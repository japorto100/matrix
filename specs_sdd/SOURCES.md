---
title: SDD Sources and Provenance Policy
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Sources and Provenance Policy

`specs_sdd/` replaces the old planning landscape only when it preserves the
reasoning chain, not just the task list. Local specs, execution files,
Superpower findings, `main_docs`, papers, reference repos and product docs are
all part of the source material.

## Non-Negotiable Rules

- Every migrated feature must list local legacy sources in frontmatter
  `migrated_from`.
- Normative `main_docs/root/*` sources must be listed explicitly in the owning
  feature, even when an execution file already references them.
- Paper-heavy or external-reference-heavy features must have `sources.md` or a
  clearly named `research.md`.
- A source entry must say what it is used for: normative requirement, reference
  pattern, prior decision, implementation evidence, or open research question.
- Paper ideas must be translated into matrix terms. Do not just name the paper;
  state the adopted concept and the affected subfeature.
- If a source stays unresolved, it becomes a research task or verify gate.

## Source Classes

| Class | Meaning | Required Handling |
|---|---|---|
| Legacy spec | Old `specs/*.md` current/target state | Map to feature/subfeature and keep key decisions |
| Main doc | Root architecture / main project SSOT in `main_docs/` | Explicitly map to owning feature; treat as normative if newer SDD does not supersede it |
| Execution file | Task history, gates, implementation notes | Carry built/open/superseded status into tasks/gates |
| Superpower finding | ADR, review, research synthesis | Preserve rationale and cross-feature ownership |
| Paper | Research result or algorithmic pattern | Name paper, adopted idea, and validation need |
| Reference repo | Existing implementation pattern | State whether used as inspiration, port, or rejected |
| Product/protocol doc | Operational requirement or API behavior | Distinguish normative config from optional reference |

## Feature-Level Source Files

Feature directories should prefer this split:

- `sources.md`: provenance ledger and external/local references.
- `research.md`: synthesis, alternatives, paper implications, open questions.
- `decisions.md`: accepted architectural decisions when no full ADR exists.
- `gates.md`: verify/live-verify checklist derived from old execution files.

## Current High-Source Features

| Feature | Required source depth |
|---|---|
| 005 Matrix Chat | exec2 gates, Cinny lineage, Matrix/E2EE behavior, live manual gates |
| 008 A2UI/MCP/Artifacts | A2UI papers, MCP docs, Superpower mapping plans |
| 011 LLM Gateway | provider docs, key vault, BYOK, routing policy |
| 012 Memory/Context/World/KB | Supermemory, MemGPT/Mem0/Zep/Letta/Graphrag/Hindsight lineage |
| 013 Sandbox/Security/HITL | OpenSandbox, pentagi/deer-flow/Hermes, OWASP, redaction research |
| 014 Observability/Harness/Evals | OTel/OpenObserve/Langfuse, Meta-Harness, EvoSkill, AutoResearch |
| 015 Scheduler/Skills/Planning | Hermes scheduler/skills, PDDL/DSPy, planning research |

## Archival Threshold

`specs/` can be treated as obsolete only when:

1. `MIGRATION_MAP.md` assigns every relevant old source.
2. `LEGACY_COVERAGE.md` has no unassigned semantic source.
3. `SEMANTIC_AUDIT.md` says the new SDD is equal or better for each feature.
4. High-source features carry their papers/context in `sources.md` or
   `research.md`.
5. Live-verify gaps are explicit and not hidden in old execution files.

## Main Docs Rule

`main_docs/` is not automatically obsolete just because execution specs mention
it. Root architecture files such as `MEMORY_ARCHITECTURE.md`,
`CONTEXT_ENGINEERING.md`, `AGENT_RUNTIME_ARCHITECTURE.md`,
`AGENT_SECURITY.md`, `AGENT_HARNESS.md` and
`RAG_GRAPHRAG_STRATEGY_2026.md` must be carried into the relevant SDD feature
as normative or reference sources.
