# ADR-001 — Smart Cheap-vs-Strong Routing Rollout Gate

**Date:** 2026-04-23
**Status:** Decided — rollout blocked behind 6-item gate
**Owner-spec:** `specs/execution/exec-a2fm-adaptive-routing.md` (to be updated)
**Gateway cross-ref:** `specs/execution/exec-16-llm-provider-gateway.md §2.D`
**Contrarian review:** `sota-contrarian stakes=high` (2026-04-23)
**Impl files:**
- `python-backend/agent/llm/smart_routing.py` (194 LOC heuristic)
- `python-backend/agent/graph/nodes/llm_node.py` (wire-point, iteration==0)
- `python-backend/agent/security/credentials.py::get_user_smart_routing_config`
- `python-backend/alembic/versions/026_smart_routing_config.py`

---

## Context

A conservative keyword-based cheap-vs-strong router landed 2026-04-20 (port of hermes `choose_cheap_model_route`, multi-domain keyword set). Gated off by default (`{}` config = disabled). Owner-spec exec-a2fm targets an A2FM-paper ML-router long-term; the current code is the Stufe-0 heuristic stub. 6 open design questions were flagged; this ADR records the verdict per question + the rollout gate.

## Verdict per flagged question

| # | Question | Verdict | Rationale |
|---|---|---|---|
| Q1 | A/B-dispatcher integration (variant vs always-on) | **REBUILD** | Without making `routing_used` a first-class dimension in the span schema, all fitness data collected during rollout is analytically compromised — confounds runner-variant with routing decision. |
| Q2 | LiteLLM gateway × per-user routing overlap | **SHIP-WITH-GUARDRAILS** | LiteLLM fallback on cheap-model-down is acceptable (exception catch at `llm_node.py:125` falls through to primary). But credential-pool pre-flight needed (see G2). |
| Q3 | Control-UI surface unbuilt | **SHIP-WITH-GUARDRAILS** | SQL-only enablement acceptable for ops-controlled pilot with documented runbook. Block general-user availability until UI ships. |
| Q4 | Cost-attribution undercount in InsightsEngine | **SHIP-WITH-GUARDRAILS** | Non-blocking for pilot; `routing_reason` must be indexed in aggregation before business-level reporting. |
| Q5 | English-only keyword list | **REBUILD** | User base is German-speaking (CLAUDE.md). Complex DE queries ("analysiere mein Portfolio", "berechne das Risiko") route to cheap because keywords don't match — systematic inversion of the stated conservative bias. This is a correctness bug, not a gap. |
| Q6 | Spec (Draft/Research) vs Code alignment | **SHIP-WITH-GUARDRAILS** | Update exec-a2fm.md to describe what shipped (hermes-port heuristic at llm_node.py wire-point as Phase 0.5), not what was planned (`router_node.py` as Phase 1). Code is not wrong; spec is stale. |

## Additional critical findings (not in the original 6)

- **[CRITICAL] Silent vendor substitution without user consent.** User picks `claude-sonnet-4-6` (Anthropic DPA); simple turn silently lands on `gpt-4o-mini` (OpenAI DPA). Span attribute `llm.routing_reason` is ops-only, not user-visible. For GDPR-adjacent enterprise context this is a processor-change without disclosure. **Mitigation:** user-visible indicator on routed turns + Control-UI disclosure text before toggle.
- **[CRITICAL] `get_user_smart_routing_config` opens new DB connection per iteration-0 turn.** No in-process cache, no connection pool; runs on EVERY new chat regardless of `enabled` state. At 50 concurrent new chats → 50 conn open/close/sec. **Mitigation:** wrap with 60s TTL in-process cache OR pre-load alongside `get_user_default_model` in `app.py` pre-graph.
- **[CRITICAL] Keyword list systematically misfires for DE user base.** See Q5; combined with a bias the other direction on trivial English ("review", "plan", "tool" in the keyword set block cheap-route for casual chat).
- **[MAJOR] Credential pool mismatch.** After `state["model"]` mutation to cheap model, credential acquire at `llm_node.py:180-186` uses cheap model's provider. If user has Anthropic credentials only → `acquire()` returns None → falls through to state api_key (Anthropic) sent to OpenAI endpoint → 401. Hard failure on routed turns for single-vendor-credential users.
- **[MAJOR] A/B harness contamination.** Self-selected SQL-enabled cohort confounds `langgraph` vs `simple_loop` fitness comparison; routing effect attributed to runner variant.
- **[MAJOR] Deprecation cliff.** Literal `cheap_model: "gpt-4o-mini"` in JSONB; no validation, no fallback sentinel. OpenAI sunsets model → silent `except Exception` catch hides the failure; ops is blind. Routing_reason span attribute then lies about why routing was not evaluated.
- **[MINOR] iteration==0 semantics unspecified on session resume / fork / crash-replay.** Document the invariant; if history-replay hydrates fresh graph with `iteration=0` but `len(messages) > 2`, skip routing.

