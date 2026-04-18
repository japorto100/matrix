# exec-scheduler — Matrix Scheduler (Cron / Events / Conditions)

**Status:** Draft 2026-04-18
**Owner:** matrix-core (Go service in `go-appservice/internal/scheduler/` + Python agent-tool)
**Cross-Refs:** archive/exec-19-devstack-consolidation.md (former §4.1 owner), exec-hermes.md §4.1 (pattern source), exec-16-llm-provider-gateway.md (LLM calls from scheduled jobs), exec-17-observability-harness-traces.md (job-run traces), exec-18-unified-agent-schema.md (schema conventions), exec-memory.md (persisted-task-context), exec-skills.md (skill-binding), exec-6-agent-chat-integration.md (chat-surface as entry point)
**Papers:**
- OpenAI ChatGPT-Tasks launch notes (2025-01, 2026-Q1 expansion)
- Anthropic Claude Code Routines (2026-04 research preview)
- Temporal + AI Agents orchestration (2026 industry pattern)
- `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md §42` (Matrix's own Temporal-later plan)

---

## 0. TL;DR

Matrix needs a scheduler for three distinct consumer classes:

1. **End-users** who say in agent-chat or matrix-DM: *"jeden Montag 9 Uhr gib mir ein Portfolio-Briefing"*, *"morgen 8 Uhr check EUR/USD"*, *"in 6 Monaten erinnere mich an Passport renewal"*.
2. **Developers / admins** who register routines (API + GitHub-webhook triggered) — analog zu Anthropic Claude Code Routines.
3. **System-internal infrastructure** — dependency-updates, SeaweedFS tiering, key-rotation, metric-rollups, memory-pruning, cert-renewal, harness-eval runs, user-digest-emails, health-pings, skill-promotion.

**Tech stack:** **River** (MPL-2.0, Postgres-native job-queue) in Go, hosted in `go-appservice`. Agent-jobs dispatched to Python worker via NATS. Temporal is kept as a deliberate Phase-2 migration target for long-running agentic workflows, matching the plan in `AGENT_RUNTIME_ARCHITECTURE.md §42`.

**UX model:** **chat-first creation** (matching OpenAI ChatGPT-Tasks). User talks to the agent — in agent-chat UI, matrix-DM with agent, or @mention in a group — natural language is parsed to `(cron_expr, prompt, delivery_target)`, agent echoes back for confirmation, task lands. Control-UI shows a list with pause / edit / delete, but does **not** have an "Add Task" form.

---

## 1. Why

### The gap today

Matrix currently has **no scheduler at all**:

- Cron for dependency updates, cleanup jobs, metric aggregation — done by hand or not at all.
- User-scheduled tasks (ChatGPT-Tasks-style) — not possible. Users can't say "jede Woche portfolio-briefing".
- Developer routines (deploy verification, doc-drift) — not possible.
- Condition-triggered agent-runs (risk > threshold → alert) — not possible.

Hermes-agent has a single-host `fcntl`-based `cron/scheduler.py` (archive/exec-19 §4.1 described the port). That pattern is enterprise-unsuited (no distributed lock, no persistence, no UI, no user-scoped multi-tenancy).

### The driver — 15 concrete use-cases across 4 categories

The scheduler unlocks all of these at once. See §3 for the full table; headline examples:

- **User-initiated (3)**: recurring, one-shot, reminder
- **Dev-admin routines (2)**: cron-routine, webhook-triggered
- **Condition-triggered (1)**: risk/drift/error alerts
- **Infrastructure (9)**: dependency updates, storage tiering, key rotation, metric rollups, memory pruning, cert renewal, harness eval, user digests, health pings, skill promotion

A Go service with a Postgres queue covers **all 15** with one code path. Splitting each into its own one-off cron would triple the maintenance surface.

---

## 2. Non-Goals

- **Not** a workflow-orchestration engine (no saga, no compensation, no deterministic replay). If we need those, Phase 2 migrates to Temporal.
- **Not** a distributed event bus — NATS keeps that role; the scheduler is a **producer** of NATS messages for agent-jobs, not a bus itself.
- **Not** a user-facing "admin dashboard for cron expressions". Cron syntax stays agent-internal; user writes natural language.
- **Not** a replacement for Renovate / Dependabot for dependency-update PRs. Scheduler **triggers** a Renovate run (mode A) or emits a digest message (mode B) — it does not solve version-diffing itself.
- **Not** a real-time reminder service (push notifications within 100ms). Scheduler tick is 60s; sub-minute triggers require a different tool (would use NATS direct-subscribe).

---

## 3. Use-Cases — Complete Taxonomy (15)

| # | Cat | Use-Case | Trigger | Entry Point | Delivery |
|---|---|---|---|---|---|
| 1 | User | Recurring task ("jeden Montag 9:00 portfolio-briefing") | cron | chat (agent / matrix-DM / group-mention) | Matrix-chat-message / email / Telegram |
| 2 | User | One-shot task ("morgen 8:00 check EUR/USD") | scheduled-at | chat | same |
| 3 | User | Reminder ("in 6 Monaten passport renewal") | scheduled-at | chat | same |
| 4 | Dev | Cron routine ("daily security-scan on matrix-repo") | cron | API (REST) | Matrix-room / email |
| 5 | Dev | Webhook-triggered routine ("on-PR open → review-agent") | webhook | HTTP POST endpoint | PR-comment / Matrix |
| 6 | Condition | Alert agent on threshold ("portfolio-risk > X → alert") | periodic-eval | agent-tool + rule-DSL | Matrix-chat |
| 7 | Infra | Dependency updates (bun/uv/go/cargo outdated) | cron (weekly) | internal | Matrix-chat-digest OR Renovate-trigger |
| 8 | Infra | SeaweedFS tiering (Hot→Warm→Cold after age) | cron (daily) | internal | — (internal) |
| 9 | Infra | API-key rotation health-check | cron (weekly) | internal | audit-log + matrix-chat on failure |
| 10 | Infra | Daily metric-rollups → `agent.metrics` | cron (daily 00:00) | internal | — |
| 11 | Infra | Memory pruning (sessions > 30d archive) | cron (weekly) | internal | — |
| 12 | Infra | Cert renewal (if matrix owns certs) | cron (monthly) | internal | audit + alert on failure |
| 13 | Infra | Harness eval-run (weekly benchmark) | cron (weekly Sun 02:00) | internal | matrix-chat benchmark-summary |
| 14 | Infra | User digest emails (daily 08:00 activity summary) | cron (daily per-user) | internal | email |
| 15 | Infra | Provider health-pings (every 5min) | cron (tight interval) | internal | alert on failure |

Note: Use-cases 1-3 are the **primary UX feature**; users see these in a "Meine Tasks" list in control-UI. Use-cases 4-15 are **operational** — they exist without user-visibility except when they fail or emit a digest.

---

## 4. Architecture

### 4.1 Stack decision

| Layer | Choice | Rationale |
|---|---|---|
| Scheduler engine | **River** (MPL-2.0) in Go | Postgres-native (no new infra), transactional, retry/backoff middleware, native cron via `PeriodicJob`, job-status for UI, admin-web-UI. Handles all 15 use-cases with one code path. |
| Host process | `go-appservice` | Already always-on, owns pgxpool + NATS client + Matrix-bridge. Zero new services. |
| Storage | Postgres schema `scheduler.*` | Mirrors `storage.*` / `agent.*` / `hindsight.*` convention. River tables are scoped to this schema (no `public` pollution). |
| Agent-dispatch | NATS subject `matrix.scheduler.job.execute` | Go scheduler publishes; Python agent-worker subscribes. Keeps Python single-responsibility (LLM), Go single-responsibility (scheduling). |
| Go-internal dispatch | in-process River worker | Infra jobs (cleanup, rollups) run inside go-appservice — no hop via NATS. |
| User-facing entry | Agent-tool `schedule_task` | Natural-language parsing happens inside the LLM turn. Control-UI is read-only listing. |

### 4.2 Runtime topology

```
 ┌──────────────────────────────────────────────────────────┐
 │  frontend_merger/  (single UI, see MEMORY.md)            │
 │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
 │  │ features/    │  │ features/    │  │ features/     │   │
 │  │  agent/      │  │  matrix/     │  │  control/     │   │
 │  │  (agent-chat │  │  (DM w/agent │  │  (tasks list, │   │
 │  │   surface)   │  │   or group   │  │  read-only)   │   │
 │  │              │  │   @mention)  │  │               │   │
 │  └─────┬────────┘  └──────┬───────┘  └──────┬────────┘   │
 │        │ BFF /api/agent   │ BFF /api/matrix │ /api/control
 └────────┼──────────────────┼─────────────────┼────────────┘
          │                  │                 │
          ▼                  ▼                 ▼
 ┌─────────────────────────────────────────────────────────┐
 │ go-appservice  ←── HTTP layer, Matrix-bridge, scheduler │
 │  ┌────────────────────────────────────────────────────┐ │
 │  │ internal/scheduler/ (NEW)                          │ │
 │  │  ├── jobs.go      (CRUD scheduler.scheduled_tasks) │ │
 │  │  ├── periodic.go  (River PeriodicJob registration) │ │
 │  │  ├── worker.go    (River Client + Worker setup)    │ │
 │  │  ├── dispatch.go  (NATS publish for agent-jobs)    │ │
 │  │  ├── delivery.go  (Matrix/Email/Telegram/SMTP)     │ │
 │  │  └── routines.go  (Claude-Code-Routines adapter)   │ │
 │  └────────────────────────────────────────────────────┘ │
 └──────────┬─────────────────────────────────┬────────────┘
            │  in-process (Go jobs)            │ NATS publish
            │                                  │ "matrix.scheduler.job.execute"
            ▼                                  ▼
  Infra jobs (tiering, rollups,         python-backend/agent/workers/
  cert, metric, pruning, pings)          scheduler_subscriber.py (NEW)
                                                │
                                                │ reads task_id, user_id,
                                                │ prompt, skill_ids, context
                                                ▼
                                         agent/graph/runner.py
                                         (standard LLM turn)
                                                │
                                                ▼
                                         delivery via Matrix-bridge
                                         (Go) or email/telegram (Go)
```

### 4.3 Why not Temporal now

Matrix's own `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md:42` says:

> `| Produkt-/Business-Workflows | Temporal spaeter gezielt | langlebige, produktkritische Ablaeufe |`

Temporal is the right tool **when**:
- Multi-step workflows need durable execution (survive worker crashes mid-flow)
- Long-running plans (> 10min) need replay semantics
- Saga patterns with compensations
- Human-in-the-loop approval gates

None of that is needed for cron-driven jobs or short LLM turns (<2min). Adding Temporal now means: Temporal server + its own DB + new SDK + new mental model. River gives 90% of production-cron value with zero new infra.

**Migration path to Temporal (Phase 2):** River jobs become Temporal-workflows by wrapping the existing handler functions; the user-facing agent-tool API stays the same. No re-learning for users.

---

## 5. Data Model — `scheduler.*` schema

```python
# Alembic migration 020_scheduler_schema.py (sketch)

op.execute("CREATE SCHEMA IF NOT EXISTS scheduler")

op.create_table(
    "scheduled_tasks",
    sa.Column("task_id", sa.Text, primary_key=True),        # uuid7
    sa.Column("user_id", sa.Text, nullable=False, index=True),
    sa.Column("source", sa.Text, nullable=False),           # "chat_agent" | "chat_matrix_dm" | "chat_matrix_group" | "api" | "github_webhook" | "system"
    sa.Column("kind", sa.Text, nullable=False),             # "recurring" | "one_shot" | "reminder" | "routine" | "condition" | "infra"
    sa.Column("cron_expr", sa.Text, nullable=True),         # null for one_shot/reminder
    sa.Column("scheduled_at", sa.BigInteger, nullable=True),# epoch-ms — used for one_shot/reminder
    sa.Column("prompt", sa.Text, nullable=True),            # the natural-language instruction for agent tasks
    sa.Column("skill_ids", postgresql.ARRAY(sa.Text), nullable=True),  # exec-skills bindings (when §4.2 lands)
    sa.Column("delivery_target", postgresql.JSONB, nullable=True),
    # {kind: "matrix_room", id: "!abc:server"} | {kind: "email", to: "..."} | {kind: "telegram", chat_id: "..."}
    sa.Column("status", sa.Text, nullable=False, server_default="active"),
    # active | paused | completed | cancelled | errored
    sa.Column("max_executions", sa.Integer, nullable=True), # None = unlimited; 1 for one_shot
    sa.Column("execution_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("next_run_at", sa.BigInteger, nullable=True, index=True),
    sa.Column("last_run_at", sa.BigInteger, nullable=True),
    sa.Column("last_output_ref", sa.Text, nullable=True),   # audit_events.id or storage ref
    sa.Column("metadata", postgresql.JSONB, nullable=True), # free-form for routine/condition params
    sa.Column("created_at", sa.BigInteger, nullable=False),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    schema="scheduler",
)
op.create_index("ix_scheduled_tasks_user_status", "scheduled_tasks",
                ["user_id", "status"], schema="scheduler")
op.create_index("ix_scheduled_tasks_next_run", "scheduled_tasks",
                ["next_run_at"], schema="scheduler")

op.create_table(
    "task_executions",
    sa.Column("execution_id", sa.Text, primary_key=True),   # uuid7
    sa.Column("task_id", sa.Text, nullable=False, index=True),
    sa.Column("started_at", sa.BigInteger, nullable=False),
    sa.Column("completed_at", sa.BigInteger, nullable=True),
    sa.Column("status", sa.Text, nullable=False),           # running | completed | failed | cancelled
    sa.Column("trace_id", sa.Text, nullable=True),          # links to agent.traces (exec-18)
    sa.Column("output_ref", sa.Text, nullable=True),        # audit_events.id
    sa.Column("error", sa.Text, nullable=True),
    sa.ForeignKeyConstraint(["task_id"], ["scheduler.scheduled_tasks.task_id"], ondelete="CASCADE"),
    schema="scheduler",
)
```

**Plus River's own tables** (`river_job`, `river_leader`, `river_migration` in the same `scheduler` schema, configured via River's `Schema` option).

