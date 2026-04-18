# exec-hermes — Adoption-Analyse von `_ref/hermes-agent` für matrix

> ## STATUS: **ENTWURF — NICHT FREIGEGEBEN**
>
> **Dies ist eine Analyse und Adoption-Roadmap, kein genehmigter Plan.** Muss vor Implementierung **deeper besprochen** werden, insbesondere:
>
> 1. CLI-vs-Enterprise-Übersetzung pro Pattern (siehe §2)
> 2. Priorisierung gegen bestehende Execs (exec-memory, exec-harness, exec-context, exec-11, exec-15, exec-17, exec-18)
> 3. **Architekturfrage "Graph vs Loop vs Hybrid"** — offene Diskussion (§9)
> 4. Test-Budget und Maintenance-Cost pro adoption-Pattern
>
> **Hermes ist ein CLI-Agent (Single-Tenant-Selfhost), matrix ist Enterprise (Multi-Tenant-fähig).** Jede Adoption muss diese Substratverschiebung bewusst mitdenken — siehe Translation-Matrix in §2.

> Erstellt: 2026-04-18
> Referenz-Index: `_ref/hermes-agent/` via gitnexus (47,734 nodes, 1,707 Files)
> Hermes-Commits 2026-04, Hermes 4 Paper: arxiv 2508.15204
> Querverweise: exec-harness, exec-context, exec-memory, exec-11, exec-15, exec-16, exec-17, exec-18, exec-12, exec-10, exec-skills

---

## 0. TL;DR

Hermes-Agent ist ein **enormer Fundus an produktionsgetesteten Mikro-Patterns** (47k nodes über 326 Python-Files). Die interessanten Teile sind **nicht das Framework als Ganzes** (CLI-zentriert), sondern isolierbare Subsysteme: `ContextEngine`-ABC, `MemoryProvider`-ABC, Cron-Scheduler, Skills-Guard, Checkpoint-Manager, Credential-Pool, Error-Classifier, Rate-Limit-Tracker, Prompt-Caching.

**Adoption-Strategie:** Cherry-pick **nach Pattern, nicht nach File**. Jedes adaptierte Stück wird auf matrix-Substrate (Postgres, NATS, go-appservice, Valkey) übersetzt — nicht 1:1 kopiert.

**Architekturfrage:** Hermes ist klar **Agno-Style** (linearer Loop + pluggable Engines), nicht LangGraph. Matrix nutzt aktuell LangGraph. Empfehlung (detail §9): **Hybrid** — LangGraph für komplexe deterministische Flows behalten, parallel einen agno-style `SimpleAgentLoop` für einfache Chat-Task einführen. Evaluieren, welches bei welchem Use-Case robuster ist.

---

## 1. Was Hermes wirklich ist (honest assessment)

### Größenordnung
- **326 Python-Files, 184k Code-Zeilen** (ohne Tests/Skills)
- **47,734 gitnexus-nodes** (davon ~25k Embeddings)
- 561 Markdown-Files (viele Skills + Docs)
- 30 Tools, 11 Memory-Provider, 16 Gateway-Platforms
- TeX/PDF: Hermes-4 Paper als Bestandteil

### Architektur-Essenz
```
run_agent.py (AIAgent-Klasse)
  └─ environments/agent_loop.py   ← DER Main-Loop (linear, nicht Graph!)
       ├─ prompt_builder.py       ← System-Prompt-Assembly
       ├─ context_engine (ABC)    ← Plugin — Compression/Compaction
       ├─ memory_provider (ABC)   ← Plugin — Retain/Recall
       ├─ tools/registry.py       ← Pluggable Tool-Set
       ├─ credential_pool.py      ← API-Key-Rotation
       ├─ rate_limit_tracker.py   ← x-ratelimit-* Header parsen
       ├─ error_classifier.py     ← Structured Failover-Taxonomy
       ├─ retry_utils.py          ← Recovery-Dispatch
       └─ trajectory.py           ← ShareGPT JSONL export
```

Drumherum:
- `gateway/` — 16 Delivery-Platforms (Matrix, Telegram, Discord, Slack, SMS, Email, etc.)
- `cron/` — Scheduled Jobs mit Multi-Platform-Delivery
- `acp_adapter/` — Agent Communication Protocol (Agent-to-Agent)
- `batch_runner.py` — Parallel Multi-Prompt-Processing via multiprocessing

### CLI vs Enterprise — warum das wichtig ist

| Hermes-Design-Assumption | Enterprise-Realität bei matrix |
|---|---|
| `~/.hermes/` als State-Root (ein User) | Multi-Tenant, per-User-Scoping, `agent.*` Postgres-Schema |
| SQLite (`hermes_state.py`) — single-machine | Postgres cluster-weit, `agent.sessions` + `agent.traces` (exec-18) |
| `fcntl` File-Locks (`cron/scheduler.py`) | Postgres advisory-locks oder Valkey / NATS-KV |
| `multiprocessing.Pool` im `batch_runner.py` | NATS-JetStream Worker-Pool, horizontal skalierbar |
| Cron-Delivery-Env-Vars (`MATRIX_HOME_ROOM`) | Per-User-Prefs in DB, nicht Env |
| `~/.hermes/skills/*.md` als Filesystem | `agent.skills` DB-Tabelle + SeaweedFS/Garage für Assets |
| `~/.hermes/checkpoints/` Shadow-Git-Repos | Workspace-Dirs im go-appservice oder exec-12 WASM-Sandbox |
| Single-Auth — OAuth-CLI-Flow | go-appservice RBAC + KeyVault (AESGCMVault) |
| `state.sqlite` Trajektorien | `agent.traces` + `agent.spans` (exec-18) |
| CLI-Tick-Loop (60s Thread) | NATS-cron-trigger oder Temporal / APScheduler via Postgres |

**Rule:** Jedes aus Hermes portierte Pattern kriegt in dieser Spec eine Zeile "Translation:" die beschreibt, welches matrix-Substrate ersetzt.

---

## 2. Translation-Matrix (generisches Port-Pattern)

| Hermes-Primitive | matrix-Substrate |
|---|---|
| Filesystem-JSON (`jobs.json`) | Postgres-Tabelle + SQLAlchemy-Model |
| `~/.hermes/` Pfad | per-user/per-org Scope (`{org_id}/{user_id}/...` Key-Prefix) |
| `fcntl.flock()` / `msvcrt.locking()` | `SELECT ... FOR UPDATE` oder `pg_advisory_lock()` |
| `threading.Lock()` | async-lock oder stateless (NATS-queue serialisiert) |
| `croniter` 60s Tick-Thread | NATS-cron-trigger-Subject + Worker-Consumer oder Postgres `pg_cron` |
| `subprocess.run(git, ...)` (Shadow-Repo) | Workspace-Dir im go-appservice / WASM-Sandbox |
| Env-Var `MATRIX_HOME_ROOM` | DB: `user_notification_prefs.matrix_room_id` |
| `~/.hermes/output/{job_id}/` Audit-MDs | `audit_events` + SeaweedFS-Bucket `agent-outputs/` |
| `trajectory_samples.jsonl` append | `agent.traces` + `agent.spans` (bereits geplant exec-18) |
| OAuth-Token refresh inline | go-appservice `keyvault/` + Background-Refresh-Job |

---

## 3. Findings — Tier 1: Unbedingt adoptieren (hoher ROI, klarer Fit)

### 3.1 `agent/context_engine.py` — ContextEngine ABC

**Was:** Pluggable Interface für Context-Compaction mit sauberem Lifecycle.

```python
class ContextEngine(ABC):
    @property @abstractmethod
    def name(self) -> str
    last_prompt_tokens: int
    threshold_tokens: int
    compression_count: int
    threshold_percent: float = 0.75
    protect_first_n: int = 3
    # Lifecycle-Hooks
    on_session_start() / update_from_response() /
    should_compress() / compress() / on_session_end()
```

**Warum unbedingt:**
- exec-context §6.1 definiert Pre-Save/Compaction/Emergency-Schwellen (80/85/95%) aktuell **als verstreute Checks**, nicht als sauberes Interface.
- Hermes' ABC + Plugin-Pattern (`plugins/context_engine/<name>/`) ist exakt die Abstraktion die wir brauchen.
- `protect_first_n: 3` direkt portierbar — verhindert dass System-Prompt/Tool-Defs wegkomprimiert werden.

**Port-Strategie:**
- Existierenden `python-backend/agent/context_manager.py` (falls vorhanden) zu ABC-Basis umbauen
- Default-Impl `CompressorEngine` = was wir jetzt machen
- Threshold-Werte aus `main_docs/root/CONTEXT_ENGINEERING.md` übernehmen
- **Cross-Ref:** exec-context §6, exec-harness §1 Tabelle (chunk_size/fusion_weights als Harness-Parameter)

**Aufwand:** 3-5 Tage.
**Risiko:** Gering — reines Refactoring, Lifecycle stimmt mit bestehenden Triggern überein.

---

### 3.2 `agent/memory_provider.py` — MemoryProvider ABC + MemoryManager

**Was:** Abstrakte Base-Class mit 10+ Lifecycle-Hooks.

```python
class MemoryProvider(ABC):
    @abstractmethod name() / is_available() / initialize() / shutdown()
    system_prompt_block()   # statischer System-Prompt-Inject
    prefetch(query)          # Recall vor jedem Turn
    sync_turn(user, asst)    # Async Write nach jedem Turn
    get_tool_schemas()       # Tools pro Provider
    handle_tool_call()
    # Optional Hooks
    on_turn_start(turn, message, **kwargs)
    on_session_end(messages)
    on_pre_compress(messages)
    on_memory_write(action, target, content)
    on_delegation(task, result)
```

**Warum unbedingt:**
- Matrix nutzt **Hindsight UND MemPalace parallel** — keine "oder"-Entscheidung. Sie sind komplementär:
  - **Hindsight** = episodische Fact-Extraction + Graph-Links (M3/M4)
  - **MemPalace** = Conversation-Mining + Palace-Graph (cross-session Palace)
