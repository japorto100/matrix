# ADR-004 — Sandbox-HITL Layer Decision

**Date:** 2026-04-23
**Status:** Decided — surface-dialog layer (via existing consent_system), not sandbox-layer
**Related tasks:** `#63` Cluster G exec-12 sandbox-HITL decision, unblocks `#64` exec-security skills-guard-drawer
**Owner-specs:** `specs/execution/exec-12-sandbox-security.md`, `specs/execution/exec-security.md §2`
**Blocked on this decision:** `agent/security/skills_guard.py` verdicts currently return HTTP 422 "dangerous" without UI feedback path

---

## Context

matrix has a skills-guard layer (`agent/security/skills_guard.py`, hermes-port commit `8ff8a6a`) that inspects skill-imports for dangerous patterns (subprocess-spawn, socket-open, raw-eval, etc.) and returns verdicts `clean | suspicious | dangerous`. On `dangerous` the import is blocked at the API layer with HTTP 422 — the user sees a raw API error, not a structured dialog.

The question: **where does the HITL (Human-In-The-Loop) "approve anyway?" dialog live?**

Two layers have been considered:

**Option A — Sandbox-layer HITL:**
- The sandbox container itself pauses on import of a flagged skill, reaches back to the frontend via an IPC channel, waits for user approval, then resumes or aborts.
- Pattern: similar to interactive debuggers pausing on breakpoints and asking the IDE for input.

**Option B — Surface-dialog layer HITL (via consent_system):**
- skills-guard runs **before** sandbox invocation at the API surface. On `dangerous` it returns a structured result that the existing `consent_system` (confirm-level) renders as an approval-dialog in the UI. User clicks approve → API retries with `trust_source=human_approved` header → skills-guard passes verdict as "override" → import proceeds.
- Pattern: consistent with how consent_policy.yaml already handles `sandbox_execute` + other confirm-level tools.

## Decision

**Surface-dialog layer (Option B).**

## Rationale

1. **matrix already has the infrastructure.** `consent/rate_limiter.py` + `consent_policy.yaml` + `approval_node.py` + `interrupt_before: ["approval_gate"]` in the LangGraph builder + audit-events `CONSENT_REQUEST`/`CONSENT_DECISION` across all paths (auto_allow, hard_deny, inform_allow, confirm) — this is the validated pattern that has been live since 2026-03-31 (`exec-12 §2.2`). Adding sandbox-layer HITL would be a parallel second consent mechanism with different semantics, different audit-event shape, different error-recovery path.

2. **Sandbox-layer HITL needs IPC that we don't have.** The OpenSandbox container doesn't expose a "pause-and-query-host" capability in the current profile (`docker-compose --profile sandbox`). Adding one would need a new NATS subject or HTTP callback from sandbox → host → UI → host → sandbox. Each hop multiplies failure modes (timeouts, partial-pause-loss-of-state, sandbox-restart races).

3. **Timing boundary:** skills-guard runs at **import time** (from Control-UI or API), not at **execution time** (inside the sandbox during a tool-call). The flagged code has not yet entered the sandbox when the verdict fires — the sandbox isn't involved in the HITL loop at all. Pushing HITL into the sandbox layer would require moving the skills-guard check later (post-import, pre-execute), which weakens the defense (dangerous code lives in the user's skill-store before the confirm).

4. **Consent-system maps cleanly:** `dangerous` verdict → `level: confirm` + `rules: [skill_import_dangerous]`. Frontend HITL-drawer (exec-security §2) renders the approval UI. User-decision (`allow_once`, `allow_session`, `deny`) fits exactly into the existing `SessionConsentCache` + audit-event structure.

5. **Observability/compliance match:** audit-events `CONSENT_REQUEST` + `CONSENT_DECISION` already capture the path for auditing. Sandbox-layer would need its own event types (`SANDBOX_PAUSED_FOR_CONFIRM`, `SANDBOX_RESUMED_APPROVED`, etc.) + own dashboard path in Control-UI AuditTab.

6. **Hermes precedent:** The original `_ref/hermes-agent/tools/skills_guard.py` is surface-level (returns verdict; caller decides). Matrix's port (`agent/security/skills_guard.py` commit `8ff8a6a`) preserved that surface-level API. Sandbox-layer HITL would mean diverging from hermes; surface-dialog stays in-pattern.

