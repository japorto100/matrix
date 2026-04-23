# ADR-003 — exec-14 DSPy-track gating + decision reframings

**Date:** 2026-04-23
**Status:** Decided — proceed with changes, Phase-(-1) PoC gate + D-7-first dependency
**Owner-spec:** `specs/execution/exec-14-DSPy.md`
**Contrarian review:** `sota-contrarian stakes=high` (2026-04-23)

---

## Context

exec-14-DSPy is in research/commitment-pre phase: no code yet, ~14 papers staged in `docs/papers/`, 7 open decisions (D-1..D-7) meant to be resolved via `sota-contrarian stakes=high` + empirical Phase-1 benchmark on matrix data. The spec's core sequence is sound (empirical winner decides framework, not paper-hype) but several decisions are mis-framed, ordered incorrectly, or premature relative to evidence.

Contrarian found **2 critical + 4 major + 2 minor issues**. This ADR records the verdict per decision and the gating changes before any implementation.

## Verdict per decision

| ID | Question | Verdict | Rationale |
|---|---|---|---|
| **D-1** | Replace matrix skill-optimization with DSPy? | **REVISIT — reframe as "add, not replace"** | pareto.py / trigger_quality.py / rl_trainer.py operate on **skill lifecycle** (promotion, eviction, retrieval quality, LoRA weight training). DSPy+GEPA operates on **prompt content optimization**. Different layers; no conflict. "Replace" is a false dilemma. |
| **D-2** | dspy.Module as standard interface? | **DEFER until D-7 resolved** | Interface standardization only meaningful if DSPy-based optimizer wins Phase-1. If LLMSelector or another model-selection approach wins, dspy.Module is the wrong primitive. |
| **D-3** | Compile-output versioning schema? | **DEFER — file-based for Phase-1** | DB schema migration before winner-selection is sunk cost. Start with `agent/skills/compiled/` files; design DB schema only after D-7 commits. |
| **D-4** | DSPy as Phase-C A/B 3rd variant? | **REVISIT — blocked on dispatcher refactor + artifact versioning** | Current dispatcher is 2-way (`hash%100` vs single threshold). A third variant needs: (a) N-way bucketing refactor, (b) compiled-artifact-version hash pinned to each `ab_experiments` row so recompile mid-experiment doesn't invalidate results. Without both, Phase-3 data is uninterpretable. |
| **D-5** | Cost-model for compile-runs | **INVESTIGATE FIRST (Phase-(-1) PoC)** | Total compile cost on matrix's historical data volumes is unmodeled. Running MIPROv2 once on smart-routing (4-8h PoC) gives a real data point and answers D-5 more accurately than any estimate. |
| **D-6** | Framework: DSPy vs TextGrad vs own-OPRO | **PROCEED with reasoning-fix** | Spec's "own-OPRO as fallback-only because we miss 2026+ research" is wrong reasoning — own-OPRO loses because it loses the Phase-1 benchmark, not because of meta-reasons. Keep the ordering but correct the rationale. |
| **D-7** | GEPA vs LLMSelector vs p1 primary algorithm | **INVESTIGATE FIRST — architectural match** | LLMSelector's +5-70% claim is on **compound-AI-systems with heterogeneous cooperative agents**. Matrix is **single-agent-with-tools** (one `llm_node.py` per turn). Architectural-match verification (2h reading LLMSelector §2 + 1h inspecting matrix's pipeline topology) must precede Phase-1. If match fails, LLMSelector is out of scope and Phase-1 candidates are GEPA + p1 + pareto.py baseline. |

## Additional critical findings (outside the original 7)

- **[Critical] D-1 misframing.** "Replace matrix skill-optimization" treats `rl_trainer.py`/`trigger_quality.py`/`pareto.py` as architecturally equivalent to DSPy+GEPA. They are not: those files govern **which skills to promote/evict** (pareto ranking on Postgres counters, LoRA weight training stubs, retrieval-quality scoring). DSPy+GEPA optimizes **what prompts the skills use**. Layer mismatch. Real D-1 question: "Should DSPy optimize prompt content inside skills, alongside the existing lifecycle layer?" Answer: almost certainly yes, no replacement needed.