- Aktuell sind beide über `python-backend/memory_fusion/` (unified) verdrahtet — `memory_fusion/FusionMemoryEngine` ist das Haupt-Runtime, das Hindsight-Summary/Fact-Pfade mit einem MemPalace-inspirierten Verbatim-Layer zusammenführt. Vorgänger `python-backend/agent/memory/` (Hindsight-Engine-Selector) und Basis-Primitives `python-backend/memory_engine/` (KG/Vector/Episodic, Phase 6) existieren parallel, aber **ohne gemeinsames Provider-Interface über `memory_fusion` hinaus** — siehe READMEs in den drei Dirs.
- Hermes zeigt: MemoryManager erzwingt "built-in always + N externe parallel" — **exakt unser Hindsight+MemPalace+optional externe (Honcho/Mem0)-Szenario**.
- `on_pre_compress(messages) -> str` ist der Killer-Hook: verbatim-Extract VOR Compaction (genau was exec-memory §3e fordert).

**Port-Strategie:**
- Existierenden `memory_fusion/` als `MemoryManager` refactoren, der Provider-Instanzen hält:
  - `HindsightProvider` (ext. pkg, via LiteLLM)
  - `MemPalaceProvider` (Conversation-Mining)
  - Zukünftig: `PersonalKBProvider` (exec-personal-kb), `WorldModelProvider` (exec-world-model)
- Lifecycle-Hooks in `agent/graph/runner.py` bzw. `SimpleAgentLoop` einhaken
- `on_pre_compress` nutzen um exec-memory §3e Verbatim-Retain zu implementieren
- **Cross-Ref:** exec-memory §3/§5, exec-11 Phase 2, exec-15 (Provider-Toggle in Control-UI)

**Aufwand:** 5-8 Tage — größerer Refactor, aber richtungsweisend.
**Risiko:** Mittel — Bestehender Code in `memory_fusion/` muss sauber migriert werden, nicht paralleles System.

---

### 3.3 `tools/skills_guard.py` — Security-Scanner mit Trust-Policy-Matrix  **[DONE 2026-04-18 — commit `8ff8a6a`, wired `19e50c4`]**

**Was:** Regex-basierter Static-Scanner + Install-Policy-Matrix.

```python
INSTALL_POLICY = {
    "builtin":       ("allow",  "allow",   "allow"),
    "trusted":       ("allow",  "allow",   "block"),
    "community":     ("allow",  "block",   "block"),
    "agent-created": ("allow",  "allow",   "ask"),
}
# Findings: exfiltration | injection | destructive | persistence | network | obfuscation
```

**Warum unbedingt:**
- Sobald Agenten eigene Skills schreiben dürfen (exec-skills), ist das **RCE-Vektor #1**.
- Trust-Level `agent-created: "ask"` = HITL-Gate bei dangerous findings — exakt der richtige Approach.
- Kein ML, kein externer Service nötig — pure Regex, deterministisch.

**Port-Strategie (geliefert):**
- ✅ Portiert nach `python-backend/agent/security/skills_guard.py` (commit `8ff8a6a`).
- ✅ `scan_skill` akzeptiert In-Memory-Dict (`{name, files: {path: content}}`) statt `Path` — enterprise no-filesystem-assumption.
- ✅ Trust-Level-Matrix erweitert um `matrix-official` (liegt zwischen `trusted` und `community`: `(allow, ask, block)`).
- ✅ `format_scan_report()` um `pattern_id` pro Finding ergänzt (audit-trail).
- ✅ Invisible-unicode Scan läuft auf allen text-files (auch `.rst`/`.adoc`/`.org`) — Regex-Scan bleibt extension-gated (review-Finding I-1).
- ✅ Wired in `agent/skills/importer.py` (GitHub-Path two-pass + ZIP-Path) mit Dict-Contract `{success, verdict, findings}`; `app.py` maps reject → HTTP 422 (commit `19e50c4`).
- ⬜ HITL-Gate via `control-ui` Notification-Drawer — Phase 2, blockiert auf exec-12.
- **Cross-Ref:** exec-12, exec-skills (`specs/execution/exec-skills.md`, 2026-04-13 Phase-1-implementierbar), exec-17 (SKILL_BLOCKED audit events).

**Aufwand:** ~3 Tage geliefert (Port + wiring + tests). HITL-UI offen.
**Risiko:** Gering — net-new code, keine Integration-Konflikte.

---

### 3.4 `agent/error_classifier.py` + `agent/retry_utils.py` — Failover-Taxonomy  **[DONE 2026-04-18 — commit `21fb602`, wired `19e50c4`]**

**Was:** Structured `FailoverReason` Enum mit 15 Fehlerklassen + Priority-Dispatch.

```python
class FailoverReason(Enum):
    auth / auth_permanent / billing / rate_limit / overloaded /
    server_error / timeout / context_overflow / payload_too_large /
    model_not_found / format_error / thinking_signature / long_context_tier / unknown
```

**Warum unbedingt:**
- Matrix hat aktuell verstreutes String-Matching für Errors in `agent/` und `litellm-gateway/`.
- Zentrale Taxonomy ermöglicht **strategische Recovery** statt "retry-n-times":
  - `context_overflow` → compress, nicht failover
  - `billing` → rotate credential sofort, nicht retry
  - `rate_limit` → backoff THEN rotate
  - `auth_permanent` → abort (nicht retry)
- Passt perfekt zu exec-16 Multi-Provider Fallback.

**Port-Strategie (geliefert):**
- ✅ Portiert nach `python-backend/agent/resilience/error_classifier.py` (commit `21fb602`), nicht `agent/errors/` — `resilience/` hält neben classifier auch den rate_limit_tracker (§3.5) für eine kohärente Unit.
- ✅ `litellm.exceptions` als Primärquelle (matrix gateway ist LiteLLM): `AuthenticationError`, `RateLimitError`, `ContextWindowExceededError`, `BadRequestError`, `InternalServerError`, `ServiceUnavailableError`, `Timeout`, `BudgetExceededError`.
- ✅ Matrix-spezifisches Enum-Member `upstream_unavailable` für LiteLLM-"all-fallbacks-exhausted".
- ✅ `classify_error(exc) -> ClassificationResult` ist **pure** (no logging, no I/O) — tests assert caplog empty.
- ✅ Priority-Dispatch: `auth → billing → rate_limit → context_overflow → overloaded → server_error → timeout → format_error → unknown`. Auth-by-message-pattern deferred zum Ende (nach billing/rate_limit) — dokumentiert in der Module-Docstring und pinned by `test_auth_message_defers_to_billing_match`.
- ✅ `RecoveryStrategy` Enum (retry / backoff_then_retry / backoff_then_rotate / rotate_immediately / compress / fallback / abort) — stabile Schnittstelle für caller.
- ✅ Wiring (commit `19e50c4`): runner.py top-level except via `build_error_packet_with_failover` → `ErrorPacket.metadata`, refiner.py one-retry für retryable strategies, llm_node.py annotates turn-span mit `llm_error` event.
- ⬜ Voller exec-16 Provider-Fallback-Chain-Wiring — Phase 2 (classifier ist bereit, Orchestration kommt mit Credential-Pool §4.4).
- **Cross-Ref:** exec-16 §Architektur Fallback-Logik (wartet), exec-17 Error-Spans (via llm_node span.add_event erledigt).

**Aufwand:** ~2 Tage Port + 0.5 Tag Wiring geliefert.
**Risiko:** Gering.

---

### 3.5 `agent/rate_limit_tracker.py` — x-ratelimit-Header-Parser  **[DONE 2026-04-18 — commit `d5fc914`, wired `19e50c4`]**

**Was:** Parst 12-Header-Schema (OpenRouter/Nous/OpenAI-compat).

**Warum:**
- Matrix hat **kein** server-side Rate-Limit-Tracking pro Provider-Key.
- Wichtig für Cost-Tracking (exec-16) und strategisches Key-Routing (credential-pool).
- Dataclass `RateLimitBucket` mit `used/remaining/usage_pct` ist plug-n-play.

**Port-Strategie (geliefert):**
- ✅ Portiert nach `python-backend/agent/resilience/rate_limit_tracker.py` (commit `d5fc914`), zusammen mit §3.4 classifier.
- ✅ `capture_from_response(response, user_id, provider_key_id, provider)` nimmt caller-identity → buckets keyed on `(user_id, provider_key_id, window)` (vier windows: `requests`, `requests-1h`, `tokens`, `tokens-1h`).
- ✅ LiteLLM-Shape: headers werden primär aus `response._hidden_params["additional_headers"]` gelesen, Fallback `response.headers` / dict-shaped responses.
- ✅ `RateLimitRegistry` ist **in-memory** (no persistence — persistenz ist exec-17 Prometheus-Territory).
- ✅ `RateLimitBucket.to_prometheus_dict()` liefert `{labels: {user_id, provider, provider_key_id, window}, metrics: {limit, remaining, used, usage_pct, reset_seconds}}` — scrape-ready.
- ✅ Wiring (commit `19e50c4`): `llm_node.py` hat `get_rate_limit_registry()` Accessor + `reset_rate_limit_registry()` für Tests; `capture_from_response` ruft nach jedem erfolgreichen LLM-Call; span-attributes `ratelimit.requests.{limit,remaining,usage_pct}` für exec-17.
- ⬜ `provider_key_id` = `_provider_label(model)` (Phase-1-Proxy) — sobald exec-16 Credential-Pool landet: hash-of-real-key.
- **Cross-Ref:** exec-16 §Cost-Tracking, exec-17 Metrics-Exporter.

**Aufwand:** ~1 Tag geliefert.

---

### 3.6 `agent/trajectory.py` — ShareGPT JSONL Export  **[DONE 2026-04-18 — commit `e8b3858`]**

**Was:** Minimalistisches Trajectory-Logging im ShareGPT-Format, separate JSONLs für complete/failed.

**Warum:**
- Gleiches Daten-Format das **Fine-Tuning (SFT/DPO) erwartet**.
- Falls wir je eigene Modelle trainieren (Hermes-4-ähnlich), haben wir die Daten schon sauber.
- Trivial: 60 LOC.