### Per-user limits

- Default max active tasks per user: **10** (matches ChatGPT-Tasks constraint).
- Admin override per user via `agent.user_llm_settings.scheduler_max_active_tasks`.
- Hard cap at 50 per user (denial-of-service defense against prompt-injected "add 1000 tasks").

---

## 6. Trigger Types

### 6.1 Time-based (cron + one-shot)

- **Cron expressions**: 5-field standard (`0 9 * * 1` for every Monday 09:00).
- **One-shot via `scheduled_at`**: epoch-ms timestamp; task moves to `status=completed` after one execution.
- Natural-language examples that map to cron:
  - "jeden Tag um 8" → `0 8 * * *`
  - "jeden Montag 9 Uhr" → `0 9 * * 1`
  - "alle 2 Stunden" → `0 */2 * * *`
  - "werktags 17 Uhr" → `0 17 * * 1-5`
- Timezone: user's configured TZ (from `agent.user_llm_settings.timezone`); default UTC if unset.

### 6.2 Event-based (NATS subjects + webhooks)

- NATS-subjects the scheduler listens on (and publishes to):
  - `matrix.scheduler.job.execute` — outgoing, agent-jobs
  - `matrix.ingestion.file.arrived` — incoming, triggers condition-eval
  - `matrix.audit.threshold.crossed` — incoming, triggers alert-agents
