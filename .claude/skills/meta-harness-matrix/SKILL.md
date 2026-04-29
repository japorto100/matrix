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
fixtures, scoring and trace gates.

Out of scope for this phase:

- productizing autonomous coding agents.
- switching base model as the main improvement.
- using holdout results during search.
- scenario-specific hacks.
- pure parameter sweeps unless the hypothesis says why that parameter is the
  mechanism under test.

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

Use GitNexus impact analysis before editing code symbols.

## Workflow

1. Analyze search-set results, trace-gate failures, candidate decisions and raw
   traces.
2. Identify one to three falsifiable hypotheses. Each candidate should test one
   mechanism.
3. Prefer cheap prototypes or static checks before editing runtime code.
4. Implement only bounded, reviewable changes in the declared write scope.
5. Write or update candidate metadata so the outer loop can evaluate it.
6. Do not run holdout unless the user or command explicitly authorizes it.
7. Record keep/discard/defer rationale after evaluation.

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