**Port-Strategie (geliefert):**
- ✅ `python-backend/agent/trajectory/exporter.py` — pure-logic builder `build_sharegpt_conversation(session, spans)` liest über exec-18 schema (`agent.sessions` × `agent.traces` × `agent.spans`, Migration 017).
- ✅ Source-of-truth: `agent.spans.events` JSONB (unbounded bodies) — **nicht** `audit_events` (2000-char-truncation macht das für ShareGPT unbrauchbar).
- ✅ Role mapping: `system` → `system`, `prompt`/`user_message` → `human`, `completion`/`assistant_message` → `gpt`, `tool_call`/`tool_result` → `tool`. Unbekannte Events werden dropped (keine `unknown`-Leakage).
- ✅ Streaming-DB-Adapter `iter_sessions_with_spans(since_ms, user_id, db_url, conn)` via psycopg (gleiche Connection-Konvention wie `agent/sessions.py`).
- ✅ CLI: `python scripts/export_trajectories.py --out trajectories.jsonl --since 7 --user alice --dry-run --verbose`.
- **Cross-Ref:** exec-18 Traces-Schema (Migration 017 live), exec-17 Stufe 5+6 Harness-Analysis.

**Aufwand:** ~1 Tag geliefert (Pure-Logic + DB-Adapter + CLI + 18 Tests).

---

## 4. Findings — Tier 2: Adaptieren mit Anpassung (hoher Wert, CLI→Enterprise kritisch)

### 4.1 `cron/scheduler.py` + `cron/jobs.py` — Scheduled Agent-Tasks

**Was:**
- `tick()` alle 60s, checkt due jobs
- `fcntl`-basierter File-Lock gegen Double-Tick
- Multi-Platform-Delivery (`_KNOWN_DELIVERY_PLATFORMS` inkl. Matrix!)
- `SILENT_MARKER = "[SILENT]"` → Agent kann "nichts zu melden" signalisieren, Output wird trotzdem audit-geloggt
- `croniter` für Cron-Expression-Parsing
- Oneshot + Grace-Period (120s)

**Translation für Enterprise:**
- **NICHT** `fcntl` behalten — stattdessen: NATS-subject `matrix.agent.cron.tick` mit Single-Consumer, oder Postgres `pg_cron` + `SELECT ... FOR UPDATE SKIP LOCKED`.
- `~/.hermes/cron/jobs.json` → `agent.scheduled_jobs` Table (Schema: `id`, `user_id`, `skill_ids[]`, `cron_expr`, `delivery_target`, `next_run_at`, `last_output_ref`)
- Multi-Platform-Delivery: bei uns primär **Matrix + SMTP + Telegram** (nicht alle 16 Platforms nötig)
- Audit-Output via `audit_events` + SeaweedFS-Bucket `agent-outputs/`
- **Skill-Binding**: `job.skills[]` → Skills werden VOR Task-Execution geladen (matrix skill-system noch zu bauen, exec-skills).

**Warum wertvoll:**
- User: "Schick mir jeden Montag 9:00 einen Market-Summary über Matrix" — **Killer-Feature** für persönlichen Agent.
- Komplementär zu exec-19 dev-stack (periodische Ingestion-Trigger).
- `SILENT_MARKER` ist elegant — Agent darf stille Runs haben ohne User-Spam.

**Port-Strategie:**
- Neuer Service `python-backend/agent/scheduler/` als NATS-Consumer + Postgres-Query-Worker
- Matrix-Delivery via `go-appservice` Bridge (bereits vorhanden)
- Scan-Cron-Prompt Security (aus `tests/tools/test_cronjob_tools.py`) **portieren** — Prompt-Injection-Defense ist wichtig
- **Cross-Ref:** exec-19 dev-stack, exec-6 agent-chat-integration (Delivery über Bridge)

**Aufwand:** 1-2 Wochen (neuer Service + Postgres-Migration + Bridge-Wiring).
**Risiko:** Mittel — NATS-Consumer-Semantik sauber hinkriegen, sonst Double-Execution.

---

### 4.2 `tools/skill_manager_tool.py` — Skills als Markdown mit strukturiertem Layout

**Was:**
```
~/.hermes/skills/my-skill/
    ├── SKILL.md               # Trigger + Procedure
    ├── references/            # Long-form Docs für on-demand read
    ├── templates/             # Prompt-Templates
    ├── scripts/               # Executable helper-scripts
    └── assets/                # Images, data, etc.
```

Agent kann via `skill_manager_tool` CRUD-Operations ausführen (`create`, `edit`, `patch`, `delete`, `write_file`, `remove_file`) — **eigenständige Skills erstellen** basierend auf Task-Erfolgen.

**Warum wertvoll:**
- Hermes-4 Paper: Self-Learning-Loop alle 15 Tool-Calls → neue Skills.
- Matrix hat aktuell **keine** persistente Skill-Speicherung für vom Agent gelernte Patterns.
- Komplementär zu exec-memory (Memory speichert Fakten, Skills speichern Prozeduren).

**Translation für Enterprise:**
- `~/.hermes/skills/` → `agent.skills` Postgres-Tabelle (Text-Felder) + SeaweedFS-Bucket für Assets/Scripts
- Per-User + per-Org-Scoping: `{org_id}/{user_id}/skills/{skill_id}`
- Security via Skills-Guard (§3.3) VOR Commit
- Versionierung — Skills sind Artefakte, brauchen git-style History (evtl. `agent.skill_versions` Tabelle oder direkte Verbindung zu exec-18 component_configs)
- HITL-Gate: Agent-erstellte Skills im `agent-created: "ask"` Trust-Level → User approved via control-ui

**Aufwand:** 2-3 Wochen (DB-Schema + Tools + Control-UI-Approval-Flow + Security-Gate).
**Risiko:** Hoch — Skill-System ist großes Feature. **`specs/execution/exec-skills.md` existiert seit 2026-04-13 (Phase-1 implementierbar)**; Skill-Manager-Tool (§4.2) sollte auf dessen DB-Schema `agent.agent_skills` aufsetzen, nicht auf Filesystem.

---

### 4.3 `tools/checkpoint_manager.py` — Shadow-Git-Repos für File-Mutation-Safety

**Was:** Vor jedem file-mutating Tool-Call → Snapshot in `~/.hermes/checkpoints/{sha256(abs_dir)[:16]}/` (shadow git-repo mit `GIT_DIR + GIT_WORK_TREE`). Rollback zu beliebigem Checkpoint.

**Warum interessant:**
- Nutzt git als POC-Storage — robust, clever, kein Re-Invent.
- Agenten die Code schreiben (`write_file`, `patch`) bekommen transparente Undo-Funktion.

**Translation für Enterprise — KRITISCHER PUNKT:**
- **Hermes' Modell funktioniert weil Agent auf User's Filesystem arbeitet.** Bei matrix Enterprise: Agent arbeitet in **Workspaces** (Per-Session-Dirs) oder in WASM-Sandbox (exec-12).
- Wenn `go-appservice` Workspace-Dirs managed (pro Session): Shadow-git direkt anwendbar, aber pro Session-Dir.
- Wenn WASM-Sandbox (exec-12): Checkpoint = VM-Snapshot via Wasmtime-API, nicht git.
- **Überschneidung mit exec-12 Sandbox-Security** — MUSS mit exec-12 Owner abgestimmt werden, welches Modell gewinnt.

**Empfehlung:**
- Nicht jetzt portieren. **Warten auf exec-12-Entscheidung** (WASM vs E2B vs Workspace-Dirs).
- Falls Workspace-Dir-Modell gewinnt: Shadow-Git adoptieren (1-2 Wochen).
- Falls WASM-Modell gewinnt: Pattern "Auto-Checkpoint vor File-Mutation" adoptieren, Implementierung anders.

**Cross-Ref:** exec-12 §Sandbox-Security.

---

### 4.4 `agent/credential_pool.py` — Persistent Multi-Credential-Pool

**Was:** Multi-Account-Pool pro Provider mit Strategies (`fill_first`, round-robin, least-recently-used), Status-Tracking (`ok`/`exhausted`), OAuth-Refresh-Integration.

**Warum interessant:**
- User mit mehreren OpenAI/Anthropic-Accounts kann alle nutzen, auto-failover bei Rate-Limit.
- Pairt mit `rate_limit_tracker.py` (§3.5) und `error_classifier.py` (§3.4).

**Translation für Enterprise:**
- `~/.hermes/credentials.json` → `agent.credentials` Postgres-Tabelle (encrypted via AESGCMVault — **Wiederverwendung** von `go-appservice/internal/keyvault`)
- Per-User + per-Org-Pool (nicht global single-pool)
- OAuth-Refresh via Background-Worker, nicht inline
- Integration mit exec-16 Provider-Fallback

**Aufwand:** 1 Woche (Port + Encryption-Integration).
**Risiko:** Mittel — Encryption-at-rest muss sauber mit bestehendem KeyVault integrieren.

---

### 4.5 `agent/prompt_caching.py` — Anthropic `cache_control` system_and_3  **[DONE 2026-04-18 — in `llm_node.py`, fixed `9fe9a58`]**

**Was:** 4 `cache_control` breakpoints (Anthropic max): System + letzte 3 non-system messages, rolling window. Pure Functions, keine Class-State.

**Warum:**
- exec-context §1.2 beschreibt das als "Umsetzungsregel", aber kein konkreter Code.
- Hermes' Impl ist pragmatisch und testet `native_anthropic` vs OpenAI-shape.

**Stand (geliefert):**
- ✅ Implementiert in `python-backend/agent/graph/nodes/llm_node.py`:
  - `_model_may_use_ephemeral_cache(model)` Gate auf `"claude"` / `"anthropic"` (trifft direkte Claude-IDs UND `openrouter/anthropic/...`).
  - `_mark_cache_control(msg)` Helper setzt ephemeral-cache auf alle content-parts.
  - `_apply_anthropic_caching(messages)` — fix in `9fe9a58`: System-Prompt (`messages[0]` bei role=="system") bekommt **unconditional** das cache_control, danach rolling window über die letzten 3 NON-system messages. Vier Breakpoints wie in §4.5 spezifiziert.
- ⬜ Explizite 5m / 1h TTL-Option — aktuell Default 5m (litellm/Anthropic Standard); Exposition eines `ttl`-params wäre eine Erweiterung falls wir lange Agent-Sessions mit 1h-Cache-Re-use wollen.
- **Cross-Ref:** exec-context §5/§8 (Cache-Hit-Rate-Metrik).

