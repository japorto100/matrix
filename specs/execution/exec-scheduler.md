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

### 4.3 Why not Temporal now → `exec-scheduler2.md §7`

Short answer: Phase-1 LLM turns are short (< 2min), cron-driven, and
don't need saga/replay/human-approval — River covers 90% of the
production-cron value with zero new infra. The detailed rationale +
Temporal migration path lives in the Phase-2 spec §7 alongside the
Phase-3 Temporal discussion.

---

## 5. Data Model — `scheduler.*` schema

**Implemented**: Alembic migration **019_scheduler_schema** + follow-up
**020_scheduler_cap_trigger_fix** (Lane-E hard-cap bypass fix). Migration
019 is the primary — 020 only patches the trigger function.

```python
# python-backend/alembic/versions/019_scheduler_schema.py

op.execute("CREATE SCHEMA IF NOT EXISTS scheduler")

op.create_table(
    "scheduled_tasks",
    sa.Column("task_id", sa.Text, primary_key=True),        # hex-16-byte ULID from Python helper
    sa.Column("user_id", sa.Text, nullable=False),
    sa.Column("source", sa.Text, nullable=False),
    # CHECK: chat_agent | chat_matrix_dm | chat_matrix_group | api | github_webhook | system
    sa.Column("kind", sa.Text, nullable=False),
    # CHECK: recurring | one_shot | reminder | routine | condition | infra
    sa.Column("cron_expr", sa.Text, nullable=True),
    sa.Column("scheduled_at", sa.BigInteger, nullable=True),
    sa.Column("tz", sa.Text, nullable=False, server_default="UTC"),
    sa.Column("prompt", sa.Text, nullable=True),
    sa.Column("skill_ids", postgresql.ARRAY(sa.Text), nullable=True),
    sa.Column("delivery_target", postgresql.JSONB, nullable=True),
    sa.Column("status", sa.Text, nullable=False, server_default="active"),
    # CHECK: active | paused | completed | cancelled | errored
    sa.Column("max_executions", sa.Integer, nullable=True),
    sa.Column("execution_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("next_run_at", sa.BigInteger, nullable=True),
    sa.Column("last_run_at", sa.BigInteger, nullable=True),
    sa.Column("last_output_ref", sa.Text, nullable=True),
    sa.Column("metadata", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.BigInteger, nullable=False),
    sa.Column("updated_at", sa.BigInteger, nullable=True),
    # CHECK constraint on trigger-field coherence:
    #   (kind in ('cron','routine','condition','infra') AND cron_expr NOT NULL)
    #   OR (kind in ('one_shot','reminder') AND scheduled_at NOT NULL)
    #   OR kind in ('webhook','condition','composite')
    schema="scheduler",
)
# Indexes: (user_id, status) | (next_run_at) | (kind, status)
# Plus trigger trg_scheduled_tasks_notify → pg_notify('scheduler_task_changed')
#     trigger trg_scheduled_tasks_active_limit → hard-cap 50 per user

op.create_table(
    "task_executions",
    sa.Column("execution_id", sa.Text, primary_key=True),
    sa.Column("task_id", sa.Text, nullable=False),
    sa.Column("started_at", sa.BigInteger, nullable=False),
    sa.Column("completed_at", sa.BigInteger, nullable=True),
    sa.Column("status", sa.Text, nullable=False, server_default="running"),
    # CHECK: running | completed | failed | cancelled | timeout
    sa.Column("trace_id", sa.Text, nullable=True),
    sa.Column("output_ref", sa.Text, nullable=True),
    sa.Column("result_summary", sa.Text, nullable=True),
    sa.Column("error", sa.Text, nullable=True),
    sa.Column("duration_ms", sa.Integer, nullable=True),
    sa.ForeignKeyConstraint(["task_id"], ["scheduler.scheduled_tasks.task_id"], ondelete="CASCADE"),
    schema="scheduler",
)
# Indexes: (task_id, started_at DESC) | (trace_id WHERE NOT NULL)
```

**Plus River's own tables** (`river_job`, `river_leader`, `river_migration`
in the same `scheduler` schema, configured via `river.Config{Schema:"scheduler"}`).
`rivermigrate` runs at Go startup — idempotent so co-existence with
Alembic-owned tables is safe.

### Trigger details

