# exec-scheduler2 — Matrix Scheduler Phase-2 (Routines, Delivery, Conditions)

**Status:** Draft — created 2026-04-19 after Phase-1 DONE
**Owner:** matrix-core (same as Phase-1)
**Cross-Refs:** `exec-scheduler.md` (Phase-1, baseline), `exec-16-llm-provider-gateway.md`, `exec-17-observability-harness-traces.md`, `exec-18-unified-agent-schema.md`

---

## 0. Why this is a separate slice

`exec-scheduler.md` is **Phase-1 DONE** — chat-first user-scheduled agent-
tasks firing via River + NATS + Matrix-bridge are production-ready (12
commits, sota-verify PASS, 5 live-gate E2E tests, 212 unit-tests green).

Phase-2 extends the scheduler to **3 consumer classes that weren't in
the Phase-1 scope**:

1. **Dev / admin routines** — API- and GitHub-webhook-triggered tasks
   (analog to Anthropic Claude Code Routines).
2. **Alternative delivery channels** — email + Telegram on top of the
   Matrix-only Phase-1 delivery.
3. **Condition-triggered tasks** — metric-threshold alerts that fire
   an agent only when a rule trips.

Plus the **infra jobs** 7+8+9+12+13+14 that were deferred as not-critical-
for-Phase-1 (dep-updates, tiering, key-rotation, cert-renewal, harness-
eval, user-digest).

Each block has **product-design decisions** that blocked Phase-1 and
need resolving before coding. This spec collects them + the resulting
implementation items.

---

## 1. Open design decisions (to resolve BEFORE implementation)

### D-1 — Dev-routine API shape + auth

Who can register a routine? How do they authenticate? Options:

- **A: BFF-auth** — Control-UI user creates routines via the existing
  `/api/control/*` proxy; `user_id` from session. Limits routines to
  users with Control-UI access.
- **B: Signed webhook-secret** — dev registers routine via REST with a
  per-routine bearer token; GitHub/CI calls `POST /scheduler/trigger/{routine_id}`
  with `Authorization: Bearer <token>`. Token stored in `scheduler.
  scheduled_tasks.metadata->>'webhook_secret'` (encrypted).
- **C: GitHub App** — OAuth-App installation per org; webhook verification
  via GitHub's signed payloads. Heavier but matches Anthropic's
  Claude Code Routines flow.

**Recommendation to unblock:** start with B (signed webhook-secret),
upgrade to C if we need GitHub-App installation analytics. A is a
subset of B (the Control-UI just issues tokens for its users).

### D-2 — Delivery credentials storage

Phase-1 delivery is Matrix-only, uses the existing `@agent:matrix.local`
bridge. Phase-2 adds email + telegram. Where do creds live?

- **SMTP/Email**: server-global in `.env` (single sender address) vs.
  per-user `agent.user_credentials` row. Per-user gives legitimate
  from-address per user but adds friction (user has to configure SMTP).
- **Telegram bot**: single shared bot-token vs. per-user bots. Per-user
  means each user runs their own bot (overkill for delivery only).

**Recommendation:** single server-global SMTP + single Telegram bot
for Phase-2a; per-user upgrade later if legitimate business case.
Store both in `.env` + `docs/env-vars.md`, NOT in DB.

### D-3 — Condition-DSL choice

A condition-task periodically evaluates a rule against metrics and only
spawns the downstream agent-job when the rule trips.

- **A: Hand-rolled `expr(metric, op, threshold)`** — minimal. 3 kwargs,
  one function. Fast to build, easy to validate.
- **B: CEL (Common Expression Language)** — Google's embedded expr
  language. Library-supported (`cel-go`), composable (`metric > 0.05 &&
  time.Hour > 9`), future-proof. ~2MB binary bloat.
- **C: OPA Rego** — overkill for this use-case. Reject.