- **[Critical] D-2/D-3 parallel-execution risk.** Spec section 5 lists D-1..D-7 as independent decisions but D-2 (interface) and D-3 (schema) are downstream of D-7 (algorithm). If teams start Phase-2 schema work in parallel with Phase-1 benchmark, they'll design a prompt-artifact schema for a world where the winner is model-selection. 2-3 weeks wasted.

- **[Major] rl_trainer.py is a false substitute.** §4.2 of the spec says "wir haben möglicherweise eine eigene DSPy gebaut". Reading the file: `AGENT_RL_ENABLED=false` and LoRA paths explicitly marked `not_implemented`. The existing stack is NOT a DSPy clone — it's a complementary skill-lifecycle layer.

- **[Major] Phase-0 reading cost front-loaded without exit gate.** 1-1.5 days of team time to read 8 P1+P2 papers before any data exists. Inversion: a 4-8h PoC (MIPROv2 on smart-routing flow, ~200 LOC, one historical data slice) gives the first real signal. If delta < 2% on matrix data, the entire DSPy track can be deferred. Read-then-benchmark reverses the right information order; benchmark-then-read gates the reading investment.

- **[Major] D-4 3-way dispatcher confounding.** Adding a third variant (`variant="dspy_compiled"`) multiplies the confounding risk already seen in ADR-001 G4 (routing dimension). Additional failure mode: GEPA recompile mid-experiment changes the compiled artifact — "dspy_compiled" is no longer a stable variant unless the `ab_experiments` row captures the compiled artifact hash.

- **[Minor] Compile-vs-streaming model mismatch.** DSPy's offline-compile model (train once, infer many) conflicts with matrix's per-user, streaming feedback loop. Recompile trigger criterion (time-based / data-volume / fitness-drift) is undefined; without it, compiled artifacts either decay silently (no trigger) or cost-explode (too-frequent trigger).

- **[Minor] Opportunity cost.** 3-4 weeks of engineering on DSPy track competes directly with smart-routing G5/G6 (GDPR rollout blockers), exec-17 Langfuse setup, exec2-04 E2EE A1 Tuwunel smoke, and other queued Welle 3 items. Should be priced explicitly against those items.

## Decision — gated proceed

**Before Phase-0 reading week starts:**

### G(−1).1 — Architectural match verification for LLMSelector (2h)

Read LLMSelector (2502.14815) §2 "Architecture Requirements". Answer in one paragraph: does matrix have ≥2 distinct pipeline stages that could profitably run different models *per query*? Inspect `agent/graph/nodes/llm_node.py` — if that's the only LLM call per turn, LLMSelector doesn't apply. Document the answer in `exec-14-DSPy.md §5 D-7`.

**If architectural match fails:** replace LLMSelector in Phase-1 with TextGrad as second comparison baseline. Downgrade LLMSelector paper from P1 to P2 in reading-priority table.

### G(−1).2 — PoC benchmark gate (4-8h)

Run MIPROv2 (via DSPy, the documented/stable optimizer) against **one** matrix flow — candidate: `agent/llm/smart_routing.py` keyword heuristic (pure Python, bounded, testable). Use one historical data slice (session_id range from `agent.sessions`). Measure: fitness delta vs current heuristic, LLM call count, token cost per compile run.

**Exit criteria:**
- Fitness delta **≥ 5%**: green-light Phase-0 reading week, proceed with updated D-7 architectural-match result.
- Fitness delta **2-5%**: amber — proceed to Phase-0 but set a harder Phase-1 significance gate (N ≥ 200 instead of 100).
- Fitness delta **< 2%**: red — defer entire DSPy track to Welle 4 or later. Document the null result in the spec changelog and re-prioritize the queued Welle 3 items that were blocked by this.