- HTTP webhook endpoint: `POST /api/v1/scheduler/trigger/{routine_id}` with bearer-token auth — Claude-Code-Routines-style external trigger.
- GitHub-webhook endpoint: `POST /api/v1/scheduler/webhook/github` — matches Anthropic's routines-on-PR pattern.

### 6.3 Condition-triggered (eval loop)

- Periodic eval: a condition-task runs every N minutes, executes a **pure-eval** rule (no LLM), and only spawns the downstream agent-job if the rule trips.
- Rule DSL (Phase 1, minimal): `expr(metric_name, comparison, threshold)`.
  - Example: `expr("portfolio.var_95", ">", 0.05)`.
- Phase 2: extend to full CEL (Common Expression Language) or re-use OPA.

---

## 7. User-Facing UX — Chat-First

### 7.1 Entry Points (all three surfaces map to the SAME agent-tool)

| Surface | Path | Behaviour |
|---|---|---|
| **Agent-chat** | `frontend_merger/src/features/agent/` | User opens the agent chat, says "jeden Montag 9 Uhr portfolio-briefing". Agent parses, confirms, writes task. |
| **Matrix DM** | user opens a DM room with the agent-matrix-user (`@agent:matrix.local`) | Same parsing, same tool. Delivery default = Matrix-message back to the DM room. |
| **Matrix group** | user @mentions the agent in a group room | Same parsing. Delivery default = the group room. |

