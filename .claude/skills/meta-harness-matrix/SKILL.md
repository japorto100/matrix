---
name: meta-harness-matrix
description: Use when acting as the Meta-Harness proposer for Matrix: inspect prior scenario traces, scores, specs and code, propose bounded harness/memory/tool/skill improvements, write candidate artifacts, and leave evaluation to the outer loop.
---

# Meta-Harness Matrix

Act as the proposer for Matrix harness optimization. Do not run a hidden
external proposer LLM by default; this Codex session is the proposer unless the
user explicitly enables another backend.

## Scope

Optimize the harness around the fixed Matrix agent: context assembly, memory
routing, tool policy, consent/recovery behavior, skill selection, scenario
fixtures, scoring and trace gates. In this repository the agent harness is the
agent-adjacent runtime, not the `meta_harness/` package itself: `agent/`,
`memory_fusion/`, RAG/KG, skills, tools/MCP, Matrix transport/session handling
and context construction are candidate surfaces.

Out of scope for this phase:

- productizing autonomous coding agents.
- switching base model as the main improvement.
- using holdout results during search.
- scenario-specific hacks.
- pure parameter sweeps unless the hypothesis says why that parameter is the
  mechanism under test.
- changing holdout fixtures, deterministic evaluators or goldens during an
  active run.
- treating inner-loop metrics as promotion authority.

## Required Inputs

Before proposing a candidate, inspect the relevant subset of:

- `data/meta_harness/domain_spec.md`
- `data/meta_harness/runs/*/candidates/*`
- `data/harness/search_set/`
- `data/harness/holdout_set/` only to verify existence/split, not results
- `specs_sdd/features/016-meta-harness-agent-optimization/`
- `specs_sdd/features/012-memory-context-world-personal-kb/`
- `specs_sdd/features/015-scheduler-skills-planning-automation/`
- `python-backend/meta_harness/`
- `python-backend/agent/runners/`
- `python-backend/memory_fusion/`
- `python-backend/agent/skills/`
- `data/meta_harness/runs/*/experience_packet.json`
- `data/meta_harness/runs/*/candidates/*/candidate_manifest.json`

Use GitNexus impact analysis before editing code symbols.

## Workflow

1. Build or inspect an outer-loop experience packet:
   `uv run python -m meta_harness.meta_cli experience-packet --run-id <id>`.
2. Analyze search-set results, trace-gate failures, candidate decisions, source
   snapshots and raw traces. Do not rely on summaries when raw files exist.
3. Identify one to three falsifiable hypotheses. Each candidate should test one
   mechanism.
4. Prefer cheap prototypes or static checks before editing runtime code.
5. Implement only bounded, reviewable changes in the declared write scope.
6. Write or update candidate metadata so the outer loop can evaluate it.
7. Run only search-set/provider-free or explicitly budgeted live-search gates.
8. Do not run holdout unless the user or command explicitly authorizes it.
9. Record keep/discard/defer rationale after evaluation.

## Role Separation

In a Codex-driven run, Codex may act as both proposer and simulated user, but
the roles stay separate:

- proposer: inspects search artifacts, source, scores and raw traces; proposes
  bounded candidate changes.
- simulated user: drives fixed scenario fixtures to generate controlled traces.
- evaluator: frozen CLI lanes, trace gates and Pareto computation; the proposer
  cannot self-certify promotion.
- promotion: explicit decision plus frontier/holdout gates. Candidate notes are
  never sufficient.

Holdout paths and scores must not be included in proposer packets.

## Paper-Required Candidate Artifacts

Each evaluated candidate should have:

- `candidate_manifest.json`
- `run.json`
- `config.json`
- `source_snapshot.json`
- `scores.json` or `aggregate.json`
- `verdicts.json`
- raw `traces/**/*.json` and `sse/*.jsonl` when it is a scenario run
- benchmark-specific evidence for benchmark/inner-loop candidates
- `decision.json` or candidate-decision ledger entry after evaluation

If any of these are missing, improve artifact capture before trusting the
candidate as Meta-Harness evidence.

## Inner Loop and Autoresearch

Inner loops are candidate generators only. They may sweep RAG, KG, memory,
skill or tool-policy spaces and write typed candidates, but the outer loop must
validate and promote them.

Autoresearch contributes run discipline: fixed evaluator, fixed budget,
keep/discard/crash status, no evaluator mutation during the run, and rollback
on regression. Use that discipline for Matrix candidate decisions.

## Candidate Quality Bar

Good candidates change a mechanism:

- Hindsight vs MemPalace trigger policy.
- context ordering/source/freshness labeling.
- memory evidence selection before compaction.
- failed-tool recovery and retry policy.
- consent behavior for risky tools.
- skill selection/promotion criteria.
- deterministic trace gates or scenario coverage.

Weak candidates only tune numbers:

- top-k changes without retrieval logic change.
- timeout tweaks without failure-mode evidence.
- prompt wording changes without trace-backed hypothesis.

## Output Pattern

When proposing, produce a concise candidate record:

```json
{
  "name": "snake_case",
  "hypothesis": "Falsifiable claim",
  "mechanism": "What changes and why",
  "write_scope": ["paths"],
  "expected_improvement": "Metric/gate expected to improve",
  "expected_risk": "Likely regression risk",
  "evaluation": "Search scenarios/gates to run"
}
```

If implementation is requested, edit the files directly and leave the outer
loop to run search/holdout evaluation.