## Consequences

**Positive:**
- Unblocks `#64` exec-security skills-guard-drawer — straight-forward frontend work: new approval-drawer panel that receives the skills-guard verdict (fields: verdict, matched_patterns, suggested_trust_source) and calls the existing `approveToolCall`/`denyToolCall` hooks with a new "skill_import" kind.
- No new audit-event types; existing `CONSENT_REQUEST`/`CONSENT_DECISION` with `metadata.skill_import_verdict = dangerous` carries the semantic.
- No new IPC/NATS surface; skills-guard HTTP 422 response body carries `{verdict, matched_patterns, require_confirm}`; frontend BFF parses and routes to the drawer.
- `consent_policy.yaml` gains one new rule: `skill_import_dangerous: { level: confirm, reason: "Skills guard flagged dangerous patterns" }`.

**Negative:**
- Skills-guard verdict is visible on the API surface (status code 422 + JSON body). A naive caller sees the error raw; only the Control-UI BFF knows to unwrap it into a dialog. Mitigation: frontend BFF documents that `422 + {verdict: "dangerous"}` = show HITL drawer, anything else = generic error.
- If we ever add in-sandbox dangerous-pattern detection (at runtime, not import-time), we'll still need a second mechanism. That's out of scope today and would get its own decision.

**Neutral:**
- Existing `agent/security/skills_guard.py` code is unchanged by this decision; what changes is only how the caller reacts to its verdict (API response shape + frontend drawer + consent_policy.yaml rule).

## Implementation plan

Order (each small, bounded):

1. **Backend shape response** (~30 LOC): skills-guard HTTP handler wraps the verdict into a structured 422 body: `{verdict, matched_patterns, suggested_action: "hitl_confirm"}`. Non-breaking for existing callers that only check status code.
2. **consent_policy.yaml rule** (~5 lines): add `skill_import_dangerous` rule at `level: confirm`. Route name in policy must match the verdict emitter.
3. **Frontend BFF error-parser**: on 422 from skills-import endpoint, detect the `suggested_action: "hitl_confirm"` field and dispatch to the approval-drawer instead of generic toast.
4. **Frontend skills-guard-drawer (`#64`)**: Control-UI panel or modal that shows verdict, matched-patterns, and three buttons: `Allow Once`, `Allow Session`, `Deny`. Calls the existing approval endpoint with a new `kind: "skill_import"` to disambiguate from tool-call consent.
5. **Audit-event wiring**: when the user decides, the existing CONSENT_DECISION audit-event fires with `metadata.skill_import_verdict = dangerous` + `metadata.matched_patterns = [...]`.

Step 1-3 is ~1-2h backend work. Step 4 is ~4-6h frontend work (`#64` scope). Step 5 is a no-op if we reuse the existing approval path — audit-event auto-fires from `approval_node.py`.

## Alternatives not chosen

- **Hard-deny-always (no HITL):** drop the "allow anyway" path entirely. Rejected because matrix's power-user persona (trading devs + researchers) does import legitimately-dangerous skills (e.g. custom backtesting engines that spawn subprocesses). Hard-deny blocks legitimate use.
- **Control-UI-only HITL (no agent-chat path):** skills imports only happen from Control-UI today, so in-chat HITL seems unnecessary. Rejected because future MCP-tool-driven skill installs (`exec-20 MCP Manager`) could trigger verdicts from the chat, and we want one dialog path, not two.

## Cross-refs

- `exec-12-sandbox-security.md §2.2` — existing consent-system infrastructure
- `exec-security.md §2` — HITL skills_guard umbrella (this ADR unblocks)
- `agent/security/skills_guard.py` — hermes-port, surface-level API
- `agent/consent/` package — existing consent mechanism reused here
- `consent_policy.yaml` — policy file that gets the new rule
- `agent/audit/logger.py` — CONSENT_REQUEST/CONSENT_DECISION events already defined

## Changelog

| Datum | Event |
|---|---|
| 2026-04-20 | `exec-security.md §2` created, flagged BLOCKED on exec-12 sandbox-decision |
| 2026-04-23 | This ADR decides surface-dialog layer; unblocks `#63` + `#64`. Next: 3-step backend wiring + skills-guard-drawer frontend. |