All three route through `python-backend/bridge/` (Matrix) or the direct HTTP path (agent-chat) to the **same agent turn**, with the **same agent-tool** available. There is **no separate scheduler UX** per surface.

### 7.2 Agent-Tools (exposed to every agent turn)

```python
# python-backend/agent/tools/scheduling/*.py

@tool
async def schedule_task(
    natural_language: str,
    *,
    context: ToolContext,
) -> dict:
    """Parse user's natural-language scheduling intent and return a
    CONFIRMATION draft. Does NOT commit — user must confirm in chat.
    """

@tool
async def confirm_scheduled_task(
    draft_id: str,
    *,
    context: ToolContext,
) -> dict:
    """Commit a previously-drafted task. Returns task_id + next_run_at."""

@tool
async def list_scheduled_tasks(
    *, context: ToolContext,
) -> list[dict]:
    """Return the user's current active tasks for agent-readable summary."""

@tool
async def cancel_scheduled_task(task_id: str, *, context: ToolContext) -> dict: ...
@tool
async def pause_scheduled_task(task_id: str, *, context: ToolContext) -> dict: ...
@tool
async def resume_scheduled_task(task_id: str, *, context: ToolContext) -> dict: ...
```

**Draft-then-confirm pattern**: LLM-parses may be wrong ("morgen 9" could mean today 09:00 tomorrow morning or 9 PM tomorrow). Two-step prevents silent misinterpretation.

