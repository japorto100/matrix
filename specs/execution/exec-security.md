# exec-security — Umbrella Security-Posture für matrix

**Status:** Draft (exec-hermes Phase-B P2 creation, 2026-04-20)
**Owner:** matrix-core (security posture cross-cuts exec-11/12/17)
**Cross-Refs:** `exec-hermes.md` (adoption-index), `exec-12-sandbox-security.md` (sandbox-HITL), `exec-17-observability-harness-traces.md` (span-redaction hook), `exec-scheduler.md §11` (prompt injection defense)

---

## 0. Why an umbrella spec

matrix has security concerns that cross multiple execs — span-redaction (exec-17 owns spans), skills-guard HITL (exec-12 owns sandbox UX), API-key vault (exec-16 has KeyVault but no rotation policy), audit-trail integrity (exec-18 owns audit tables). Each exec holds one piece; none holds the cross-cutting posture.

This spec is the **umbrella** — it owns the decisions that span execs, references the owning-exec for implementation, and collects SOTA-2026 research TODOs for items where heuristic approaches aren't sufficient anymore.

Focus areas:

1. **Redaction** — preventing secret-leak via persisted spans, trajectory-exports, and fine-tuning datasets (§1)
2. **HITL skills_guard** — human-in-loop confirm for dangerous skill-imports (§2, blocked on exec-12)
3. **Audit-trail integrity** — append-only + tamper-detection (§3)
4. **Prompt-injection defense** — scan user prompts before agent-dispatch (§4)

---

## 1. Redaction — secret-scanning on persisted + exported content

**Status:** Planned exec-hermes Phase-B P3.
**Implementation path:** `python-backend/agent/security/redact.py` (new) + hook in `PostgresSpanProcessor.on_end` (exec-17) + hook in `trajectory/exporter.py`.
**Hermes-ref:** `_ref/hermes-agent/agent/redact.py` (~198 LOC, 48+ regex patterns).

### 1.1 Why this is enterprise-critical (not CLI-specific)

Hermes redact targets **stdout** (user sees terminal output). For a CLI-agent that's "nice to have" — the user only sees their own secrets.

matrix is enterprise: agent-output flows into **three persistence surfaces** where unredacted secrets mean **cross-user leak-risk**:

1. `agent.spans.events` JSONB → Control-UI AuditTab → any admin-access user sees → 🔴 cross-user leak
2. `trajectory/exporter.py` → ShareGPT JSONL → fine-tuning datasets → **landed in LLM weights** → permanent leak
3. Matrix-delivery messages → if routed to wrong room → user's creds posted publicly

Redaction is therefore **more** critical for matrix than for hermes, at different layers.

### 1.2 Two-tier architecture (Contrarian BLOCKER-1 fix)

`PostgresSpanProcessor.on_end` (exec-17) is **synchronous** (sync `psycopg.connect()`). Async DB-backed pattern-lookup cannot run there. Solution:

- **Tier 1 — Sync regex-only, in on_end** — 48+ static patterns snapshot-at-import:
  - API-key shapes: `sk-*`, `sk-ant-api*`, `AKIA*`, `ghp_*`, `hf_*`, `xoxb-*`, `xoxp-*`, `sk_live_*`, `sk_test_*`
  - Bearer-auth headers: `(bearer|token)\s+[a-zA-Z0-9._-]+`
  - Matrix-tokens: `syt_*` (matrix server access-tokens)
  - Env `MATRIX_REDACT_SECRETS=true|false` (default true in prod, false in dev w/ warning)
  - API: `redact_span_event(event: dict) -> dict` — pure CPU, 100% sync-safe
  - span-attribute `audit.redaction_count` tracks per-span matches

- **Tier 2 — Async DB-backed custom patterns, separate background-consumer** — for org-specific patterns beyond the static set:
  - Migration 022 (Phase-B P1 DONE as `022_agent_sync_failures`; P3 introduces 023_agent_redaction_patterns)
  - Table shape: `(pattern_regex TEXT, replacement TEXT, severity TEXT CHECK, org_scope TEXT nullable, is_active BOOLEAN, created_at)`
  - INSERT-endpoint validates via `re.compile(pattern)` (syntax check)
  - Async consumer wraps match calls with 100ms timeout (ReDoS defense)
  - `agent/security/redact_consumer.py` (NEW in P3): NATS subscriber or async-task, runs post-insert against `agent.spans`, UPDATEs in-place
  - Default **disabled** (migration creates empty table); activated via `MATRIX_REDACT_CONSUMER_ENABLED=true`

### 1.3 Admin-bypass policy

Raw-span inspection needed for debugging. Endpoint:

`GET /api/v1/audit/spans/{id}?raw=true&reason=<string>`

- Requires admin role + non-empty `reason` query-param
- Audit-logged in `agent.audit_events` as `action=AUDIT_RAW_ACCESS` with admin-user-id + reason
- Rate-limited per admin-user to prevent abuse

### 1.4 Per-user opt-out

`agent.user_llm_settings.redaction_enabled` (default true). Admin override per user if user's workflow requires raw output (edge case, documented consent required).

### 1.5 SOTA-2026 research TODOs

Heuristic (regex) alone isn't sufficient by 2026 — LLMs generate novel secret-shapes, and prompt-injection-leaks produce content like "my API key is sk-ant-xyz" where the regex needs context-awareness.