## Decision — Rollout Gate

Do **not** flip `enabled: true` on any user's `agent.user_llm_settings.smart_routing` row until all 6 gates pass:

1. **German keyword set + hyphen-tokenizer added** — OR language-detection guard (langdetect ~50KB) + branching. Without this the heuristic is semantically broken for the target user base. **Non-negotiable, correctness bug.**
2. **Credential pre-flight check** — before mutating `state["model"]` in `llm_node.py`, verify the cheap model's provider has credentials; if not, keep primary. Prevents silent 401s. Alternatively: require `cheap_model` be reachable via LiteLLM virtual key (provider-agnostic), document virtual-key-only policy.
3. **Config accessor cached (60s TTL)** — eliminate per-turn Postgres conn on every new chat. Either in-process cache in `credentials.py` or pre-load in `app.py` pre-graph + pass via state.
4. **A/B harness gets routing dimension** — add `routing_used: bool` / `routing_picked: str` to span schema or as composite variant tag (`variant="langgraph_cheap_routed"`). Must be in place **before** data collection starts, not post-hoc fix.
5. **User-visible routing indicator** — conversation-level disclosure that a cheap-model was used on a given turn. OTel span attributes do not count as user disclosure for GDPR processor transparency.
6. **Control-UI panel + disable path** — minimum: self-service toggle in `frontend_merger/src/features/control/`. SQL-only ops flow requires documented runbook for the interim; general-user availability blocked until UI ships.

## Inversion — what a rebuild would look like

Move the routing decision out of `llm_node.py` side-effect and into a proper `router_node.py` as the exec-a2fm Phase-1 spec originally described. Produces a `routing_decision` state key; gets A/B-tested as a first-class variant; naturally fixes Q1 (dispatcher dimension) and iteration==0 ambiguity. Reuses the existing `smart_routing.py` heuristic as-is. **Cost:** one new node file + state schema addition. **Benefit:** clean A/B semantics, explicit wire-point, testable as a standalone unit. Recommend this as the Phase-1 target after Gate 1-3 are shipped (tactical) — the current wire-point is Phase-0.5 and should be treated as provisional.

## Pre-mortem — most likely 6-month failure chain

1. Pilot user (ops-enabled via SQL) asks complex German financial question under the length gate with no English-keyword hit.
2. Routes to `gpt-4o-mini`. Mediocre answer. User notices "something is off", no UI indicator to diagnose.
3. Support ticket: "the assistant got worse." Ops can't quantify distribution (Q4 undercount).
4. Meanwhile A/B harness conflates routing with runner variant (Q1); decision to deprecate `simple_loop` gets made on corrupted fitness data.
5. First user without cross-vendor virtual key hits 401 on a routed turn (credential mismatch); looks like a transient outage in the span logs.
6. OpenAI deprecates `gpt-4o-mini`; silent `except` swallows the 404; routing_reason span lies; ops is blind.

**Probability:** moderate. **Blast radius:** corrupted A/B signal (architectural decisions on bad data) + user-trust erosion + GDPR exposure.

## Implementation priority

| Gate | Size | Urgency | Blocker for |
|---|---|---|---|
| G1 DE keyword set | S (1 day) | HIGH | Any user rollout |
| G2 Credential pre-flight | S (0.5 day) | HIGH | Any non-virtual-key user |
| G3 Config cache | XS (0.25 day) | MEDIUM | Load beyond ops pilot |
| G4 Harness dimension | S (0.5 day) | HIGH | Data-driven decisions |
| G5 User-visible indicator | M (1-2 days, frontend) | HIGH | GDPR / enterprise users |
| G6 Control-UI panel | M (2-3 days, frontend) | MEDIUM | General-user rollout |

**Recommended sequence:** G1 → G3 → G2 → G4 → (G5, G6 parallel, frontend-owner).

**Total effort to gate-clear:** ~5-7 dev-days (backend: 2, frontend: 3-5).

## Changelog append

| Date | Event |
|---|---|
| 2026-04-20 | Code landed, flagged NEEDS HOLISTIC REVIEW |
| 2026-04-23 | `sota-contrarian stakes=high` review complete; this ADR records the rollout gate |
| 2026-04-23 | **G1-G4 + P1 landed** (commits `0a59a76` DE keywords, `5061586` cache, `57400f4` credential preflight, `dc539df` A/B dimension + migration 027, `<P1-commit>` router_node refactor). Remaining: G5 (frontend user-indicator), G6 (frontend Control-UI panel). |