### 7.3 Control-UI — list/edit only

`frontend_merger/src/features/control/tasks/` (new sub-feature):

- List: `/control/tasks` → table of user's tasks (name/prompt, next-run, last-run, status, executions-count)
- Actions: **pause**, **resume**, **edit** (delivery-target change only; prompt/schedule edits go through chat), **cancel**
- **No "+ New Task" button.** Instead: prominent link to `/agent` or "open DM with Agent" with placeholder "Sag mir wann und was".

Rationale documented in `~/.claude/projects/.../memory/project_scheduler_chat_entry.md`.

---

## 8. Developer / Admin Routines (Claude-Code-Routines pattern)

Same table, `source=api` or `source=github_webhook`, `kind=routine`.

### 8.1 API-triggered routine

```
POST /api/v1/scheduler/routines
Authorization: Bearer <admin-token>
Body: {
  "name": "daily-security-scan",
  "cron_expr": "0 3 * * *",
  "prompt": "Scan matrix-core repo for vulnerabilities. Post digest to #security.",
  "skill_ids": ["security-audit"],
  "delivery_target": {"kind": "matrix_room", "id": "!security:matrix.local"}
}
```

### 8.2 Webhook-triggered routine

```
POST /api/v1/scheduler/webhook/github
X-GitHub-Event: pull_request
Body: (GitHub PR payload)
→ Scheduler matches payload to a routine by filter (e.g. "event=opened AND repo=matrix").
→ Executes routine with payload injected into prompt.
```

### 8.3 Routine registry

Separate table `scheduler.routines` (not `scheduled_tasks`) for dev-admin-owned routines. Rows reference `scheduled_tasks` when they spawn instances. Separation prevents user-task limits from affecting infra routines.

---

## 9. Infrastructure Jobs (Category 4)

All 9 run as River `PeriodicJob`s registered at go-appservice startup. Each has a dedicated handler; no prompt / no LLM call.