**Aufwand:** ~1 Tag (ursprünglicher Port war bereits ~80% — nachträglicher System-Prompt-Breakpoint-Fix in ~30 Min).

---

## 5. Findings — Tier 3: Mit Vorsicht evaluieren (Niche, Überschneidung, Aufwand-vs-Nutzen)

### 5.1 `gateway/platforms/api_server.py` — OpenAI-kompatibler HTTP-Endpoint

**Was:** aiohttp-Server mit `/v1/chat/completions` + `/v1/responses` + `/v1/runs/{id}/events` (SSE) + `/v1/models`.

**Resultat:** Hermes kann mit **Open WebUI, LobeChat, LibreChat, AnythingLLM, NextChat, ChatBox** als Drop-In verwendet werden.

**Für matrix relevant?**
- Wir haben `control-ui` (eigene UI) und Agent-Chat (Matrix-Bridge). Brauchen wir einen OpenAI-kompatiblen Fremd-UI-Endpoint?
- **Vielleicht** für Power-User die bestehende OpenAI-SDK-Apps weiter nutzen wollen.
- Niedrige Priorität bis v2.0.

**Nicht jetzt adoptieren.** Notieren für später.

---

### 5.2 `acp_adapter/` — Agent Communication Protocol (Agent-to-Agent)

**Was:** Separates Modul für A2A-Kommunikation. `auth.py`, `permissions.py`, `events.py`, `session.py`, `tools.py`.

**Relevant?**
- Matrix plant Multi-Agent (exec-10). ACP wäre eine Option.
- Aber: A2A-Standards sind noch unreif (ACP, LangChain A2A, Google A2A — alle "proposed").
- **Eher selbst in NATS-Subject-Convention bauen** — matrix hat NATS sowieso.

**Nicht adoptieren.** NATS-basiertes A2A ist näher an unserer Stack, siehe §9 Hybrid-Vorschlag.

---

### 5.3 `plugins/memory/holographic/` — Holographic Reduced Representations (HRR)

**Was:** Phasen-Vektor-Encoding (Plate 1995, Gayler 2004) — mathematische Basis für "vector symbolic architecture". Bind/Unbind/Bundle via circular convolution.

**Neuheit:** Deterministisches SHA-256-Atom-Encoding (cross-platform reproduzierbar).

**Für matrix?**
- Fundamentale Forschungs-Technik, sehr interessant als alternative Representation für KG-Nodes.
- Aber: Überschneidet mit `exec-world-model` / KG-Architektur (KuzuDB/FalkorDB-Entscheidung).
- **Experimentell — nicht jetzt**. Notieren für KG-Forschung.

**Nicht adoptieren.** Notieren unter "interessante Ideen für `exec-world-model`".

---

### 5.4 `agent/smart_model_routing.py` — Keyword-based Cheap/Strong-Routing

**Was:** 37 Keywords triggern "strong model" (`debug`, `implement`, `analyze`, `architecture`, `plan`, etc.), sonst cheap.

**Für matrix relevant?**
- Complementary zu LiteLLM-Fallback (exec-16).
- Aber: Wir haben bereits `control-ui` mit User-gewähltem Model pro Rolle → `smart_model_routing` würde das **übersteuern**.
- Evtl. als optional-Layer "Auto-Model-Downgrade" wenn User "auto" gewählt hat.

**Nicht jetzt adoptieren.** Zuerst Cost-Tracking in exec-16 fertig, dann überlegen ob Auto-Routing dazu.

---

### 5.5 `tools/process_registry.py` — In-Memory Background-Process-Registry

**Was:** `spawn / poll / wait / kill` für Background-Tools mit Output-Buffering (200KB rolling), JSON-Checkpoint-File für Crash-Recovery.

**Für matrix relevant?**
- Agent darf Long-Running-Commands starten (z.B. `pytest`, `docker build`, `ingestion-full-rebuild`) ohne zu blockieren.
- Aber: `subprocess`-spawn passt nicht ins Enterprise-Modell — stattdessen NATS-Job-Queue + Worker.

**Adaptieren:** Pattern ja, Implementierung nein. Bei matrix:
- "Spawn" = NATS-publish auf `matrix.agent.long_task.new`
- "Poll" = DB-Query auf `agent.long_tasks` Tabelle
- "Wait" = Subscribe auf `matrix.agent.long_task.{task_id}.done`

---

### 5.6 `batch_runner.py` — Multiprocessing-Pool für Parallel-Multi-Prompt

**Was:** Python `multiprocessing.Pool` für Eval-Runs über viele Prompts parallel.

**Für matrix relevant?**
- Eval/Benchmark-Runs (exec-harness §1 AutoResearch-Pattern) — ja.
- Aber: `multiprocessing` ist single-host. Besser: NATS-Worker-Pool (horizontal).

**Adaptieren:** Pattern ja. Der Checkpoint-Resumption-Pattern aus `test_batch_runner_checkpoint.py` ist wertvoll — Resume-Able Eval-Runs nach Crash.

---

## 6. Findings — Tier 4: Kleine Gems (trivial zu übernehmen)

### 6.1 `agent/manual_compression_feedback.py` — UX für manuelle Compression
- 50 LOC, zeigt dem User "Compressed: X → Y messages, ~N → ~M tokens".
- Note-Warnung falls fewer messages aber mehr tokens (dichter Summary).
- **Port:** 1 Stunde. In `control-ui` Compression-Button einbauen.

### 6.2 `agent/title_generator.py` — Auto-Chat-Title
- LLM generiert 5-Wort-Title für Chat-Session.
- **Port:** 2 Stunden. In `control-ui` Chat-Listen für UX.

### 6.3 `agent/insights.py` — Usage-Report (Tokens, Cost, Tools, Platforms)
- Analog zu Claude Code's `/insights` Command.
- Aggregiert über `state.sqlite`-Sessions.
- **Für matrix:** genau das was exec-17 OpenObserve-Dashboards machen könnten. Pattern-Referenz, nicht direkter Port.

### 6.4 `tests/tools/test_cronjob_tools.py` → `scan_cron_prompt`
- Prompt-Injection-Defense für Cron-Task-Prompts.
- **Port mit §4.1 Cron-Scheduler.** Pflicht.

### 6.5 `agent/prompt_builder.py` + `agent/subdirectory_hints.py`
- System-Prompt-Assembly mit dynamischen Hints (aktuelles Working-Dir, letzte Files, etc.).
- **Referenz** für exec-context §5 Prompt-Reihenfolge. Nicht direkter Port, aber Inspiration.

---

## 7. Was definitiv NICHT übernehmen

- `hermes_state.py` (SQLite) — wir haben Postgres.
- `hermes_cli/` + `cli.py` — Hermes ist interaktiver CLI, matrix ist API-first.
- `flake.nix` — wir nutzen `mise` + podman, nicht Nix.
- `docker/` — wir haben eigenes podman-compose setup.
- `environments/agentic_opd_env.py` + `hermes_swe_env/` — Benchmark-Environments, für matrix nicht relevant.
- `datagen-config-examples/` — RL-Training-Daten-Generation, matrix ist nicht Research-Lab.
- `mini_swe_runner.py` — Single-Purpose Benchmark-Runner.
- Die 16 Gateway-Platforms einzeln (WeChat, QQ, DingTalk, WhatsApp, Signal, BlueBubbles, HomeAssistant, Feishu) — matrix braucht primär Matrix + Telegram + evtl. Email. Alles andere ist CLI-Bloat den wir nicht wollen.

---

## 8. Architektur-Matching — was überschneidet sich mit welcher bestehenden Exec

| Hermes-Modul | Überschneidet mit | Relation |
|---|---|---|
| `agent/context_engine.py` | **exec-context** §6 | **Direkter Port als ABC** — exec-context bekommt das Interface |
| `agent/memory_provider.py` + Manager | **exec-memory** §3, **exec-11**, **exec-15** | **Direkter Port** — ersetzt verdrahtetes Fusion-Pattern |
| `tools/skills_guard.py` | **exec-12** (Sandbox), **exec-skills** (`specs/execution/exec-skills.md`) | Ergänzt — Static vs Runtime |
| `cron/scheduler.py` | **exec-19** (dev-stack), **exec-6** (agent-chat) | Neuer Service, NATS-basiert |
| `tools/checkpoint_manager.py` | **exec-12** (Sandbox-Security) | Wartet auf exec-12-Entscheidung |
| `agent/error_classifier.py` | **exec-16** (LLM-Gateway) | Ergänzt Fallback-Logik |
| `agent/credential_pool.py` | **exec-16**, `go-appservice/keyvault` | Multi-Key-Rotation oben drauf |
| `agent/rate_limit_tracker.py` | **exec-16**, **exec-17** (Observability) | Neues Signal für OpenObserve |
| `agent/prompt_caching.py` | **exec-context** §1.2 | Konkreter Code für Abstrakt-Regel |
| `agent/trajectory.py` | **exec-18** (Traces), **exec-17** | Export-View statt separate File |
| `tools/skill_manager_tool.py` | **exec-skills** (muss erst geschrieben werden) | Blockiert auf Skill-Spec |
| `gateway/platforms/` | **exec-6** agent-chat, Matrix-Bridge | Matrix-Platform als Referenz |
| `acp_adapter/` | **exec-10** multi-agent | Nicht direkt — NATS-A2A bauen |
| `plugins/memory/holographic/` | **exec-world-model** (KG) | Forschungs-Referenz, nicht jetzt |

---

## 9. Die große Architekturfrage: Graph vs Loop vs Hybrid

### 9.1 Was wir haben: LangGraph (`python-backend/agent/graph/`)
- State-Machine mit deterministischen Edges
- Gut für: Multi-Step-Workflows mit strikten Zuständen (Ingestion-Pipeline, Research-Chain)
- Schlecht für: simples Chat-Turn-Loop (Over-Engineering)
- Exec-Reference: **exec-10** multi-agent, exec-18 component_configs