**Research items to evaluate before implementing Tier-3 ML-based detection:**

- [ ] **Cloudflare Secret-Detection 2025 paper** — ML-based secret-scanning architecture. Compare FP-rate vs regex on real matrix span-samples.
- [ ] **GitHub Secret-Scanning** — their ML approach (2024-2025). API integration possible?
- [ ] **Trufflehog v4** (2026) — embedding-based secret detection. Library-usable or service-only?
- [ ] **GitGuardian API** — commercial API for secret-detection. Cost model + latency?
- [ ] **OWASP 2026 LLM-leak-taxonomy** — which leak-types are regex-tractable vs need ML?
- [ ] **Benchmark**: regex vs ML FP-rate on matrix span-samples (1000 curated examples). If regex FP < 1% ML isn't worth the complexity; if > 5% investigate further.

### 1.6 Verify gates

- [ ] redact_string matches all 48 patterns against test-corpus, all replaced
- [ ] Non-secret text passes through unchanged (zero false-positive on 100-sample corpus)
- [ ] Snapshot-at-import: env-mutation after import has no effect
- [ ] Span-attribute `audit.redaction_count` reflects actual match count
- [ ] Admin-bypass endpoint requires reason + logs to audit_events
- [ ] Per-user opt-out respected
- [ ] ReDoS: 100ms-timeout catches pathological custom patterns in Tier-2 consumer

---

## 2. HITL skills_guard — blocked on exec-12

**Status:** BLOCKED on exec-12 sandbox-decision + frontend HITL-dialog pattern.
**Hermes-ref:** `_ref/hermes-agent/tools/skills_guard.py` (code ported as `agent/security/skills_guard.py` commit `8ff8a6a`).

Skills-guard today returns `dangerous|suspicious|clean` verdicts — but there's no user-facing dialog when `dangerous` fires. Import is blocked (HTTP 422), but the user sees a raw API error rather than a structured "this skill tried to invoke subprocess-spawn — allow anyway?" prompt.

Blocked on:
- exec-12 decision: sandbox-layer vs surface-dialog layer for HITL-confirm
- Frontend HITL-dialog pattern (needs approval-drawer in Control-UI or agent-chat)

When unblocked: small PR wires skills_guard verdict → HITL drawer → on-approval, re-imports with `trust_source=human_approved`.

---

## 3. Audit-trail integrity — append-only + tamper-detection

**Status:** Partial — `agent.audit_events` is append-only by schema-convention, but no HMAC-chain for tamper-detection.

**Current:** `agent/audit/logger.py` writes rows with `id` PK + `timestamp`. DB-level INSERT-only (no UPDATE/DELETE policies — trusted by convention).

**Gap:** a compromised admin + DB-write-access could modify rows.

**Optional future enhancement (Phase-C or later):**

- Each row carries `prev_hash` = SHA-256 of (prev_row.id, prev_row.timestamp, prev_row.prev_hash). Forms append-only hash-chain.
- Chain-validation scheduled job detects tampering (split-chain = modified row).
- Documented as "append-only by convention → HMAC-chain by implementation" upgrade path.

Not yet planned — cost/value unclear without a concrete regulatory requirement. Listed here as umbrella-security concern rather than Phase-B scope.

---

## 4. Prompt-injection defense — scan before dispatch

**Status:** Planned exec-hermes Phase-B P3.
**Implementation:** `python-backend/agent/security/prompt_scanner.py` (new).
**Hermes-ref:** `_ref/hermes-agent/tools/cronjob_tools.py::scan_cron_prompt` + related heuristics.

User-supplied prompts that feed into scheduled tasks (exec-scheduler `scheduled_tasks.prompt` column) can inject shell-escapes, destructive filesystem commands, credential-extraction-phrases ("what's your API key"). Scanner runs before INSERT.

Scope:
- `scan_scheduled_task_prompt(prompt: str) -> PromptScanResult` with `risk ∈ {low, medium, high}`
- Heuristics: shell-escape patterns, credential-phrases, subprocess-spawn keywords, base64-encoded-payloads
- Wired in `agent/tools/scheduler_tools.py::ScheduleTaskTool.execute` — at `risk=high` → refuse + log + audit-log entry
- Extensions for agent-chat freeform prompts (Phase-C): scan every user-turn input with a lightweight regex pass, flag suspicious content for agent-loop's attention-prompt-protection

---

## 5. Cross-refs

- `exec-hermes.md §0` — Gems Coverage Matrix (redact.py row refs here)
- `exec-17-observability-harness-traces.md §2.5` — span-redaction hook in PostgresSpanProcessor (implementation-owner)
- `exec-12-sandbox-security.md` — sandbox-HITL dialog pattern (blocks §2)
- `exec-scheduler.md §11.1` — prompt-injection defense refs §4 here
- `exec-16-llm-provider-gateway.md` — KeyVault + credential rotation
- `exec-18-unified-agent-schema.md` — audit_events schema

---

## 6. Changelog

| Date | Change |
|---|---|
| 2026-04-20 | Erstversion. Umbrella-security spec created during exec-hermes Phase-B P2 (doc-restructure). Covers redaction (§1, Phase-B P3 target), HITL skills_guard (§2, blocked on exec-12), audit-integrity (§3, Phase-C+), prompt-injection (§4, Phase-B P3 target). §1.5 collects SOTA-2026 research TODOs for ML-based redaction beyond regex. |