| Job | Cron | Handler |
|---|---|---|
| Dependency updates | `0 4 * * 1` (Mon 04:00) | `infra_dep_updates.go` — runs `bun outdated` / `uv pip list --outdated` / `go list -m -u all` / `cargo outdated` in each sub-project sandbox, publishes result-JSON to Matrix-room `#infra` OR triggers Renovate-job via GitHub-action-dispatch |
| SeaweedFS tiering | `0 2 * * *` | `infra_storage_tier.go` — scans `storage.artifact_metadata` for age > 30d, moves to cold bucket |
| Key rotation health | `0 5 * * 0` (Sun 05:00) | `infra_key_rotation.go` — tests all user-provider-keys, flags expiring/invalid |
| Metric rollups | `0 0 * * *` (00:00) | `infra_metric_rollup.go` — aggregates `agent.audit_events` + `agent.traces` → `agent.metrics` for the past day |
| Memory pruning | `0 3 * * 0` (Sun 03:00) | `infra_memory_prune.go` — archives `agent.sessions` with completed_at > 30d |
| Cert renewal | `0 6 1 * *` (first of month 06:00) | `infra_cert_renewal.go` — LetsEncrypt ACME run (only if matrix owns certs) |
| Harness eval | `0 2 * * 0` (Sun 02:00) | `infra_harness_eval.go` — triggers `python-backend/agent/harness/evaluator.py` benchmark suite, publishes result |
| User digest emails | per-user cron from `agent.user_llm_settings.digest_schedule` | `infra_user_digest.go` — activity summary email |
| Provider health pings | `*/5 * * * *` | `infra_provider_health.go` — chat-completion probe per provider, alert on failure |

### 9.1 Dependency-update job — two modes

Mode A — Renovate trigger (auto-PR):
- `bun outdated` / `uv pip list --outdated` / `go list -m -u all` / `cargo outdated` run in each sub-project
- Upload outdated-list as artifact
- Trigger a GitHub-action that invokes Renovate with that list
- Renovate opens PRs per Renovate-config
- User reviews/merges normally
- **Requires**: GitHub-token in go-appservice keyvault + Renovate config in `.github/renovate.json`

Mode B — Digest message (review-first):
- Same outdated-check
- Post summary to Matrix-room `#infra` or `#dev` : "3 critical bun updates, 12 minor uv, 5 major cargo — react with `/reviewupdates` to open PRs"
- User reacts → scheduler fires Mode-A path for the flagged subset
- **Requires**: Matrix-room for `#infra` in delivery-target + simple reaction-to-trigger handler

Both modes share the outdated-scan core (`infra_dep_updates.go`); mode is configured per-job in `scheduler.scheduled_tasks.metadata.update_mode`.

---

## 10. Delivery Channels

Go side (`delivery.go`) implements a `Deliverer` interface with 4 built-in impls:

- **MatrixRoomDeliverer** — uses existing Matrix-bridge client (already wired in go-appservice). Posts as agent-matrix-user.
- **EmailDeliverer** — SMTP (matrix owns SMTP-relay creds or uses external provider). User's email from `agent.users` profile.
- **TelegramDeliverer** — Telegram-bot-API (optional; only if `TELEGRAM_BOT_TOKEN` configured).
- **NoopDeliverer** — for infra jobs where "done" = write to `audit_events`, no external surface.

Default delivery per surface (user chat-initiated tasks):
- agent-chat surface → respond in agent-chat UI + write a matrix-message to user's personal matrix-user
- matrix DM → matrix-message to the DM room
- matrix group → matrix-message to the group room
- API/webhook routines → delivery-target must be explicit in request body

---

## 11. Security

### 11.1 Prompt-injection defense

- **Scan cron-bound prompts** with `skills_guard.scan_skill()` at task-creation (treats the `prompt` field as content, scans for exfiltration / injection / destructive patterns).
- Reject with 422 (user-surfaced) if `verdict == "dangerous"`.
- `ask` verdict → confirm-loop in chat: "this prompt has some questionable patterns — confirm you want to schedule it anyway?" before commit.

### 11.2 Per-user scoping