### Phase-1 benchmark — changes from spec

1. **Candidate list update:** GEPA (DSPy-based), own-OPRO-style (pareto.py extended) baseline, and **one of** LLMSelector (if G(−1).1 passes) OR TextGrad (if G(−1).1 fails). p1 (2604.08801) only if its code is public; spec's current "falls open-source ist — check repo first" stays correct.
2. **D-2 and D-3 blocked** until Phase-1 concludes. No interface standardization, no DB schema work in parallel.
3. **Recompile-trigger criterion required** as Phase-1 deliverable (not Phase-2): pick one of {weekly, data-volume N sessions, fitness-drift threshold} and justify.

### Phase-3 (A/B integration) — changes from spec

1. **Dispatcher bucketing refactored for N-way splits** before adding third variant. Current 2-way `hash%100` is not extensible.
2. **`ab_experiments` row captures compiled artifact version hash** — add column via migration. Without it, Welch t-test on fitness is measurement-invalid if GEPA recompiles mid-experiment.
3. **D-1 reframed** in the spec: not "replace" but "add prompt-optimization at skill internal layer while pareto.py/trigger_quality.py continue governing skill lifecycle".

## Opportunity-cost pricing

Before committing to Phase-0, the team must list the top 3 Welle-3 items that DSPy track displaces and pre-commit to:

- **If Phase-(-1) green/amber:** proceed with DSPy track; ship the top-3-displaced items deferred to Welle 4.
- **If Phase-(-1) red:** DSPy track → Welle 4+; ship the top-3-displaced items now.

Candidates for top-3 displaced (subject to review):
1. Smart-routing G5 frontend indicator (ADR-001 G5, GDPR-rollout blocker)
2. Smart-routing G6 Control-UI panel (ADR-001 G6, GDPR-rollout blocker)
3. exec-17 Langfuse account + OTel collector fan-out (existing Stufe-3 TODO)

## Consequences

**Positive:**
- No Phase-2 schema work happens before a winner is empirically confirmed — prevents the "we migrated the DB for the wrong framework" failure mode.
- Phase-(-1) PoC gate (4-8h) is the cheapest way to answer "does DSPy move the needle on matrix data?". Real data before expensive reading investment.
- D-1 reframing (add, not replace) removes a false architectural conflict that was sending the review cycles through a dead end.
- A/B integration (D-4) has concrete pre-conditions (N-way bucketing + artifact versioning) instead of unspecified risk.

**Negative:**
- Adds a Phase-(-1) gate that wasn't in the original spec — 4-8h effort before Phase-0 "officially" starts.
- Architectural-match check for LLMSelector is a judgment call; if misread, we exclude a potentially valid candidate. Mitigation: document the reasoning in the spec so it can be re-reviewed.

**Neutral:**
- Reading plan preserved (papers stay where they are in `docs/papers/`), only prioritization shifts.
- Phase-1 framework-choice empirical-benchmark core intent preserved.

## Implementation

- `specs/execution/exec-14-DSPy.md`: add this ADR as reference, reframe D-1, mark D-2/D-3 blocked on D-7, add G(−1).1 + G(−1).2 gates, update candidate list (LLMSelector conditional on architectural match).
- This ADR recorded in `docs/superpowers/findings/` alongside ADR-001 + ADR-002.
- No code changes in this ADR — all gating is spec-level + process-level.

## Changelog

| Datum | Event |
|---|---|
| 2026-04-20 | exec-14-DSPy spec created with 14 papers + 6 open decisions |
| 2026-04-20 | D-7 added (GEPA vs LLMSelector vs p1) when 5 additional 2026-ecosystem papers were surfaced |
| 2026-04-23 | sota-contrarian stakes=high review — this ADR records the gated-proceed with D-1 reframing + G(−1) gates + D-2/D-3 deferral. Next: team runs G(−1).1 + G(−1).2 before Phase-0. |