### 9.2 Was Hermes hat: Agno-Style Loop
- `environments/agent_loop.py` = linearer multi-turn Loop
- `while not done: llm_call → parse → tool_dispatch → maybe_compress → loop`
- Pluggable via ABCs (ContextEngine, MemoryProvider, ToolRegistry)
- Gut für: Chat, Code-Agent, Research-Agent
- Schlecht für: strikte Workflows mit expliziten States

### 9.3 Was Agno (das Framework) macht
- Team-Abstraktion: mehrere Agenten kommunizieren via Message-Bus/Pub-Sub
- Emergent Coordination via Roles + Instructions
- Gut für: flexible Multi-Agent, emergente Zusammenarbeit
- Schlecht für: Compliance-kritische Flows wo jeder State beweisbar sein muss

### 9.4 Ehrliche Empfehlung für matrix: **HYBRID**

**Nicht** Graph komplett ersetzen. **Nicht** nur Loop. Stattdessen:

```
┌──────────────────────────────────────────────────────────────┐
│  Entry-Point: agent-runner (dispatcher)                       │
│                                                                │
│  ├─ task-mode/complexity:                                      │
│  │                                                             │
│  ├─► SimpleAgentLoop (ReAct, Hermes/Agno-Style)                │
│  │     Use-Cases: Chat, Single-Task, Tool-Use-Chain            │
│  │     Pluggable: ContextEngine, MemoryProvider, ToolRegistry  │
│  │     ~200 LOC, token-effizient (2-3k tokens/task)            │
│  │                                                             │
│  ├─► Plan-and-Execute Loop                                     │
│  │     Use-Cases: Long-horizon Reasoning, Multi-Step Analyse   │
│  │     Planner-Call upfront → Executor-Loop                    │
│  │     +92% accuracy vs ReAct laut LangChain-2026-Benchmark    │
│  │                                                             │
│  ├─► LangGraph-Pipelines (bestehend)                           │
│  │     Use-Cases: Ingestion, Research, Multi-Step mit States   │
│  │     Deterministische Edges, Checkpointing, HITL-Gates       │
│  │     DAG-Parallelism (LLMCompiler-Pattern: ~3.6× Speedup)    │
│  │                                                             │
│  └─► Multi-Agent-Team (NATS-basiert)                           │
│        Use-Cases: parallele Agenten mit Rollen                 │
│        Pattern: Supervisor + Hierarchical Delegation           │
│        NATS-Subjects als Message-Bus, nicht ACP                │
│        ~exec-10 richtung                                       │
└──────────────────────────────────────────────────────────────┘
         ▲
         │  (outer optimization loop — unabhängig vom inneren Pfad)
         │
┌────────┴──────────────────────────────────────────────────────┐
│  Meta-Harness (exec-harness §1 Stufe B)                        │
│  Coding-Agent liest Traces+Scores → schlägt Harness-Patches    │
│  vor → Evaluator scored → Pareto-Frontier                      │
│  arxiv 2603.28052 — Methodologie, nicht Architektur            │
└────────────────────────────────────────────────────────────────┘
```

**Vorteile des Hybrid:**
1. **SimpleAgentLoop** deckt 60% der Agent-Flows (Chat, Tool-Use) ohne Graph-Overhead ab
2. **Plan-and-Execute** für 10% long-horizon Tasks (empirisch +92% accuracy)
3. **LangGraph** bleibt für 20% kritische Workflows wo States wichtig sind
4. **Multi-Agent-Team** für 10% emergenten Kollaborationen
5. Alle vier Pfade teilen sich die **gleichen Plugins**: `ContextEngine`, `MemoryProvider`, `ToolRegistry` — kein Vendor-Lock auf ein Pattern
6. **Meta-Harness** ist orthogonal — optimiert JEDEN der Pfade, ohne den Pfad selbst zu sein

**Anti-Patterns die vermieden werden:**
- ❌ "Alles in Graph" — produziert Boilerplate für einfache Chats
- ❌ "Alles in Loop" — verliert Compliance-Prüfbarkeit bei komplexen Flows
- ❌ "Drei parallele, nicht-geteilte Stacks" — verdreifacht Test-Burden
- ❌ "Hermes 1:1 übernehmen" — CLI-Assumptions brechen Enterprise
- ❌ "Framework-Lock auf Agno oder LangGraph" — beide haben Schwächen

**Phase-Plan:**
1. **Phase 0** (jetzt): ContextEngine- + MemoryProvider-ABCs portieren (§3.1, §3.2) — beide Patterns teilen dieselben Engines. **Das ist der Enabler für Hybrid.**
2. **Phase 1**: `SimpleAgentLoop` als neuer Pfad für Chat/Simple-Tool-Use. Bestehende LangGraph-Pipelines bleiben unverändert.
3. **Phase 2**: Benchmarks — welche Tasks gehen besser durch welchen Pfad? (exec-harness §1 AutoResearch-Pattern nutzen)
4. **Phase 3**: Multi-Agent-NATS-Pattern bauen (exec-10).
5. **Phase 4**: Routing-Layer — Agent-Runner wählt Pfad basierend auf Task-Metadata.

**Evaluations-Kriterien pro Use-Case:**
- Latenz (Turn-to-Turn)
- Code-Lesbarkeit (LOC pro Flow)
- Debuggability (Trace-Qualität)
- Failure-Recovery (was passiert bei Crash mid-Flow)
- Compliance-Audit-Trail
- Developer-Velocity (wie schnell neue Skills/Tools einbauen)

### 9.5 Ehrliche Anti-Pattern-Warnungen

- **"Wir brauchen beide weil beide cool sind"** ist kein Argument. Hybrid nur wenn klarer Mehrwert pro Pfad.
- **"Ganz ohne LangGraph"** klingt aufgeräumt, verliert aber die deterministische Ingestion-Pipeline die wir schon haben.
- **"Schnell mal Agno dran"** — Agno das Framework zu adoptieren ist 3-6 Wochen Refactor. Wir bauen stattdessen einen **selbst-kontrollierten SimpleAgentLoop** der Agno-Patterns nutzt ohne Framework-Lock.
- **Hermes als Ganzes forken** = Maintenance-Hell. Hermes hat 184k LOC, 60% davon nicht-matrix-relevant.
- **"Meta-Harness statt LangGraph"** — Kategorienfehler. Meta-Harness ist kein Pfad im Flowchart oben, sondern der Mechanismus der die Pfade TUNT. Siehe §9.7.

### 9.6 Empirische Rückendeckung 2026 — Web-Research vom 2026-04-18

Die Hybrid-Empfehlung ist **nicht nur Bauchgefühl** — sie ist gestützt durch aktuelle Benchmarks und Surveys:

| Erkenntnis | Quelle | Implikation für matrix |
|---|---|---|
| **Plan-and-Execute +92% Accuracy** auf long-horizon Tasks vs ReAct | LangChain/Redis/Vellum 2026 Benchmarks, [dasroot.net 2026-04](https://dasroot.net/posts/2026/04/agent-architectures-react-plan-execute-graph-agents/) | §9.4 Diagramm hat Plan-Execute als eigenen Pfad |
| **Shift weg von ReAct** zu hierarchical/search-based Systems | arxiv [2601.12560](https://arxiv.org/html/2601.12560v1) (Jan 2026 Survey) | "Myopic single-loop" alleine ist nicht mehr state-of-art |
| **Graph-DAG ~3.6× Speedup** via Parallelism (LLMCompiler) | Redis/Vellum 2026, [aiagentsquare.com](https://aiagentsquare.com/blog/ai-agent-benchmarks-2026.html) | LangGraph-Retention gerechtfertigt für parallelisierbare Flows |
| **AutoGen GroupChat ~20+ LLM-Calls/Task** — teurer | [pooya.blog 2026-Bench](https://pooya.blog/blog/ai-agents-frameworks-local-llm-2026/) | NATS-basiertes Multi-Agent statt AutoGen |
| **LangGraph = höchste Production-Readiness** (LangSmith, Checkpointing, MCP-Tool-Nodes-first-class) | [gurusup.com 2026](https://gurusup.com/blog/best-multi-agent-frameworks-2026) | LangGraph als stabile Basis für stateful Workflows bestätigt |
| **CrewAI 40% schneller time-to-production**, aber geringere Prod-Maturity | [pooya.blog](https://pooya.blog/blog/ai-agents-frameworks-local-llm-2026/) | Nicht adoptieren — time-to-prototype ≠ time-to-stable-production |
| **SWE-Bench Pro nur 17-23%** vs SWE-Bench Verified 80-94% | [Scale AI SWE-Bench Pro PDF](https://static.scale.com/uploads/654197dc94d34f66c0f5184e/SWEAP_Eval_Scale%20(9).pdf) | Enterprise-Long-Horizon-Tasks sind ungelöst — Raum für Meta-Harness-Optimierung |
| **Meta-Harness** schlägt Hand-Engineered auf TerminalBench-2, +7.7pt Context-Mgmt, +4.7pt IMO-Math | arxiv [2603.28052](https://arxiv.org/abs/2603.28052) (Stanford 2026) | Unser exec-harness §1 Stufe B adoptiert die Methodologie — on track |
| **3-Layer-Konsens**: Prompt → Context → Harness Engineering | Industry-Konsens 2026 (multiple sources) | exec-context + exec-harness + system-prompts sind die 3 matrix-Layer |

**Kern-Konsens 2026:** Nicht EINE Architektur wählen. Graph-Orchestrierung mit austauschbaren Loop-Engines + outer Meta-Harness-Optimization ist der empirisch robusteste Pfad. **Das ist genau was §9.4 beschreibt** — die Empirie bestätigt den Entwurf.

**Production-Patterns die sich 2026 etabliert haben** (aus Industry-Surveys, sollte exec-10 multi-agent benennen):
1. **Pipeline** — sequenzielle Stages (unsere Ingestion-Pipeline)
2. **Fan-out / Fan-in** — parallele Sub-Tasks, Ergebnis-Aggregation
3. **Expert Pool** — spezialisierte Agenten, Dispatcher wählt Experten
4. **Producer-Reviewer** — einer produziert, zweiter reviewed (→ exec-harness Evaluator-Pattern)
5. **Supervisor** — zentraler Koordinator, delegiert an Sub-Agenten
6. **Hierarchical Delegation** — Supervisor hat Sub-Supervisors (Tree-Struktur)

Matrix sollte diese Pattern explizit benennen können (exec-10 Multi-Agent-Spec), nicht Ad-hoc-Kollaboration bauen.

### 9.7 Meta-Harness — Methodologie, nicht Architektur-Blueprint

**Wichtige Klarstellung** (aus Deep-Dive-Diskussion 2026-04-18):

Meta-Harness ist **kein alternativer Pfad im §9.4 Flowchart**. Es ist der **Outer-Optimization-Loop**, der **jede** der vier Pfade (SimpleAgentLoop, Plan-Execute, LangGraph, Multi-Agent) verbessert, ohne selbst einer dieser Pfade zu sein.

```
  Kategorie:          Was es ist:                         Beispiel:
  ─────────────────────────────────────────────────────────────────────
  Inner Harness       Architektur des Agenten             LangGraph, ReAct
                      (Flow, State, Loops)                Plan-Execute, Multi-Agent

  Outer Harness-      Methodologie zur Verbesserung       Meta-Harness
  Optimization        des Inner Harness                   (Stanford 2603.28052)
                      (Code-Editing-Loop über Traces)     Auto-GPT-Selfimprove
```

**Matrix-Status (Stand 2026-04-18):**
- `exec-harness.md §1 Stufe B` adoptiert Meta-Harness **als Methodologie** — Coding-Agent liest `agent.traces` + `agent.spans` (exec-18), schlägt Harness-Config-Patches vor, Pareto-Frontier tracked Candidates.
- Wir bauen unseren Harness **nicht AS Meta-Harness** (d.h. wir machen nicht den inneren Flow-Mechanismus zu einem Meta-Harness-artigen System). Der innere Flow bleibt LangGraph + SimpleAgentLoop.
- Meta-Harness "frisst" unseren Harness-Code, verbessert ihn, gibt verbesserten Harness zurück. Analogie: **Compiler-Optimizer ist kein Programm, das ein Programm AUSFÜHRT, sondern ein Programm, das ein Programm VERBESSERT.**

**Warum das wichtig ist:**
- "Meta-Harness als Architektur" würde bedeuten: jede User-Anfrage durchläuft einen Coding-Agent-Proposer — Latenz + Kosten explodieren. **Falsch für Runtime.**
- "Meta-Harness als Methodologie" bedeutet: einmal pro Woche (oder on-demand) läuft ein Offline-Optimierungs-Job, der Harness-Parameter tunt. **Korrekt.**

**Implikation:** Bestehendes `python-backend/agent/harness/` (exec-17 Stufe 5+6) ist der richtige Platz für Meta-Harness-Integration. Nicht neuer Runtime-Path im agent-runner.

---

## 10. Konkreter Port-Roadmap (Stand 2026-04-18 — Sprints 1-3 abgearbeitet)

### Sprint 1 — Foundation ✅ DONE
- [x] **§3.1 ContextEngine ABC** — `context/context_engine.py` (commit `7e1d387`). DefaultContextEngine mit 80/85/95-Thresholds, Peer-Service-Pattern (SOTA 2026 hermes + OpenClaw convention).
- [x] **§3.2 MemoryProvider ABC + MemoryManager** — `memory_fusion/memory_provider.py` (commit `7e1d387`). FusionProvider-Adapter, Error-Isolation, `auto_fusion_provider()` factory.
- [x] **§3.3 Skills-Guard** — `agent/security/skills_guard.py` (commit `8ff8a6a`), wired in `agent/skills/importer.py` GitHub+ZIP two-pass (commit `19e50c4`). REST 422-reject in `agent/app.py`.
- [x] **§3.4 Error-Classifier** — `agent/resilience/error_classifier.py` (commit `21fb602`), wired via `build_error_packet_with_failover` in runner.py top-level except + refiner one-retry + llm_node span-event (commit `19e50c4`).

### Sprint 2 — Observability & Resilience ✅ DONE
- [x] **§3.5 Rate-Limit-Tracker** — `agent/resilience/rate_limit_tracker.py` (commit `d5fc914`), wired via `get_rate_limit_registry()` singleton + `capture_from_response()` after successful LLM calls (commit `19e50c4`). Span-attributes surface ratelimit.requests.{limit,remaining,usage_pct}.
- [x] **§3.6 Trajectory-Export** — `agent/trajectory/exporter.py` + `scripts/export_trajectories.py` (commit `e8b3858`). Source-of-truth: `agent.spans.events` JSONB (exec-18 Migration 017), NICHT audit_events (2000-char truncated).
- [x] **§4.5 Prompt-Caching** — in `llm_node.py` (fix commit `9fe9a58`): System-prompt-breakpoint unconditional + last-3 non-system rolling window.
- [ ] **§6.1-6.2 UX-Gems** — manual-compression-feedback + title-generator (control-ui, 1-2h each, backlog)

### Sprint 3 — Credentials ✅ PARTIALLY DONE
- [x] **§4.4 Credential-Pool** — `agent/resilience/credential_pool.py` (commit `38b9b64`). ABC + SingleKeyCredentialPool wrapping `get_user_api_key`. `apply_recovery()` dispatcher wires error_classifier → pool (rate_limit → 1h cooldown, billing → 24h, auth → mark_auth_failed, overloaded/server_error → 5min). Multi-key-per-user bleibt der DB-Schema-Erweiterung überlassen.
- [ ] **§4.1 Cron-Scheduler** — Blocker-Revision 2026-04-18: exec-19 ist archiviert (devstack-consolidation abgeschlossen). Realer Status: NATS läuft bereits (docker-compose.yml :50). Benötigt: Alembic Migration für `agent.scheduled_jobs` Table + Go-Implementation in go-appservice/internal/scheduler/ (Postgres `FOR UPDATE SKIP LOCKED` + NATS-publish → Python-Subscriber). **Nicht blockiert** — kann starten sobald priorisiert. Skill-Binding wartet weiterhin auf exec-skills DB-flow.

### Sprint 4 — Architektur-Entscheidung (Backlog)
- [ ] **§9 Hybrid-Loop-Pfad** — `SimpleAgentLoop` Prototyp (nicht production)
- [ ] Benchmarks gegen LangGraph auf 5 Task-Typen — **nutzt den gemeinsamen Evaluator aus [`exec-harness.md §4d`](./exec-harness.md#4d-evoskill-evaluator-stage-integration--expliziter-adoption-plan)** mit neuem `hermes_pattern`-Scorer
- [ ] Entscheidung: Adoption ja/nein, welche Use-Cases via Loop

### Weitere Cleanups (parallel gelandet)
- [x] `agent/memory/` legacy-selector archiviert → `archive/legacy-agent-memory/` (commit `1338b7d`). Alle 10 call-sites migriert zu `memory_fusion/` (commit `aefce78`).
- [x] `python-backend/memory/` toter REST-Stub archiviert → `archive/legacy-memory-service/` (commit `72044df`). Nie aktiviert laut docker-compose.yml + keine Python-Importer.
- [x] 3 pre-existing test failures gefixt (policy.py grounded_derived → L0, kg_store guard loosened für SELECT-literals, kg_store INSERT-guard-contract als Test geschrieben).
- [x] Memory-dirs READMEs: `memory_fusion/` (primary runtime + ABC), `context/` (ContextEngine + peer-service-pattern), `memory_engine/` (3-memory-types Taxonomie), `archive/` (retirement trail).

### Später (blockiert auf andere Execs)
- **§4.2 Skill-Manager-Tool** — `specs/execution/exec-skills.md` existiert (2026-04-13), aber `agent.agent_skills` DB-flow noch offen
- **§4.3 Checkpoint-Manager** — wartet auf exec-12 Sandbox-Entscheidung (WASM vs Workspace-Dir)
- **§5.x Tier-3** — niedrige Priorität, später evaluieren

---

## 11. Offene Fragen (für Deep-Dive-Session)

1. **Memory-Provider-Integration:** Soll MemoryManager beide (Hindsight + MemPalace) **parallel bei jedem Turn** aufrufen, oder sequenziell mit Ranking-Merge? Heutiges `memory_fusion/` macht Sequential — passt das ins Hermes-Pattern?

2. **Skills-Guard vs WASM-Sandbox:** Wenn exec-12 WASM-Sandbox wählt, brauchen wir Skills-Guard noch? Antwort vermutlich ja (Defense-in-Depth), aber wie viel Aufwand rechtfertigt das?

3. **Cron-Scheduler:** Ist Postgres `pg_cron` Extension akzeptabel, oder reines NATS-basiertes Scheduling bevorzugt? Hängt mit exec-19 Infra-Entscheidungen zusammen.

4. **SimpleAgentLoop:** Wirklich bauen, oder doch komplett auf LangGraph bleiben? Benchmarks müssten laufen bevor entschieden — aber wer macht die Benchmarks?

5. **Trajectory-Export:** ShareGPT-Format ist fine-tuning-standard. Haben wir mittelfristig Pläne für eigenes Fine-Tuning? Falls nein → nur als Debug-Tool, nicht als Data-Pipeline.

6. **Skill-System (exec-skills):** Existiert das als Spec bereits? Falls nein → erst schreiben, bevor `skill_manager_tool` portiert wird.

7. **Credential-Pool:** Per-User oder per-Org? Multi-Tenant-Implikationen.

---

## 12. Anhang — Deep-Dive-Kommandos für weitere Exploration

### Via gitnexus (bereits genutzt)
```
mcp__gitnexus__cypher({query:"MATCH (f:File) WHERE f.filePath STARTS WITH '<prefix>/' RETURN f.filePath", repo:"hermes-agent"})
mcp__gitnexus__query({query:"<concept>", repo:"hermes-agent", goal:"..."})
mcp__gitnexus__context({name:"<symbol>", repo:"hermes-agent"})
```

### Via CLI-Tools
```bash
# Quick structure scan
tokei /home/lipfi2/code/matrix/_ref/hermes-agent --exclude tests --exclude 'skills/*' --exclude 'optional-skills/*'

# Symbol search across codebase
rg "class.*Provider|class.*Engine" /home/lipfi2/code/matrix/_ref/hermes-agent/agent/ -t py

# Flow-Diagramm generator (onefetch zeigt repo-Stats)
onefetch /home/lipfi2/code/matrix/_ref/hermes-agent
```

### Wichtige Files für Deep-Dive-Session
- `run_agent.py` (AIAgent-Klasse, Main-Loop-Entry)
- `environments/agent_loop.py` (80 LOC, HermesAgentLoop)
- `agent/context_engine.py` (ABC)
- `agent/memory_provider.py` (ABC + MemoryManager)
- `tools/skills_guard.py` (Security-Matrix)
- `cron/scheduler.py` + `cron/jobs.py`
- `gateway/platforms/api_server.py` (OpenAI-compat HTTP, für später)

---

## 13. Referenzen

### 13.1 Hermes-Agent Repo + Paper

- **Hermes-Agent Repo (NousResearch):** https://github.com/NousResearch/hermes-agent
- **Hermes-4 Technical Report** (Teknium et al., Aug 2025): https://arxiv.org/abs/2508.15204
- **Hermes-Agent Docs:** https://hermes-agent.nousresearch.com/docs/
- **OpenClaw Alternative Review** (What Is Hermes Agent?): https://mindstudio.com/ (Mar 2026)
- Matrix gitnexus-Index: `_ref/hermes-agent/` — 47,734 nodes, 25,633 Embeddings, 1,707 Files

### 13.2 Architektur-Vergleich Papers (primäre Quellen für §9)

- **Meta-Harness: End-to-End Optimization of Model Harnesses** (Lee, Nair, Zhang, Lee, Khattab, Finn — Stanford IRIS Lab, 2026): https://arxiv.org/abs/2603.28052
  - HTML: https://arxiv.org/html/2603.28052v1
  - Artifact (GitHub): https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact
  - Notes-Review (Hugo Cisneros): https://hugocisneros.com/notes/leemetaharnessendtoend2026/
  - Substack: https://arxiviq.substack.com/p/meta-harness-end-to-end-optimization
- **The Landscape of Emerging AI Agent Architectures for Reasoning, Planning, and Tool Calling: A Survey** (Jul 2025): https://arxiv.org/abs/2404.11584
- **AI Agent Systems: Architectures, Applications, and Evaluation** (Jan 2026 Survey): https://arxiv.org/html/2601.01743v1
- **Agentic AI: Architectures, Taxonomies, and Evaluation of LLM Agents** (Jan 2026): https://arxiv.org/html/2601.12560v1
  - Kern-Zitat: "Reasoning architectures have moved from myopic single loop solvers such as ReAct to hierarchical and search based systems."
- **Evaluation and Benchmarking of LLM Agents: A Survey** (Jul 2025): https://arxiv.org/html/2507.21504v1
- **A Comprehensive Empirical Evaluation of Agent Frameworks on Code-centric SE Tasks** (2026): https://arxiv.org/html/2511.00872v1
- **awesome-ai-agent-papers (VoltAgent, 2026 curated):** https://github.com/VoltAgent/awesome-ai-agent-papers

### 13.3 Framework-Vergleich + Production-Benchmarks 2026

- **Agent Architectures: ReAct vs Plan-Execute vs Graph** (dasroot.net, 2026-04): https://dasroot.net/posts/2026/04/agent-architectures-react-plan-execute-graph-agents/
- **Best Multi-Agent Frameworks 2026** (gurusup.com): https://gurusup.com/blog/best-multi-agent-frameworks-2026
- **AI Agent Benchmarks 2026: Performance, Accuracy & Cost** (aiagentsquare.com): https://aiagentsquare.com/blog/ai-agent-benchmarks-2026.html
- **LangGraph vs CrewAI vs AutoGen 2026** (pooya.blog mit lokalen LLM-Benchmarks): https://pooya.blog/blog/ai-agents-frameworks-local-llm-2026/
- **ReAct vs Plan-and-Execute** (agixtech): https://agixtech.com/react-vs-plan-and-execute-which-reasoning-loop-is-better-for-your-agentic-ai/
- **The Great AI Agent Showdown 2026** (Medium): https://topuzas.medium.com/the-great-ai-agent-showdown-of-2026-openai-autogen-crewai-or-langgraph-7b27a176b2a1
- **CrewAI vs LangGraph vs AutoGen vs OpenAgents 2026**: https://openagents.org/blog/posts/2026-02-23-open-source-ai-agent-frameworks-compared
- **Best AI Agent Frameworks 2026 Decision Matrix** (arsum): https://arsum.com/blog/posts/ai-agent-frameworks/
- **120+ Agentic AI Tools Mapped 2026** (StackOne): https://www.stackone.com/blog/ai-agent-tools-landscape-2026/

### 13.4 SWE-Bench + Coding-Agent-Benchmarks

- **SWE-bench Verified 2026 Leaderboard** (Epoch AI): https://epoch.ai/benchmarks/swe-bench-verified
- **SWE-bench official Leaderboards:** https://www.swebench.com/
- **SWE-Bench Pro: Can AI Agents Solve Long-Horizon SE Tasks?** (Scale AI): https://static.scale.com/uploads/654197dc94d34f66c0f5184e/SWEAP_Eval_Scale%20(9).pdf
- **SWE-Bench+: Enhanced Coding Benchmark** (arxiv 2410.06992): https://arxiv.org/abs/2410.06992
- **SWE-Bench Repo:** https://github.com/SWE-bench/SWE-bench
- **Introducing SWE-bench Verified** (OpenAI): https://openai.com/index/introducing-swe-bench-verified/
- **SWE-Bench Verified Leaderboard** (llm-stats): https://llm-stats.com/benchmarks/swe-bench-verified

### 13.5 Meta/HyperAgents + Harness-Konzept

- **HyperAgents by Meta: When Agents Engineer Their Own Harness** (Cobus Greyling, Apr 2026): https://cobusgreyling.medium.com/hyperagents-by-meta-892580e14f5b
- **A New Harness in Town: Meta-Harness** (softmaxdata): https://softmaxdata.com/blog/a-new-harness-in-town-meta-harness/
- **HuggingFace Paper-Page Meta-Harness:** https://huggingface.co/papers/2603.28052
- **Yoon Hooli Lee's Meta-Harness Demo-Page:** https://yoonholee.com/meta-harness/

### 13.6 Hermes-Internal-Referenzen (aus dem _ref/hermes-agent/ Repo)

- `plugins/memory/holographic/README.md` — HRR-Memory-Theorie (Plate 1995, Gayler 2004)
- `plugins/memory/hindsight/README.md` — Hindsight-Provider-Integration (nutzt **unsere** hindsight-engine)
- `gateway/platforms/ADDING_A_PLATFORM.md` — Gateway-Platform-Extension-Guide (Referenz für exec-6)
- `hermes-already-has-routines.md` — Hermes Self-Routing-Notes

### 13.7 Meta-Harness / EvoSkill / AutoResearch / Feedback Descent

- **Meta-Harness Paper**: siehe §13.2 oben (arxiv 2603.28052)
- **AutoResearch** (Karpathy): https://github.com/karpathy/autoresearch
- **AutoRAG Optimizer** (praktisches AutoResearch-Beispiel): https://github.com/yeyu2/Youtube_demos/tree/main/auto-rag-optimizer
- **EvoSkill** (arxiv 2603.02766, Sentient AGI): https://github.com/sentient-agi/EvoSkill
  - **Expliziter Adoption-Plan:** `exec-harness.md §4d` — File-Mapping, Pattern-Nachbau (nicht Fork), 3-Konsumenten-Architektur
  - EvoSkill-Code (`_ref/EvoSkill/src/`, 91 Files) dient als Referenz, wird nicht geforkt
- **Feedback Descent: Open-Ended Text Optimization via Pairwise Comparison** (Nov 2025, neu entdeckt beim Deep-Dive): https://arxiv.org/abs/2511.07919
  - Wird in EvoSkill `src/feedback_descent.py` genutzt
  - Optional in unseren Evaluator-Mode-Flag einbauen (exec-harness §4d.4)

### 13.8 Bifrost / LiteLLM (für exec-16 Kontext)

- **Bifrost Repo:** https://github.com/maximhq/bifrost
- **Bifrost Docs:** https://docs.getbifrost.ai/overview
- **LiteLLM Docs:** https://docs.litellm.ai/docs/simple_proxy
- (Entscheidung matrix: LiteLLM bleibt, siehe Memory `feedback_bifrost_not_now.md`)

### 13.9 Cross-Refs matrix (bestehende Execs)

- `specs/execution/exec-harness.md` — AutoResearch/Meta-Harness-Pattern-Implementation
- `specs/execution/exec-context.md` §5/§6 — Prompt-Reihenfolge + Compaction
- `specs/execution/exec-memory.md` — Hindsight+MemPalace Dual-Use (owner)
- `specs/execution/exec-11-memory-evolution.md`
- `specs/execution/exec-15-memory-control-ui.md`
- `specs/execution/exec-16-llm-provider-gateway.md` — LiteLLM + Fallback
- `specs/execution/exec-17-observability-harness-traces.md` — OTel + Audit + Harness Stufe 5+6
- `specs/execution/exec-18-unified-agent-schema.md` — agent.* Tabellen
- `specs/execution/exec-12-sandbox-security.md` — Sandbox-Entscheidung (Checkpoint-Manager wartet)
- `specs/execution/exec-10-multi-agent.md` — sollte Production-Pattern aus §9.6 benennen
- `specs/execution/archive/exec-19-devstack-consolidation.md` — Cron-Scheduler-Integration
- `transformersjs.md` + `specs/execution/exec-transformersjs.md` — verwandter Client-Side-ML-Plan
- `postgres.md` — Schema-pro-Service-Pattern

### 13.10 User-Memory (Entscheidungs-Referenzen)

- `~/.claude/projects/-home-lipfi2/memory/feedback_bifrost_not_now.md` — Bifrost-Entscheidung
- `~/.claude/projects/-home-lipfi2/memory/reference_gitnexus_indexes.md` — Index-Landschaft

---

## 14. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-18 | Erstversion. Deep-Dive via gitnexus (47k nodes) + direct-read 15+ key files. 4-Tier Adoption-Klassifizierung. CLI-vs-Enterprise Translation-Matrix. Hybrid-Architektur-Vorschlag (§9). |
| 2026-04-18 | §9.4 Diagramm um Plan-and-Execute als vierten Pfad erweitert (LangChain-2026-Benchmark +92% accuracy). Neu: §9.6 Empirische Rückendeckung 2026 mit 9 Benchmark-Quellen. Neu: §9.7 Meta-Harness-Klarstellung (Methodologie ≠ Architektur). §13 Referenzen komplett neu aufgebaut mit 40+ URLs in 10 Unter-Abschnitten. |
| 2026-04-18 | Sprint 4 Benchmarks explizit an gemeinsamen Evaluator aus `exec-harness §4d` gekoppelt (EvoSkill-Stage-4-Adoption). §13.7 um Feedback-Descent (arxiv 2511.07919) + EvoSkill-Adoption-Plan-Cross-Ref ergänzt. |
| 2026-04-18 | **§3.3 Skills-Guard DONE** (commit `8ff8a6a`, wired `19e50c4`): enterprise port mit dict-input, `matrix-official` trust-level, `pattern_id` im report, invisible-unicode für alle text-files, importer-gating (422 bei reject). **§3.4 Error-Classifier DONE** (commit `21fb602`, wired `19e50c4`): `FailoverReason` incl. `upstream_unavailable`, pure `classify_error`, priority-dispatch, telemetry-only wiring in runner/refiner/llm_node span-events. **§3.5 Rate-Limit-Tracker DONE** (commit `d5fc914`, wired `19e50c4`): per-`(user, provider_key, window)` buckets, LiteLLM `_hidden_params`-shape, `to_prometheus_dict()`, wired via `get_rate_limit_registry()` in `llm_node`. **§3.6 Trajectory DONE** (commit `e8b3858`): ShareGPT JSONL exporter über `agent.spans.events` + `agent.sessions` (exec-18 Migration 017). **§4.5 Prompt-Caching DONE** (fix `9fe9a58`): system-prompt breakpoint nun unconditional + rolling-3 über non-system. Verbleibend Tier-1: §3.1 ContextEngine, §3.2 MemoryProvider. Details siehe §15 Implementation-Status. |
| 2026-04-18 (Phase A) | **§3.1 ContextEngine ABC DONE** (commit `7e1d387`): `context/context_engine.py` mit `ContextStage` enum, `DefaultContextEngine` (80/85/95 thresholds), predicate helpers, custom-config override. 17 tests. **§3.2 MemoryProvider ABC DONE** (commit `7e1d387`): `memory_fusion/memory_provider.py` mit Fan-out `MemoryManager` + error-isolation + `FusionProvider` concrete + `auto_fusion_provider()` factory. 20 tests. Architecture-Decision: **Peer-Service-Pattern** per 2026 hermes+OpenClaw "two-surface plugin model" — context+memory sind Peers des harness, rufen sich nicht gegenseitig. Dokumentiert in `memory_fusion/README.md` + `context/README.md`. Cleanup: `agent/memory/` → `archive/legacy-agent-memory/` (alle 10 Callers migriert), `python-backend/memory/` (toter REST-Stub) → `archive/legacy-memory-service/`, 3 pre-existing test-failures gefixt, 3 Memory-Dir-READMEs (`memory_fusion/`, `memory_engine/`, `archive/`). |
| 2026-04-18 (Phase D) | **§4.4 Credential-Pool DONE** (commit `38b9b64`): `agent/resilience/credential_pool.py` mit `CredentialPool` ABC + `SingleKeyCredentialPool` + `apply_recovery()`-dispatcher. Mappt error_classifier.RecoveryStrategy → pool-state: rate_limit → 1h cooldown, billing → 24h, auth → mark_auth_failed, overloaded/server_error → 5min, no-op bei context/format/timeout/unknown. 28 tests. Bewusst skipped: OAuth-device-code (Nous/Qwen portals) — pure Komplexität für BYO-key Modell, ROI nicht gerechtfertigt. OAuth-Subklasse später als `OAuthCredentialPool(CredentialPool)` wenn SaaS-Reselling-Use-Case kommt. |

---

## 15. Implementation-Status (as of 2026-04-18)

Checkbox-Konvention mimickt `exec-10-multi-agent.md` §Status-Section. `[x]` = in main/dev branches gelandet, `[~]` = partial/blocked, `[ ]` = offen. Commit-SHAs verlinken zu `ralph/resilience-bundle` branch (noch nicht gemerged).

### Tier 1 — Must-Adopt

- [x] §3.3 `skills_guard` — `agent/security/skills_guard.py` (`8ff8a6a`), wired `19e50c4`. 34 tests.
- [x] §3.4 `error_classifier` — `agent/resilience/error_classifier.py` (`21fb602`), wired `19e50c4`. 18 tests.
- [x] §3.5 `rate_limit_tracker` — `agent/resilience/rate_limit_tracker.py` (`d5fc914`), wired `19e50c4`. 10 tests.
- [x] §3.6 `trajectory` (ShareGPT JSONL) — `agent/trajectory/exporter.py` + `scripts/export_trajectories.py` (`e8b3858`). 18 tests.
- [x] §3.1 `ContextEngine` ABC — `context/context_engine.py` (commit `7e1d387`). Default 80/85/95 thresholds, `ContextStage` enum, predicate helpers (should_verbatim_retain / should_compact / should_emergency_compact), custom-config override. 17 tests.
- [x] §3.2 `MemoryProvider` ABC + MemoryManager — `memory_fusion/memory_provider.py` (commit `7e1d387`). Fan-out coordinator mit per-provider error-isolation, FusionProvider concrete impl, `auto_fusion_provider()` factory, system_prompt_blocks aggregation. 20 tests. Architecture: peer-service pattern per 2026 hermes + OpenClaw "two-surface plugin model" — context+memory sind Peers des harness, rufen sich nicht gegenseitig.

### Tier 2 — Adapt-with-Adaptation

- [x] §4.5 Prompt-Caching (Anthropic cache_control) — in `llm_node.py` (`9fe9a58`). System + 3-msg rolling window. 7 tests.
- [ ] §4.1 Cron-Scheduler — **nicht blockiert** (exec-19 archiviert; NATS läuft; siehe §10 Sprint-3-Detail für Go-Implementation-Plan in go-appservice/internal/scheduler/).
- [ ] §4.2 Skill-Manager-Tool — exec-skills.md existiert, aber `agent.agent_skills` DB-flow noch offen.
- [ ] §4.3 Checkpoint-Manager — blockiert auf exec-12 Sandbox-Decision.
- [x] §4.4 Credential-Pool — `agent/resilience/credential_pool.py` (commit `38b9b64`). ABC `CredentialPool` + `SingleKeyCredentialPool` wrapping `get_user_api_key`. `apply_recovery()` dispatcher classifies `ClassificationResult` → rate_limit (1h) / billing (24h) / auth → mark_auth_failed / overloaded+server_error (5min) / no-op (context/format/timeout/unknown). 28 tests. Multi-key-per-user bleibt der DB-Schema-Erweiterung vorbehalten — OAuth-Provider (Nous/Qwen portal) deliberately skipped (BYO-key model macht den Aufwand nicht wett; siehe SOTA-Diskussion im ralph-Log).

### Tier 3 — Evaluate Carefully

- [ ] §5.1 OpenAI-compat HTTP-Endpoint — defer to v2.0.
- [ ] §5.2 ACP-Adapter — NATS-native bevorzugt.
- [ ] §5.3 Holographic Memory — research-track, entkoppelt.
- [ ] §5.4 Smart Model Routing — post exec-16 Cost-Tracking.
- [ ] §5.5 Process-Registry — NATS-Pattern bevorzugt.
- [ ] §5.6 Batch-Runner — NATS-Worker-Pool bevorzugt.

### Tier 4 — Kleine Gems

- [ ] §6.1 Manual-Compression-Feedback UX — 1h control-ui.
- [ ] §6.2 Title-Generator — 2h control-ui.
- [~] §6.3 Insights-Report — exec-17 OpenObserve deckt das ab.
- [ ] §6.4 scan_cron_prompt (Injection-Defense) — koppeln mit §4.1.
- [~] §6.5 Prompt-Builder + Hints — exec-context §5 deckt das ab.

### Wiring / Infrastruktur

- [x] `ErrorPacket.metadata` Back-compat-Erweiterung (runner SSE flow tragt classification) — `streaming.py`.
- [x] `get_rate_limit_registry()` Accessor-Pattern in `llm_node.py` (Test-isolable).
- [x] `_skill_to_scan_input` + `_scan_trust_source_for_tier` helpers in `agent/skills/importer.py`.
- [x] REST 422 für skills_guard reject in `agent/app.py`.
- [x] `get_credential_pool()` / `reset_credential_pool()` Accessor-Pattern in `agent/resilience/credential_pool.py` (Test-isolable, mirror von rate_limit_registry).
- [x] `apply_recovery(pool, credential, classification)` — bridges error_classifier.RecoveryStrategy → pool state mutation. Ein Aufruf pro post-LLM-error.
- [ ] Frontend TS-types für `ErrorPacket.metadata.failover_reason` — aktuell in `metadata` gebuckt (kein TS-touch nötig), aber konsumierende UI sollte später die Keys typen.
- [ ] Call-site wiring of CredentialPool.acquire() in llm_node before LLM-call — Phase-E Arbeit (nicht in exec-hermes scope, aber Voraussetzung für "richtige" Rotation statt nur Telemetry).
- [ ] `memory_fusion.MemoryManager` + `context.ContextEngine` wiring in runner.py/llm_node — Phase-E (analog CredentialPool).
- [ ] HITL NotificationDrawer für skills_guard `dangerous`-verdicts — blockiert auf exec-12.

### Test-Summe

- Pre-Phase-A (resilience bundle merge): `python-backend/tests/agent/` 102 passed.
- Post-Phase-A (ABCs landed, legacy archived): 155 passed. 37 neue tests (17 context_engine + 20 memory_provider).
- Post-Phase-D (Credential-Pool): 183 passed. 28 neue tests (credential_pool).
- 3 pre-existing failures vom main-branch wurden parallel gefixt (context/policy.py grounded_derived, kg_store.py guard+test).
- ruff check: clean across all Phase-A/Phase-D-touched directories.