- `user_id` on every task; no cross-user read/write.
- Agent-tools validate `context.user_id` against `scheduler.scheduled_tasks.user_id` on every mutation.
- `skill_ids[]` validated against `agent.agent_skills.allowed_users` (when exec-skills §4.2 lands).

### 11.3 Max-active-task DoS defense

- Default 10 active tasks per user (matches ChatGPT-Tasks).
- Hard cap 50 per user.
- Admin-override via `agent.user_llm_settings.scheduler_max_active_tasks`.

### 11.4 API auth

- API-triggered routines require bearer-token in `agent.user_credentials` with `kind=scheduler_api_token`.
- Webhook endpoints validate `X-Hub-Signature-256` for GitHub.
- Per-route rate-limits via existing `go-appservice` middleware.

---

## 12. Observability

### 12.1 Per-execution tracing

Every task execution creates:

- `agent.traces` row (exec-18) with `kind=scheduler_task_execution`
- `agent.spans` with the LLM-turn (for agent-jobs) or internal-work (for infra-jobs)
- `scheduler.task_executions` row linking the trace
- `audit_events` row with `action=SCHEDULED_TASK_RAN`

### 12.2 Metrics (Prometheus / OpenObserve via exec-17)

- `scheduler_tasks_active` (gauge, per-user)
- `scheduler_task_executions_total` (counter, labels: `kind`, `status`)
- `scheduler_task_duration_seconds` (histogram, labels: `kind`)
- `scheduler_queue_depth` (gauge, from River-stats)

### 12.3 Admin inspection

River ships a web-UI binary (`river ui`) that shows the current Postgres-queue contents. Mount it behind admin-auth on a dev port (e.g. :8099/admin/river). Not exposed publicly.

---

## 13. Phase Plan

### Phase 1 — MVP (target: ~1 week)

- [ ] Alembic migration 020 `scheduler.scheduled_tasks` + `scheduler.task_executions` + River tables in `scheduler` schema
- [ ] `go-appservice/internal/scheduler/` package skeleton: River-client, worker setup, handler registry
- [ ] Handlers for infrastructure jobs 10+11+15 (metric-rollups, memory-pruning, health-pings) — proves the go-internal dispatch
- [ ] NATS dispatch `matrix.scheduler.job.execute` for agent-jobs
- [ ] `python-backend/agent/workers/scheduler_subscriber.py` — NATS-listen + agent-turn-execute + delivery-callback
- [ ] Agent-tools (`python-backend/agent/tools/scheduling/`) — `schedule_task`, `list_scheduled_tasks`, `cancel_scheduled_task`, `pause_scheduled_task`, `resume_scheduled_task`, `confirm_scheduled_task`
- [ ] Control-UI: `/control/tasks` list page (no "+ New" button)
- [ ] Matrix-chat DM handler — agent is reachable as `@agent:matrix.local`, same agent-tools available
- [ ] Delivery: MatrixRoomDeliverer (reuse bridge) + NoopDeliverer
- [ ] Tests: River unit-tests + agent-tool pytest + end-to-end "schedule via agent-chat, fire after 10s, deliver to matrix-room"

### Phase 2 — Polish + more use-cases (~1 week)

- [ ] Infra jobs 7+8+9+12+13+14 (dep-updates mode A+B, tiering, key-rotation, cert-renewal, harness-eval, user-digest)
- [ ] EmailDeliverer + TelegramDeliverer
- [ ] Dev-admin routines — API endpoint + GitHub-webhook endpoint
- [ ] Condition-triggered jobs — minimal rule-DSL
- [ ] Control-UI: edit delivery-target, pause/resume
- [ ] Observability: Prom-metrics + River-UI admin-mount

### Phase 3 — Temporal migration option (future, not committed)

- Driver: user-initiated task needs > 10min runtime OR multi-step human-approval flow OR mandatory saga-compensation
- Migrate `handle_agent_turn` handler from River worker to Temporal workflow; keep River for fire-and-forget infra jobs
- Scheduler table unchanged (still Postgres); Temporal-workflow-id stored in `metadata.temporal_workflow_id`

---

## 14. Verify Gates

### Phase 1 gates