**Recommendation:** A for Phase-2a (land fast, covers the canonical
"portfolio.var_95 > 0.05" case), upgrade to B (CEL) only when a second
rule demands composition.

### D-4 — Dep-update integration mode

Two modes mentioned in exec-scheduler.md §9.1:

- **A: Renovate-trigger** — scheduler triggers a GitHub Action that runs
  Renovate which opens PRs. Pro: ecosystem standard. Con: requires
  GitHub+Renovate setup.
- **B: Matrix-digest** — scheduler runs `bun outdated` / `uv pip list
  --outdated` / `cargo outdated` / `go list -m -u all` in-process,
  posts the diff to a matrix-room. Pro: no external services. Con: no
  actionable PRs, just info.

**Recommendation:** both, as separate tasks — B for the dev-heartbeat
("here's what's stale this week"), A when we actually want auto-PRs.
B is cheaper and lands first.

### D-5 — Observability metric contract

Phase-1 already fires `MetricRollupWorker` hourly, emitting rows like
`scheduler.task_executions.completed` into `agent.metrics`. Phase-2
extends this to Prometheus-exposable.

Open: which names? which labels? Candidates:

- `scheduler.task_executions.{status}` (counter, per status)
- `scheduler.task_duration_ms` (histogram)
- `scheduler.active_tasks.{user_id}` (gauge — risk of cardinality blow-up)
- `scheduler.queue_depth` (gauge, River's built-in stat)

**Recommendation:** emit counters + histogram per exec-18 span
convention; skip per-user gauges (use the DB view for per-user inspection).
Prom-mount at `/metrics` on go-appservice via the
`prometheus/client_golang` package River already exposes metrics for.

### D-6 — Routine-vs-task table separation

Should dev-routines live in the same `scheduler.scheduled_tasks` table
(with `kind=routine`) or a separate `scheduler.routines`?

**Recommendation:** keep one table (`kind=routine`). Unified listing
wins over clean user-limit scoping. Per-user cap only counts
`kind IN ('recurring','one_shot','reminder')`, not `kind=routine`,
routines go through a different cap if needed.

### D-7 — Skill-binding migration

When `exec-skills §4.2` lands, `skill_ids[]` becomes first-class.
`scheduled_tasks.skill_ids` is already nullable and present — no
schema change needed. Agent-tool `schedule_edit` can already PATCH it.

**Recommendation:** no Phase-2 work needed; naturally resolved when
exec-skills ships.

### D-8 — Session-aware userId (app-wide, not scheduler-scoped)

`useScheduledTasks()` hardcodes `userId="local"` — same as
`useOverview()`, `useContextInspector()` across Control-UI. This is an
**app-wide auth wiring problem**, not scheduler-scoped.

**Recommendation:** fix in a separate `exec-control-auth.md` slice.
Phase-2 scheduler keeps the placeholder + TODO(auth) comment until then.

---

## 2. Implementation items

Listed in suggested landing order; most are independent.

### Phase-2a — Quick wins (~3–5 days)

- [ ] **P2a-1** — Dep-update Mode B (Matrix-digest): new
      `internal/scheduler/handlers/dep_digest.go` River worker; cron
      default Monday 04:00 UTC; runs `bun outdated` + `uv pip list
      --outdated` + `go list -m -u all` + `cargo outdated` via
      `os/exec`; formats result into a Matrix message; delivers via
      existing Matrix-bridge. Env var `DEP_DIGEST_ROOM_ID` names the
      target room.

- [ ] **P2a-2** — EmailDeliverer: new
      `python-backend/agent/scheduler/delivery/email.py` + `go-appservice/
      internal/scheduler/delivery/email.go`. Use single server-global
      SMTP from env (`SCHEDULER_SMTP_HOST`, `_PORT`, `_USER`, `_PASS`,
      `_FROM`). `delivery_target={"kind":"email","to":"..."}`.

- [ ] **P2a-3** — TelegramDeliverer: single-bot via `python-telegram-bot`
      or raw HTTP to `api.telegram.org`. Env `TELEGRAM_BOT_TOKEN`.
      `delivery_target={"kind":"telegram","chat_id":...}`.

- [ ] **P2a-4** — Observability: add `prometheus/client_golang` Mount at
      `GET /metrics` on go-appservice with scheduler counters. River's
      own stats via `riverpromotherq` (community package) or manual
      instrumentation of `MatrixDispatchWorker.Work`.

- [ ] **P2a-5** — Control-UI inline edit: wire up `schedule_edit` tool's
      DB patch path into `TasksTab.tsx` row-actions. Small form popover
      for prompt / cron / delivery_target edits.

### Phase-2b — Dev / admin routines (~3 days)

- [ ] **P2b-1** — Migration 022: add webhook-secret column OR reuse
      `metadata` JSONB for encrypted `webhook_secret`. Pick one in D-1
      resolution.

- [ ] **P2b-2** — Go REST: `POST /api/v1/scheduler/routines` (create
      routine with generated webhook_secret), `GET /api/v1/scheduler/
      routines` (list), `POST /api/v1/scheduler/trigger/{routine_id}`
      with `Authorization: Bearer <token>` for external triggers.

- [ ] **P2b-3** — GitHub webhook endpoint: `POST /api/v1/scheduler/
      webhook/github` with signature verification (X-Hub-Signature-256
      against per-routine secret). Parses PR-open events → fires
      routine's associated agent-prompt.

- [ ] **P2b-4** — Control-UI `/control/routines` — list + manage
      routines. Separate tab from Tasks, but under the same Control
      surface.

### Phase-2c — Condition-triggered + more infra (~2 days)

- [ ] **P2c-1** — Minimal condition-DSL: `internal/scheduler/conditions/
      expr.go` with `Expr{Metric, Op, Threshold}` struct + evaluator
      reading from `agent.metrics` (latest bucket). Stored in
      `scheduled_tasks.metadata->>'condition'`.

- [ ] **P2c-2** — Condition-eval periodic job: runs every N minutes
      (default 5), iterates `scheduled_tasks WHERE kind='condition' AND
      status='active'`, evaluates each expr, fires agent-job if
      triggered.

- [ ] **P2c-3** — Dep-update Mode A (Renovate-trigger): dispatches a
      GitHub-action-run via `POST repos/:owner/:repo/dispatches` with
      PAT auth. Only wire after P2b if we need it.

- [ ] **P2c-4** — Infra jobs 8 (seaweedFS tiering) + 9 (key-rotation
      health-check) + 12 (cert renewal) + 13 (harness-eval weekly) + 14
      (user-digest) — each is a new River worker in `internal/scheduler/
      handlers/`. Land as we need them, not all at once.

---

## 3. Verify gates

Phase-2a:

- [ ] Dep-digest fires Monday 04:00 → matrix-room receives outdated
      packages list
- [ ] Email-delivery: a scheduled task with `delivery_target.kind="email"`
      lands in test inbox
- [ ] Telegram-delivery: same, in chat-id `@test_receiver`
- [ ] Scheduler metrics visible at `GET /metrics` — counters for fired
      jobs per status, histogram for duration
- [ ] Control-UI: edit a task's prompt from the TasksTab row → next
      fire uses the new prompt

Phase-2b:

- [ ] Create routine via REST → receive webhook_secret in response
- [ ] `curl POST /api/v1/scheduler/trigger/<id>` with bearer → agent
      turn fires
- [ ] GitHub PR-open with signed payload → routine fires → PR comment
- [ ] Invalid signature → 403

Phase-2c:

- [ ] Condition-task with `expr("test.metric", ">", 0.5)` — insert
      metric=0.6 → task fires; metric=0.4 → task does NOT fire
- [ ] Condition-eval runs every 5min regardless of triggers
- [ ] Dep-update Mode A: task fires → GitHub-action starts (webhook
      payload confirms)

---

## 4. Non-goals (still)

Same as Phase-1 §2 — this is still **not**:

- A workflow-orchestration engine (no saga / compensation / replay)
- A distributed event bus (NATS keeps that role)
- A sub-minute-precision trigger (scheduler tick is 60s)
- A commercial Renovate replacement

Temporal migration remains the Phase-3 option, not committed (§7).

---

## 4a. Architecture — extracted from `exec-scheduler.md`

The sections below migrated out of the Phase-1 spec when it was slimmed
to Phase-1-only content. They describe Phase-2 features at architectural
level; implementation items are in §2 above.

### 4a.1 Event-based triggers (was `exec-scheduler.md §6.2`)

NATS-subjects the scheduler listens on (and publishes to):

- `matrix.scheduler.job.execute` — outgoing, agent-jobs. **Already in
  Phase-1.**
- `matrix.ingestion.file.arrived` — incoming, triggers condition-eval
  for "when new file arrives, run eval task X". **Phase-2** (needs
  condition-DSL first).
- `matrix.audit.threshold.crossed` — incoming, triggers alert-agents
  when a monitored metric crosses. **Phase-2**.

HTTP triggers:

- `POST /api/v1/scheduler/trigger/{routine_id}` with bearer-token auth
  — Claude-Code-Routines-style external trigger. **Phase-2b** (P2b-2).
- `POST /api/v1/scheduler/webhook/github` — matches Anthropic's
  routines-on-PR pattern. **Phase-2b** (P2b-3).

### 4a.2 Condition-triggered eval loop (was `exec-scheduler.md §6.3`)

A condition-task runs every N minutes, executes a **pure-eval** rule
(no LLM) against `agent.metrics`, and only spawns the downstream
agent-job when the rule trips. Cheaper than running the agent every
cycle.

Phase-2a rule shape (hand-rolled, D-3 resolution): `Expr{Metric, Op,
Threshold}` — one struct, evaluator pulls latest bucket from
`agent.metrics`. Example: `Expr("portfolio.var_95", ">", 0.05)`.

Phase-2b+: CEL upgrade if a composition case arrives
(`metric > 0.05 && time.Hour() > 9`).

### 4a.3 Dev/admin routines (was `exec-scheduler.md §8`)

Same `scheduler.scheduled_tasks` table, `source in ('api',
'github_webhook')`, `kind=routine`. D-6 (shared vs. separate table)
resolved in favour of shared. D-1 (auth-shape) resolution: signed
webhook-secret per routine, stored in `scheduled_tasks.metadata->>
'webhook_secret'` (encrypted).

**API-triggered routine** (Phase-2b item P2b-2):

```
POST /api/v1/scheduler/routines
Authorization: Bearer <admin-token>
Body: {
  "name": "daily-security-scan",
  "cron_expr": "0 3 * * *",
  "prompt": "Scan matrix-core repo for vulnerabilities. Post digest to #security.",
  "skill_ids": ["security-audit"],
  "delivery_target": {"kind":"matrix_room","id":"!security:matrix.local"}
}
→ response: { "task_id": "...", "webhook_secret": "one-time-shown" }
```

**Webhook-triggered routine** (P2b-3): `POST /api/v1/scheduler/
webhook/github` with GitHub-signed `X-Hub-Signature-256`; matches
incoming payload to a routine (by filter, e.g. `event=opened AND
repo=matrix`), injects payload into the routine's prompt before firing.

### 4a.4 Infrastructure Jobs (Category 4) (was `exec-scheduler.md §9`)

All Phase-1 + Phase-2 infra jobs run as River `PeriodicJob`s registered
at go-appservice startup. Each has a dedicated handler; no LLM call.

| Job | Cron | Handler | Phase |
|---|---|---|---|
| Health pings | `* * * * *` | `workers.go HealthPingWorker` | **1 (done)** |
| Memory pruning | `0 3 * * 1` | `workers.go MemoryPruneWorker` | **1 (done)** |
| Metric rollups | `5 * * * *` | `workers.go MetricRollupWorker` | **1 (done via gap-closer 021)** |
| Dependency updates | `0 4 * * 1` (Mon 04:00) | `handlers/dep_digest.go` (Mode B) + optional `handlers/dep_renovate.go` (Mode A) | **2a (P2a-1) + 2c (P2c-3)** |
| SeaweedFS tiering | `0 2 * * *` | `handlers/storage_tier.go` — scans `storage.artifact_metadata` for age > 30d, moves to cold bucket | **2c (P2c-4)** |
| Key rotation health | `0 5 * * 0` (Sun 05:00) | `handlers/key_rotation.go` — tests all user-provider-keys, flags expiring/invalid | **2c (P2c-4)** |
| Cert renewal | `0 6 1 * *` (1st of month) | `handlers/cert_renewal.go` — LetsEncrypt ACME | **2c (P2c-4)** (only if matrix owns certs) |
| Harness eval | `0 2 * * 0` (Sun 02:00) | `handlers/harness_eval.go` — triggers `python-backend/agent/harness/evaluator.py` | **2c (P2c-4)** |
| User digest emails | per-user cron | `handlers/user_digest.go` — activity summary email | **2c (P2c-4)** (depends on P2a-2 EmailDeliverer) |

#### Dep-update — two modes (D-4 resolution: both land)

**Mode A — Renovate trigger** (auto-PR path):

- Run the outdated-scan core (`handlers/dep_scan.go` — `bun outdated` +
  `uv pip list --outdated` + `go list -m -u all` + `cargo outdated`)
- Upload list as artifact
- Dispatch a GitHub-action (`POST repos/{owner}/{repo}/dispatches`)
  that invokes Renovate with the list
- Renovate opens PRs per its config
- User reviews/merges normally
- **Requires:** GitHub-token in go-appservice keyvault + Renovate
  config in `.github/renovate.json`

**Mode B — Digest message** (review-first, Phase-2a P2a-1):

- Same outdated-scan core
- Post summary to Matrix-room (`DEP_DIGEST_ROOM_ID` env): "3 critical
  bun updates, 12 minor uv, 5 major cargo — react with
  `/reviewupdates` to open PRs"
- User reacts → scheduler fires Mode A for the flagged subset
- **Requires:** Matrix-room for `#infra` / `#dev` + reaction-to-trigger
  handler

Both modes share the scan core; mode is configured per-job in
`scheduler.scheduled_tasks.metadata.update_mode`.

### 4a.5 Delivery Channels (was `exec-scheduler.md §10`)

Go side (`delivery.go` in `internal/scheduler/delivery/`) will implement
a `Deliverer` interface with 4 built-in impls. Phase-1 ships only the
first; the rest are Phase-2a.

- **MatrixRoomDeliverer** — uses existing Matrix-bridge client (already
  wired in go-appservice). Posts as `@agent:matrix.local`. **Phase-1
  (done)**.
- **EmailDeliverer** — SMTP. D-2 resolution: single server-global SMTP
  from env (`SCHEDULER_SMTP_HOST`, `_PORT`, `_USER`, `_PASS`, `_FROM`).
  **Phase-2a (P2a-2)**.
- **TelegramDeliverer** — Telegram-bot-API. Single shared bot-token
  (`TELEGRAM_BOT_TOKEN` env). **Phase-2a (P2a-3)**.
- **NoopDeliverer** — for infra jobs where "done" = write to
  `audit_events`, no external surface. **Phase-1 (implicit)**.

Default delivery per surface (user chat-initiated tasks, Phase-1):

- agent-chat surface → matrix-message back to user's personal matrix-user
- matrix DM → matrix-message to the DM room
- matrix group → matrix-message to the group room
- API/webhook routines → delivery-target must be explicit in request body

---

## 5. Phase-3 option — Temporal migration (was `exec-scheduler.md §4.3 + §13`)

**Status:** Speculative. Not committed. Only becomes relevant when a
Phase-2 use-case can't fit River's model — not pre-emptively.

### 5.1 Why not Temporal now (Phase-1 answer, still holds in Phase-2)

Matrix's own `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md:42` says:

> `| Produkt-/Business-Workflows | Temporal spaeter gezielt | langlebige, produktkritische Ablaeufe |`

Temporal is the right tool **when**:

- Multi-step workflows need durable execution (survive worker crashes
  mid-flow)
- Long-running plans (> 10min) need replay semantics
- Saga patterns with compensations
- Human-in-the-loop approval gates

None of that is needed for cron-driven jobs or short LLM turns (< 2min).
Adding Temporal means: Temporal server + its own DB + new SDK + new
mental model. River covers 90% of production-cron value with zero new
infra.

### 5.2 When Temporal becomes necessary

A concrete trigger — **any one** is sufficient:

1. **User-initiated task > 10min runtime** — e.g. a deep-research agent
   that calls many tools, exceeds River's `JobTimeout` and can't be
   checkpointed. Temporal's workflow-replay handles this; River can't.
2. **Multi-step human-approval flow** — "agent drafts 3 PRs, waits for
   human approval on each, proceeds after all approvals". River has
   no native await-external-signal primitive.
3. **Saga with compensation** — "schedule task A + task B; if B fails,
   roll back A's side-effects". River is fire-and-forget, no
   compensation story.

### 5.3 Migration path

- Add Temporal server (new infra — Docker image + own Postgres DB)
- Migrate ONLY the impacted handler from River-worker to Temporal-
  workflow; keep River for fire-and-forget infra jobs
- `scheduler.scheduled_tasks` table **unchanged** — a `metadata->>
  'temporal_workflow_id'` field links the row to the workflow instance
- User-facing agent-tools (`schedule_task`, ...) API unchanged
- Control-UI routing unchanged; runs-drawer gains a "workflow timeline"
  view for Temporal-backed tasks

### 5.4 Non-decision

Temporal evaluation is **demand-driven**. Phase-2 does NOT schedule
Temporal work; it flags the first use-case that needs it and we
re-evaluate at that point.

---

## 6. Cross-refs

- `exec-scheduler.md` — Phase-1 (done, verify-gates only)
- `exec-16-llm-provider-gateway.md` — LLM calls go via LiteLLM; metrics
  feed into Phase-2a observability
- `exec-17-observability-harness-traces.md` — span convention for
  scheduler metric names
- `exec-18-unified-agent-schema.md` — metric-rollup uses
  `agent.task_executions` (exec-18-managed)
- `exec-control-auth.md` (not yet written) — session-aware userId fix
  lives here, blocks P2a-5 polish

---

## 7. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-19 | Erstversion. Phase-2 extrahiert aus exec-scheduler.md §13 nach Phase-1 DONE. 8 Design-Decisions dokumentiert (D-1..D-8), 12 Implementation-Items gruppiert in 2a (quick-wins), 2b (routines), 2c (conditions + more infra). Phase-1 Spec behält nur Verify-Gates, keine offenen Implementierungspunkte mehr. |
| 2026-04-24 | **D-1..D-8 recommendations ratified.** Phase-2a (quick-wins) unblocked for implementation: signed-webhook-secret auth (D-1), server-global SMTP + single telegram bot (D-2), hand-rolled `expr(metric,op,threshold)` condition (D-3), matrix-digest dep-update (D-4), counters+histogram metrics via `prometheus/client_golang` (D-5), single `scheduler.scheduled_tasks` table with `kind=routine` (D-6), no schema change for skills (D-7), `TODO(auth)` placeholder until exec-control-auth.md (D-8). Phase-3 Temporal remains **demand-driven** per §5.4; no pre-emptive work. Next concrete item: §2 Implementation order landing Phase-2a quick-wins first. |