- **`trg_scheduled_tasks_notify`** (AFTER INSERT/UPDATE/DELETE): fires
  `pg_notify('scheduler_task_changed', json{task_id, op, status})`. The
  Go `CronRegistry.WatchNotifications` LISTEN-loop picks this up and
  `river.PeriodicJobs().Add/Remove`s without restarting the client.

- **`trg_scheduled_tasks_active_limit`** (BEFORE INSERT OR UPDATE): the
  hard-cap trigger. Post-020 it gates on `becoming_active := status='active'
  AND (INSERT OR OLD.status != 'active')` so the pause→insert→resume
  bypass is closed. Excludes `NEW.task_id` from the count to avoid
  off-by-one.

### Per-user limits

- **Soft cap: 10 active tasks per user** — enforced at the agent-tool layer
  (`schedule_task` checks `count_active_for_user()` before INSERT).
  Admin override planned via `agent.user_llm_settings.scheduler_max_active_tasks`.
- **Hard cap: 50 active tasks per user** — enforced at the DB trigger,
  cannot be bypassed by pause+insert+resume (post migration 020).

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

### 6.2 — 6.3 Event-based + Condition-triggered → `exec-scheduler2.md`

Phase-1 implements only the time-based trigger (§6.1). Webhook triggers
and periodic-eval condition tasks are Phase-2 scope; their detailed
design lives in the Phase-2 spec (D-1 for webhook auth, D-3 for rule-
DSL choice, implementation items P2b-3 + P2c-1/2).

The only NATS subject Phase-1 uses is `matrix.scheduler.job.execute`
(outgoing, Go → Python subscriber). The `matrix.ingestion.file.arrived`
and `matrix.audit.threshold.crossed` incoming subjects come online with
the condition-eval worker in Phase-2.

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