- [ ] `go build ./...` green in go-appservice
- [ ] `go test ./internal/scheduler/...` 100% handler paths covered
- [ ] `pytest python-backend/agent/tools/scheduling/ python-backend/agent/workers/` green
- [ ] Live: user types "jeden Montag 9 Uhr portfolio-briefing" in agent-chat → task lands in `scheduler.scheduled_tasks`
- [ ] Live: matrix-DM with agent-user: same natural-language → same outcome
- [ ] Live: wait-for-next-minute cron-tick → task fires → matrix-room receives the expected message
- [ ] `/control/tasks` shows the task with correct `next_run_at`
- [ ] Cancel via chat (`"cancel my Monday briefing"`) → `status=cancelled`
- [ ] skills_guard scans prompt at creation — dangerous prompt rejected

### Phase 2 gates

- [ ] Dep-update Mode B: scheduled weekly Monday 04:00 → matrix-room `#infra` receives summary
- [ ] Dep-update Mode A: GitHub-action triggered, Renovate PRs visible in repo
- [ ] Email delivery: daily 08:00 user-digest lands in email inbox
- [ ] GitHub-webhook: PR open → routine fires → PR-comment from review-agent
- [ ] Condition-triggered: metric crosses threshold → alert-agent-message in matrix

---

## 15. Open Questions

1. **Natural-language parsing**: Do we re-use LiteLLM (the agent's own model) for cron-parsing, or a dedicated small-model (fast + cheap)? Dedicated means extra model-download; re-use means every schedule-task request costs a full agent-turn-worth of tokens.
2. **Timezone UX**: Store per-user timezone in `agent.user_llm_settings`, or derive from matrix-server locale, or always prompt the user on first schedule-attempt?
3. **Daylight-saving**: cron-expressions with fixed wall-time (e.g. "jeden Montag 9 Uhr") need DST-aware rescheduling. River uses standard cron lib; does it honour DST correctly per-user?
4. **Routine-vs-task distinction**: should dev-routines live in the same `scheduled_tasks` table (with `kind=routine`) or a separate `scheduler.routines` table? Separate gives clean user-limit scoping; same gives unified listing.
5. **Rate-limit for chat-initiated tasks**: user asks agent to schedule 5 tasks in one turn — ok? Or enforce per-turn max?
6. **Condition-rule DSL**: start with hand-rolled `expr(metric, op, threshold)` or adopt CEL from day 1?
7. **Skill-binding**: when exec-skills §4.2 lands, `skill_ids[]` becomes mandatory for agent-jobs — migration path?

---

## 16. Cross-Refs

- `archive/exec-19-devstack-consolidation.md` — former home of §4.1 cron, archived 2026-04-18
- `exec-hermes.md §4.1` — original pattern source, now delegated to this spec
- `exec-16-llm-provider-gateway.md` — scheduled jobs call LLMs via LiteLLM; cost-tracking + rate-limit already integrated
- `exec-17-observability-harness-traces.md` — every execution emits `agent.traces` + `agent.spans`
- `exec-18-unified-agent-schema.md` — schema conventions (kind=scheduler_task_execution)
- `exec-memory.md` — persisted tasks are long-lived; their prompts are user-evidence
- `exec-skills.md` — skill-binding (pending)
- `exec-6-agent-chat-integration.md` — chat-surface (primary entry point)
- `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md §42` — Temporal-as-Phase-2 validation
- Frontend-merge slice `claude-merge-frontend-chat-ui-2OqmH/README.md` — confirms `frontend_merger/src/features/control/` is where `/control/tasks` lives

---

## 17. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-18 | Erstversion. Spec entstanden aus Archivierung von exec-19 §4.1 + Redistribution. Stack-Entscheidung River (Phase 1) + Temporal (Phase 2). UX chat-first via agent-tools. 15 use-cases in 4 Kategorien dokumentiert. Dep-update als explizite Infra-Job-Klasse mit 2-Mode-Integration (Renovate-trigger + Matrix-digest). Scheduler-DM-Entry über `@agent:matrix.local` festgehalten — gleiches Verhalten wie agent-chat, keine separate UX. |