**Design note (2026-04-19 revision):** the earlier two-step
`schedule_task(nl) → confirm_scheduled_task(draft_id)` pattern has been
collapsed into a single `schedule_task(...)` tool with explicit
structured fields (``kind``, ``cron_expr | scheduled_at_ms``, ``prompt``,
``tz``, ``delivery_target``, ``skill_ids``, ``max_executions``). Reason:
the agent LLM already parses natural language in every other tool call —
a regex- or rules-based NL-parser dedicated to scheduling duplicates
reasoning the model does (better), only works for languages we code,
and is redundant. Confirmation-before-write happens in the LLM's chat
turn ("Soll ich 'jeden Montag 09:00 UTC, Portfolio-Briefing' anlegen?
Bestätigen mit 'ja'."), not in a separate tool step.

Phase-1 ships **eight** tools:

```python
# python-backend/agent/tools/scheduler_tools.py

@tool
async def schedule_task(
    kind: Literal["recurring", "one_shot", "reminder"],
    prompt: str,
    *,
    cron_expr: str | None = None,      # required for 'recurring'
    scheduled_at_ms: int | None = None, # required for 'one_shot'/'reminder'
    tz: str = "UTC",
    source: str = "chat_agent",
    delivery_target: dict | None = None,
    skill_ids: list[str] | None = None,
    max_executions: int | None = None,
    context: ToolContext,
) -> dict:
    """Create a scheduled task. The LLM is expected to infer the fields
    from the user's natural-language request and echo back a summary for
    user confirmation BEFORE calling this tool."""

@tool
async def schedule_list(limit: int = 50, *, context: ToolContext) -> dict: ...
@tool
async def schedule_pause(task_id: str, *, context: ToolContext) -> dict: ...
@tool
async def schedule_resume(task_id: str, *, context: ToolContext) -> dict: ...
@tool
async def schedule_cancel(task_id: str, *, context: ToolContext) -> dict: ...
@tool
async def schedule_list_runs(task_id: str, limit: int = 20, *, context: ToolContext) -> dict: ...
@tool
async def schedule_edit(task_id: str, *, prompt=None, cron_expr=None,
                        scheduled_at_ms=None, tz=None, delivery_target=None,
                        max_executions=None, context: ToolContext) -> dict:
    """Patch editable fields (NOT kind — cancel + recreate for that)."""
@tool
async def schedule_run_now(task_id: str, *, context: ToolContext) -> dict:
    """Manual one-off fire; does not touch the cron schedule."""
```

### 7.3 Control-UI — list/edit only

`frontend_merger/src/features/control/tasks/` (new sub-feature):

- List: `/control/tasks` → table of user's tasks (name/prompt, next-run, last-run, status, executions-count)
- Actions: **pause**, **resume**, **edit** (delivery-target change only; prompt/schedule edits go through chat), **cancel**
- **No "+ New Task" button.** Instead: prominent link to `/agent` or "open DM with Agent" with placeholder "Sag mir wann und was".

Rationale documented in `~/.claude/projects/.../memory/project_scheduler_chat_entry.md`.

---

## 8 — 9 Dev/Admin Routines + Remaining Infra Jobs → `exec-scheduler2.md`

Phase-1 covers only **3 of the 9 infra jobs from §3**: metric-rollup
(UC 10, landed via gap-closer migration 021), memory-prune (UC 11),
provider health-pings (UC 15 via `HealthPingWorker`). The remaining 6
jobs (dep-updates, seaweedFS tiering, key-rotation, cert-renewal,
harness-eval, user-digest) are Phase-2 scope — each becomes a new
River worker in `internal/scheduler/handlers/`, landing independently
as demand hits them. See exec-scheduler2.md §2 Phase-2c item P2c-4.

Dev/admin routines (API-triggered, GitHub-webhook-triggered, Claude-
Code-Routines pattern) are also Phase-2 — they share `scheduler.
scheduled_tasks` with `kind=routine` (see D-6 decision in exec-
scheduler2.md) and get their own REST endpoints (P2b-2 / P2b-3 in
that spec).

### 8.1 Harness A/B backfill worker (new, Phase-2 scope)

**Status:** Consumer-TODO — scheduler infra exists (River), worker code not yet written.
**Cross-ref:** `exec-harness.md §4g.4`.

Phase-C (2026-04-20) shipped the A/B dispatcher (`agent/runners/dispatcher.py`) which INSERTs rows into `agent.ab_experiments` with `harness_fitness_score` NULL. `agent/harness/scorer.py::backfill_ab_experiment_fitness` fills that column when `score_session(thread_id)` is invoked — but nobody calls it automatically today.

This is a **periodic backfill worker** that belongs in `internal/scheduler/handlers/`:

* **Trigger:** cron `*/15 * * * *` (every 15 min) — tunable via Phase-2 admin-surface.
* **Query:** `SELECT thread_id FROM agent.ab_experiments WHERE finished_at IS NOT NULL AND harness_fitness_score IS NULL LIMIT 200`.
* **Action:** POST to a new internal endpoint `/admin/harness/score-session` (lives in python-backend, not go-appservice — scorer is Python) with `{thread_id}`; endpoint calls `score_session(thread_id)` which internally dispatches the backfill UPDATE.
* **Idempotency:** natural — the UPDATE only sets the column when fitness is computable; re-running on an already-scored row just re-UPDATEs the same value.
* **Scope:** add as Phase-2c item P2c-5 (new), or inline under P2c-4 "harness-eval" if preferred — that item was originally for full harness evaluation runs, this is the lighter periodic-scorer variant that's a strict prerequisite for any A/B analysis.

Without this worker the A/B experiment table accumulates rows with no quality signal. The dispatcher is shipped; the consumer is the last blocker for end-to-end A/B data flow.

---

## 10. Delivery Channels

Phase-1 implements **Matrix-only** delivery via the existing
`natsbridge` + Go appservice bridge (the same path used by the Matrix-
chat reply flow). No new code — scheduled-task results land in the
target Matrix room via `@agent:matrix.local`.

Alternative channels (email, telegram) are Phase-2 scope — see
`exec-scheduler2.md` items P2a-2 (EmailDeliverer) and P2a-3
(TelegramDeliverer). Credentials-storage decision in D-2 of that spec.

Default delivery per surface (Phase-1 user-initiated tasks):

- agent-chat surface → matrix-message back to user's personal matrix-user
- matrix DM → matrix-message to the DM room
- matrix group → matrix-message to the group room

`delivery_target` JSONB schema accepts all delivery-kinds at the
data-layer (`matrix_room`, `matrix_dm`, `email`, `telegram`) — the
non-Matrix kinds are just not yet wired on the dispatch side.

---

## 11. Security

### 11.1 Prompt-injection defense

**Implementation:** `python-backend/agent/security/prompt_scanner.py::scan_scheduled_task_prompt` (Phase-B P3 DONE, 2026-04-20).
**Owning-spec:** `exec-security.md §4` (pattern inventory, rationale, out-of-scope items).

Wired in both `ScheduleTaskTool.execute` (INSERT path) and `ScheduleEditTool.execute` (UPDATE-with-prompt-change path, prevents `insert benign → patch malicious` bypass).

Two-state gate: `PromptRisk.LOW` → pass; `PromptRisk.HIGH` → tool returns `{"ok": false, "error": "prompt_blocked", "message": reason, "matched_patterns": [...]}`. WARN-level log includes `user_id` + pattern-ids for audit.

Covered shapes: invisible/bidi-override unicode, prompt-injection phrases (`ignore previous instructions`), shell-exfil (`curl $API_KEY`), secret-file reads (`cat .env`), host-takeover (`authorized_keys`, `/etc/sudoers`), destructive filesystem (`rm -rf /`, `rm -rf ~`), subprocess-spawn keywords, credential-leak phrases.

No MEDIUM/`ask` tier — hot-path wants an on/off gate. Partial-match warnings belong in an async audit consumer (Phase-C).

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

### Phase 1 — MVP ✅ DONE (2026-04-19, 9 commits on main)

Actual lane breakdown vs. the pre-impl plan:

- [x] **Lane P** — River dep pinned (`riverdriver` + `riverpgxv5` v0.35.0),
  shared pgxpool refactor in `handler.Server`, JetStream-enabled NATS
  already in `docker-compose.yml`. Commit `be7b367`.
- [x] **Lane A** — Alembic migration `019_scheduler_schema` (next free
  number, not 020 as the draft guessed) with `scheduler.scheduled_tasks`
  + `scheduler.task_executions` + notify trigger + cap trigger. Commit `a57e9db`.
- [x] **Lane F** — Service-user constants in Go + Python (no DB seed
  needed — pseudo-user id string). Env vars documented in `docs/env-vars.md`.
  Rolled into `a57e9db`.
- [x] **Lane B** — `go-appservice/internal/scheduler/` package complete:
  `scheduler.go` lifecycle, `store.go` (PgStore), `cron_registry.go` with
  NOTIFY hot-reload, `workers.go` (MatrixDispatchWorker, HealthPingWorker,
  MemoryPruneWorker), `routes.go` (REST), `payloads.go` (JobExecutePayload,
  HeartbeatPayload), `schedule.go` (robfig/cron wrapper),
  `jetstream_adapter.go`, plus `natsbridge/jetstream.go`. River-migrate
  runs at Start, 30s drain on Stop before HTTP shutdown.
- [x] **Lane C** — `python-backend/agent/scheduler/` package:
  `db.py` asyncpg helpers, `runner_adapter.py` drains SSE generator,
  `subscriber.py` durable JetStream consumer with 30s in_progress
  heartbeat, `handlers.py` infra stubs, `publisher.py` for manual fires,
  `app_wire.py` lifespan hook. **8 agent-tools** in
  `agent/tools/scheduler_tools.py`: `schedule_task`, `schedule_list`,
  `schedule_pause`, `schedule_resume`, `schedule_cancel`,
  `schedule_list_runs`, `schedule_edit`, `schedule_run_now`.
- [x] **Lane D** — Frontend tasks UI at `frontend_merger/src/app/control/tasks`
  + `features/control/components/TasksTab.tsx` + BFF proxy + query hooks.
  Runs drawer, pause/resume/cancel/delete, empty-state with chat-link.
  No "Add Task" form (chat-first rule).
- [x] **Lane E** — Unit tests: 10 Python (parity, runner-adapter drain)
  + Go (`payloads_test.go`, `workers_test.go` with fake JetStream/Loader/
  ExecStore). Architecture fix: rules-based NL parser removed — LLM is
  the parser (language-agnostic, no redundant code).
- [x] **sota-verify PASS** — adversarial run found 3 FAILs + 2 PARTIALs
  (TZ ignored, cap bypass, ownership missing, ack race, userId hardcoded);
  all fixed in `00fab99`. Migration `020_scheduler_cap_trigger_fix`
  installed as part of the security-gate fix.

Phase-1 use-cases covered: **UC 1+2+3+10+11+15** from §3 (user recurring,
user one-shot, user reminder, metric-rollup infra, memory-prune infra,
chat-initiated creation via all three surfaces).

### Phase 2 — extracted to `exec-scheduler2.md`

All Phase-2 implementation items — Email/Telegram delivery, dev-admin
routines, GitHub-webhook triggers, condition-DSL, remaining infra jobs
(dep-updates, tiering, key-rotation, cert-renewal, harness-eval,
user-digest), Prom-metrics endpoint, Control-UI inline editing — moved
to `specs/execution/exec-scheduler2.md` (2026-04-19). That spec also
collects the 8 open design decisions (D-1…D-8) that block coding.

Landed in Phase-1 itself (post-DONE same-day gap-closers):

- [x] **`agent.metrics` table** — migration 021_agent_metrics (2026-04-19)
      + MetricRollupWorker (hourly :05)
- [x] **Per-turn rate-limit** — `schedule_task` rejects when the user
      created > 5 tasks in the last 60s (`count_recent_inserts_for_user`)

### Phase 3 — extracted to `exec-scheduler2.md §7`

The Temporal migration option lives in the Phase-2 spec alongside its
prerequisite discussions (long-running turns, saga / compensation,
human-approval gates). Not committed, still speculative.

---

## 14. Verify Gates

### Phase 1 gates — static / build / test

All run at top of main after commit `00fab99`:

- [x] `cd go-appservice && go build -tags goolm ./...` — clean, no output
- [x] `cd go-appservice && go test -tags goolm -count=1 ./internal/scheduler/...`
      → `ok matrix/go-appservice/internal/scheduler 0.004s`
      (covers `payloads_test.go`, `workers_test.go` — fake-JetStream +
      fake-Loader/ExecStore, no real broker or DB)
- [x] `cd go-appservice && golangci-lint run --timeout 180s ./internal/scheduler/... ./internal/natsbridge/... ./internal/handler/...`
      → `0 issues.` (full `.golangci.yml` suite: errcheck, govet,
      staticcheck, gosec, wrapcheck, modernize, revive, etc.)
- [x] `cd python-backend && .venv/bin/ruff check agent/scheduler/ agent/tools/scheduler_tools.py tests/agent/scheduler/`
      → `All checks passed!`
- [x] `cd python-backend && .venv/bin/python -m pytest tests/agent/scheduler/ -x -q`
      → `10 passed in 0.96s` (cross-language constants parity,
      runner-adapter SSE-drain, service-user predicates)
- [x] `cd python-backend && .venv/bin/python -m alembic upgrade 020_scheduler_cap_trigger_fix --sql > /dev/null`
      → Offline SQL dry-run clean for migrations 019 + 020 end-to-end
- [x] `cd python-backend && .venv/bin/python -c "from agent.tools.registry import ToolRegistry; r=ToolRegistry.load(); print([t.name for t in r.all() if t.name.startswith('schedule')])"`
      → 8 `schedule_*` tools registered
- [x] `cd frontend_merger && bun run typecheck && bun run lint`
      → tsc clean, biome 0 issues

### Phase 1 gates — adversarial (sota-verify)

Both runs against the scheduler implementation on main:

- [x] **Run 1** (commit `047ba7c`): PARTIAL verdict — 3 FAILs (TZ, cap
      bypass, ownership) + 2 PARTIALs (ack race, userId hardcoded) +
      concrete file:line fix suggestions.
- [x] **Run 2** (commit `00fab99`): **PASS** verdict — all 5 findings
      confirmed FIXED, no new defects introduced by the fixes.

### Phase 1 gates — live (E2E harness exists, runs on-demand)

Live tests live at `python-backend/tests/e2e/test_scheduler_flow.py`
and are marked `@pytest.mark.integration`. They skip by default with a
helpful reason (conftest does a TCP probe on :5433 + :4222 + :9000).
Run via:

    ./scripts/scheduler-e2e.sh

or manually:

    cd python-backend
    RUN_INTEGRATION=1 .venv/bin/python -m pytest tests/e2e/ -v -m integration

Implemented gates (code path + DB assertion — no LLM mocking, exercises
the real store/trigger/NATS/REST layers):

- [x] **test_gate_insert_task_via_tool** — INSERT via `scheduler_db.insert_task`
      (the path `schedule_task` tool uses). Asserts status=active,
      cron_expr preserved, tz preserved.
- [x] **test_gate_notify_trigger_fires** — asyncpg LISTEN on
      `scheduler_task_changed`; INSERT → payload arrives within 3s with
      correct task_id + op=INSERT. Covers Go `CronRegistry.WatchNotifications`
      prerequisite.
- [x] **test_gate_hard_cap_trigger_blocks** — 50 active tasks INSERT,
      51st raises `CheckViolationError`. Plus regression: pause 30 →
      insert 30 more → resume attempt on paused row fails with
      CheckViolation (post-020 bypass fix).
- [x] **test_gate_ownership_enforced_on_rest** — PATCH /tasks/{id}
      with wrong user_id → 404 + row unchanged. Correct user_id → 200.
- [x] **test_gate_run_now_publishes_to_jetstream** — `publish_fire`
      path (same as `schedule_run_now` tool) emits
      JobExecutePayload to `matrix.scheduler.job.execute`. Ephemeral
      ad-hoc consumer asserts task_id + execution_id + owner_user_id.

Still gated on a running real agent-turn (LLM API costs):

- [ ] Live cron-tick end-to-end: minute-interval task fires → Python
      subscriber runs full agent turn → matrix-room receives delivered
      message → `task_executions` row status=completed
- [ ] Live chat-to-DB via agent-chat UI
- [ ] Live `/control/tasks` UI rendering against real DB

### Phase 2 gates → `exec-scheduler2.md §3`

Dep-update, email/telegram delivery, GitHub-webhook, condition-triggered
verify-gates all moved to the Phase-2 spec. The two stress-tests that
were originally in this section are Phase-1 security regressions — they
stayed here and are already covered by the E2E harness:

- [x] ~~Hard-cap stress test~~ → `test_gate_hard_cap_trigger_blocks`
      in `tests/e2e/test_scheduler_flow.py` — 51st INSERT + pause+insert+
      resume bypass regression
- [x] ~~Ownership stress test~~ → `test_gate_ownership_enforced_on_rest`
      — wrong-user-id PATCH expects 404, correct user_id expects 200

---

## 15. Open Questions

**Resolved in Phase-1:**

1. ~~**Natural-language parsing**~~ → **Resolved**: the agent LLM is
   the parser. Merged `schedule_draft` + `confirm_scheduled_task` into
   one `schedule_task` tool; confirmation happens in the LLM's chat
   turn before the call. Language-agnostic; no regex parser.
2. ~~**Timezone UX**~~ → **Partially resolved**: `tz` is a required
   column; LLM infers from context. Where to canonically persist a
   user's default tz (`agent.user_llm_settings.timezone`?) is an
   open question for when we go multi-user — not scheduler-scoped.
3. ~~**Daylight-saving**~~ → **Resolved**: `locScheduler` wrapper in
   `cron_registry.go` converts evaluation to the task's IANA
   `time.Location` before `Next()`. Go's `time` package handles DST.
4. ~~**Rate-limit per turn**~~ → **Resolved**: `schedule_task` rejects
   when user created > 5 tasks in the last 60s (`burst_rate_limit`
   error surfaced to the LLM).

**Deferred to `exec-scheduler2.md`:**

5. Routine-vs-task table separation → **D-6** in exec-scheduler2.md
6. Condition-DSL (hand-rolled vs CEL) → **D-3** in exec-scheduler2.md
7. Skill-binding migration path → **D-7** in exec-scheduler2.md (naturally
   resolved when exec-skills §4.2 lands; no Phase-2 work expected)

**Deferred to `exec-control-auth.md` (not yet written):**

8. Control-UI `userId="local"` placeholder is an app-wide auth wiring
   problem, not scheduler-specific. Same placeholder appears in
   `useOverview`, `useContextInspector`. Fix in one repo-wide sweep.

---

## 16. Cross-Refs

- **`exec-scheduler2.md`** — Phase-2 (delivery, routines, conditions,
  remaining infra jobs) + Phase-3 (Temporal option). All design-
  decisions blocking coding are collected there as D-1..D-8.
- `archive/exec-19-devstack-consolidation.md` — former home of §4.1 cron, archived 2026-04-18
- `exec-hermes.md §4.1` — original pattern source, now delegated to this spec
- `exec-16-llm-provider-gateway.md` — scheduled jobs call LLMs via LiteLLM; cost-tracking + rate-limit already integrated
- `exec-17-observability-harness-traces.md` — every execution emits `agent.traces` + `agent.spans`
- `exec-18-unified-agent-schema.md` — schema conventions (kind=scheduler_task_execution)
- `exec-memory.md` — persisted tasks are long-lived; their prompts are user-evidence
- `exec-skills.md` — skill-binding (pending)
- `exec-harness.md §4g` — Phase-C A/B fitness backfill; §8.1 here documents the scheduled-worker consumer
- `exec-6-agent-chat-integration.md` — chat-surface (primary entry point)
- `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md §42` — Temporal-as-Phase-2 validation
- Frontend-merge slice `claude-merge-frontend-chat-ui-2OqmH/README.md` — confirms `frontend_merger/src/features/control/` is where `/control/tasks` lives

---

## 17. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-18 | Erstversion. Spec entstanden aus Archivierung von exec-19 §4.1 + Redistribution. Stack-Entscheidung River (Phase 1) + Temporal (Phase 2). UX chat-first via agent-tools. 15 use-cases in 4 Kategorien dokumentiert. Dep-update als explizite Infra-Job-Klasse mit 2-Mode-Integration (Renovate-trigger + Matrix-digest). Scheduler-DM-Entry über `@agent:matrix.local` festgehalten — gleiches Verhalten wie agent-chat, keine separate UX. |
| 2026-04-19 | Phase-1 Implementation **DONE** (9 commits on main). Lanes P/A/F/B/C/D/E + sota-verify fixes. Divergences from original spec: (a) Migration number is **019_scheduler_schema** (next free), not 020 as draft guessed — plus **020_scheduler_cap_trigger_fix** for the Lane-E cap-bypass fix. (b) Tool count **8** (added `schedule_edit` + `schedule_run_now`; merged `schedule_draft` + `confirm_scheduled_task` → single `schedule_task`). (c) Rules-based NL parser **removed** — LLM-native parsing in single-tool. (d) Per-task IANA tz support via `locScheduler` wrapper; DST handled correctly. (e) ack_wait 600s + 30s in_progress heartbeat for long turns. (f) ownership-gating on Go REST PATCH/DELETE/GET/runs. (g) frontend_merger `/control/tasks` uses BFF proxy `/api/scheduler/*` (new), separate from `/api/control/*`. (h) `agent.metrics` doesn't exist in Phase-1 → `metric_rollup` handler deferred, infra demos are health_ping + memory_prune. Deferred to Phase-2 live tests: cron-tick fire end-to-end, NOTIFY hot-reload, matrix-delivery. sota-verify **PASS** after fixes (commit `00fab99`). |
| 2026-04-19 | **Phase-1 gap-closers** (post-Phase-1 same-day). Migration **021_agent_metrics** + MetricRollupWorker (hourly :05) re-enables the deferred `metric_rollup` infra handler. E2E harness at `python-backend/tests/e2e/test_scheduler_flow.py` — 5 `@pytest.mark.integration` tests covering insert-path, NOTIFY trigger, hard-cap + bypass regression, REST ownership, run_now → JetStream publish. Skip-by-default with clean TCP-probe messages; opt-in via `RUN_INTEGRATION=1` or `scripts/scheduler-e2e.sh`. No new docker-compose profile — existing default already provides nats+postgres+tuwunel. Full test suite: 212 passed + 5 integration-skipped. |
| 2026-04-19 | **Phase-2 + Phase-3 content extracted** to new slice `exec-scheduler2.md`. This spec is now **Phase-1-complete + verify-gates-only**, archivable once the 3 remaining LLM-API-live gates are run. Extracted sections: §4.3 Temporal rationale → scheduler2 §5, §6.2–§6.3 event-based + condition-triggered triggers → scheduler2 §4a.1–4a.2, §8 dev/admin routines → scheduler2 §4a.3, §9 infra jobs (7+8+9+12+13+14) → scheduler2 §4a.4, §10 email/telegram delivery → scheduler2 §4a.5. §13 Phase-2 + Phase-3 plans → scheduler2 §2 + §5. §14 Phase-2 gates → scheduler2 §3. 8 design decisions (D-1..D-8) collected in scheduler2 §1 so coding can start once resolved. Also **per-turn rate-limit implemented** (`burst_rate_limit` in `schedule_task` — 5 tasks/60s per user). |
