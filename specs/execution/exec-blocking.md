# exec-blocking: Externe Blocker + strategisch verschobene Punkte (C)

**Zweck:** Sammelstelle fuer Tasks, die aktuell **extern blockiert** sind oder bewusst **nicht sinnvoll** sind, sie in die aktiven Slices einzumischen.  
**Regel:** In den eigentlichen `exec*` Slices stehen nur implementierbare Code-Tasks + normale Verify-Gates. Alles was hier landet, wird dort nur noch **verlinkt**.

---

## C1. Matrix: Encrypted State Events (MSC3414/MSC4362) — wartet auf Tuwunel

- **Quelle**: `exec2-01-matrix-chat-core.md` (C-4), `exec2-02-protocol-infra.md`, `exec2-04-verify-gates.md`
- **Warum blockiert**: Homeserver/Tuwunel Support fehlt; im SDK vorbereitet.
- **Trigger zum Wiederaufnehmen**:
  - Tuwunel changelog/release bestaetigt MSC3414/MSC4362 Support, oder
  - wir entscheiden, die Funktion auf Serverseite zu emulieren (nur falls protokollkonform moeglich).
- **Verify-Gates (wenn wieder aktiv)**:
  - `enableEncryptedStateEvents: true` aktiviert
  - Encrypted State Events funktionieren ohne Decrypt-Fehler in Client + Bot

---

## C2. Matrix: OIDC/MAS Auth — Legacy SSO, MAS inkompatibel (Portierungsthema)

- **Quelle**: `exec2-02-protocol-infra.md`, `exec2-04-verify-gates.md`
- **Warum blockiert**: MAS nicht kompatibel, nur Legacy SSO evaluiert; konkrete Zielarchitektur/Serverpfad unklar.
- **Trigger**:
  - MAS Support in Tuwunel, oder
  - klares Portierungsziel (z.B. anderer HS / Proxy).
- **Verify-Gates**:
  - OIDC Login Flow stabil, Token refresh, logout, und Appservice Auth sauber

---

## C3. Federation + Prod-Security Runbook (erst bei Deployment)

- **Quelle**: `exec2-04-verify-gates.md` Sektion "Federation + Security"
- **Warum blockiert**: braucht echte Domain/DNS/TLS + Prod-Setup.
- **Trigger**:
  - Entscheidung "federation on" oder "private-only" + Prod-Domain vorhanden.
- **Verify-Gates** (aus `exec2-04`):
  - `allow_federation = true` gesetzt (falls gewollt)
  - DNS `_matrix._tcp` SRV oder `.well-known/matrix/server`
  - HTTPS + echte Domain
  - Anti-Spam Bot (Draupnir/Mjolnir), ACLs, invite-policy, Directory hidden

---

## C4. E2EE Architektur-Entscheidung: Multi-Agent Skalierung

- **Quelle**: `exec-05-nats-e2ee-pipeline.md` (Architektur-Entscheidung A/B/C/D), `exec-05c-agent-isolation.md`
- **Status**: Option A aktiv. Hybrid (Option C) als Zukunftsoption dokumentiert.
- **Warum hier**: Endgueltige Entscheidung ob Per-Agent E2EE (Option B/C) noetig wird,
  haengt von Produktionsanforderungen ab (1000+ User Szenario, Compliance).
- **Trigger zum Wiederaufnehmen**:
  - Multi-Tenant Deployment geplant, oder
  - Security Audit fordert Per-Agent Crypto-Isolation
- **Verify-Gates (wenn wieder aktiv)**:
  - vodozemac-python evaluiert + getestet
  - Per-Agent Crypto-Store funktioniert
  - NATS Subject-Routing (exec-05c) als Voraussetzung verifiziert

### Warum Agents ueberhaupt OLM-Keys brauchen (FAQ-Antwort, 2026-04-21)

**Frage:** "Wenn Agents sowieso Matrix-User sind — warum muessen *wir* ihnen OLM-Keys geben? Sollten sie die nicht wie normale User selbst managen?"

**Antwort:**

Matrix macht **keinen Unterschied** zwischen human und bot users. Jeder Teilnehmer in einem E2EE-Raum braucht device_keys (curve25519 fuer Olm, ed25519 fuer Signing). Ohne Keys sieht der Agent nur `m.room.encrypted` blobs, kann nicht entschluesseln, kann nicht antworten.

Was sich unterscheidet ist **wer die Keys managed**:

| Human User (alice via Element-Client) | Agent User (`@agent-*`) |
|---|---|
| Client-App (Element/Cinny) haelt Keys in IndexedDB / native secure store | `go-appservice` haelt Keys in zentraler OlmMachine + postgres |
| `/keys/upload` beim Login | `/keys/upload` im Appservice-Startup |
| User cross-signs eigene Devices | Appservice cross-signs alle Agent-Devices |
| Key-Backup via `m.megolm_backup.v1` | `megolm_keys_backup.bin` im appservice key-backup-Pfad |

Das go-appservice **ist der Client** fuer alle Agent-User — es spielt dieselbe Rolle die Element fuer alice spielt, aber fuer n Agent-Identitaeten gleichzeitig. Das ist Matrix-Spec-konform via **MSC3202 (Appservice E2EE)**, implementiert in mautrix-go.

**Warum heute shared OlmMachine statt per-agent:**

1. **Skalierbarkeit** — ein Prozess handled 1000+ Agent-Users vs. 1000+ Prozesse mit je eigener OlmMachine
2. **Key-Bootstrap einmalig** — zentraler cross-signing-setup einmal im Appservice, nicht pro-Agent-MFA-ritual
3. **Backup-Konsolidierung** — ein `megolm_keys_backup.bin` statt n files
4. **Device-Namespace** — die Appservice ist **autorisiert fuer den gesamten `@agent-*` namespace** (siehe `registration.yaml`), kann also on-demand neue Agent-User anlegen + fuer sie signen ohne weitere Authentifizierung

**Wann das NICHT mehr reicht** (Trigger fuer Option B/C Refactor):
- Memory-isolation-Anforderung: prozess-crash in einem Agent-context darf andere nicht korrumpieren
- Compliance (z.B. Finanz/Health): per-agent crypto-audit-trail, forensische Trennung
- Multi-Tenant-SaaS: anderer Kunde, anderer crypto-store

Bis dahin ist der shared-OlmMachine-ansatz (Option A) der SOTA-Weg. Siehe auch `exec-05c-agent-isolation §1-3` fuer das Routing darüber.

---

## C5. Tuwunel v1.6 Upstream Bugs — Tracking (Stand 11.04.2026)

- **Quelle**: `exec2-03b-advanced-matrix-options.md` (Section 6), `exec2-04-verify-gates.md` (J7)
- **Warum hier**: Upstream-Bugs die wir nicht selbst fixen koennen. Workarounds in unserem Code wo moeglich, sonst warten.
- **Trigger**: Tuwunel v1.6.0 stable Release oder Patch-Releases die diese Issues fixen.

| Bug | Severity | Unser Workaround | Status |
|---|---|---|---|
| [#411](https://github.com/matrix-construct/tuwunel/issues/411) S3 Large File Timeout | CRITICAL | `max_request_size ≤ 100 MB` | Blockiert J5 (max_request_size erhoehen) |
| [#401](https://github.com/matrix-construct/tuwunel/issues/401) Appservice /whoami device_id | HIGH | Pruefen ob mautrix-go betroffen; ggf. device_id aus lokaler Config | Offen, Test bei Go-Appservice-Integration |
| [#377](https://github.com/matrix-construct/tuwunel/issues/377) device_lists.changed fehlt in /sync | MEDIUM | `FetchKeys()` Workaround in `go-appservice/internal/crypto/machine.go:EnsureSession()` | ✅ Proaktiv gefixt |
| [#372](https://github.com/matrix-construct/tuwunel/issues/372) /room_keys/version 500 statt 404 | LOW | Pruefen ob mautrix-go 500 korrekt handled | Offen, Test bei Go-Appservice-Integration |

---

## C6. exec2-03b Future Features — Account-Provisioning + BYOS (Backlog)

- **Quelle**: `exec2-03b-advanced-matrix-options.md` (Phase A/B/C)
- **Warum hier**: Grosse Feature-Bloecke die eigene Exec-Sessions brauchen und von mehreren Abhaengigkeiten blockiert sind.
- **Trigger**: exec2-01 (Matrix Chat Core) abgeschlossen + exec-merge-chat (Hauptprojekt-Integration) + OIDC/MAS auf Tuwunel verfuegbar.

**Phase A: Auto-Create (Minimum Viable)**
- A1: OIDC/MAS Integration (blockiert durch C2 oben)
- A2: Post-Login Matrix Init (initMatrixClient, Cross-Signing Bootstrap)
- A3: Onboarding Wizard (optional)

**Phase B: BYOS (Bring Your Own Server)**
- B1: Server-Auswahl UI (Homeserver URL + Well-Known Discovery)
- B2: Federation Verify (blockiert durch C3 oben)
- B3: E2EE Key Management UI

**Phase C: Multi-Account** (erst bei echtem Bedarf)
- C1: Mehrere Matrix-Accounts gleichzeitig + Account-Switcher

**Verify-Gates** bleiben in `exec2-04-verify-gates.md` (Gates A/B/C) — werden erst aktiv wenn die entsprechende Phase gestartet wird.

---

## C7. Streaming SSE default (Phase-D) — derzeit batch, SOTA wäre token-stream

- **Quelle**: session 2026-04-20, plus `agent/runners/simple.py` docstring-lock
- **Status**: Backend ruft `graph.ainvoke()` + sendet 1 × `TextDeltaPacket(final)` (batch-mit-SSE-transport). Frontend (`@ai-sdk/react::useChat`) handelt token-streaming nativ — aber backend liefert kein token-stream. SimpleLoop hat `STREAMING DISABLED — see Phase-D` marker.
- **Warum jetzt blockiert**: Streaming aktivieren invalidiert Phase-C A/B-parity (LangGraph batch vs SimpleLoop stream = apples-vs-oranges). Beide runner müssen simultan migriert werden, oder A/B-dispatcher muss beide als batch behalten bis langgraph-streaming sauber funktioniert.
- **Trigger zum Wiederaufnehmen**:
  - Phase-C A/B liefert reale Daten (braucht erst `exec-scheduler §8.1` scorer-worker).
  - Konsens dass streaming sowohl simple.py als auch runner.py (via `graph.astream_events()`) parallel aktiviert wird.
  - SSE-contract-validierung mit AI-SDK für echte token-stream (frontend hat noch nie echten stream gehandelt).
- **Anker-Dateien bei Wiederaufnahme**: `agent/graph/nodes/llm_node.py:183` (litellm call), `agent/graph/runner.py:346` (graph.ainvoke), `agent/runners/simple.py` (streaming-lock docstring).

---

## C8. NATS JetStream für `sync_turn` at-least-once delivery

- **Quelle**: session 2026-04-20, `agent/graph/runner.py:444-456` ADR-comment, Phase-B §15 debt-list
- **Status**: Heute `asyncio.create_task(_safe_sync_turn(...))` fire-and-forget. Bei process-crash mid-turn ist memory-sync verloren. `agent.sync_failures` table fängt behandelte exceptions, nicht crash-loss. JetStream-infra läuft schon (`docker-compose.yml: nats --js`), scheduler nutzt es.
- **Warum jetzt nicht bauen**: noch keine messbaren memory-loss-incidents. NATS-publish adds ~1-3ms hot-path. Komplexität (DLQ-monitoring, consumer-deployment) ohne nachgewiesenen schmerz nicht gerechtfertigt.
- **Trigger**: harness §4g A/B-data zeigt memory-loss korreliert mit fitness-regressions, ODER konkreter incident.
- **Dann zu bauen**: neuer NATS stream `AGENT_MEMORY` (WorkQueue retention, 24h TTL, file storage) + `agent/memory/sync_consumer.py` + DLQ endpoint. ~200 LOC.

---

## C9. Tracing (agent.spans) + Audit (agent.audit_events) — parallel mit ADR, nicht mergen

- **Quelle**: session 2026-04-20 desktop-file
- **Status**: Two parallel stores. Tracing = `agent/tracing.py` + `agent.spans` JSONB (performance, 30d retention, Grafana/OpenObserve). Audit = `agent/audit/` + `agent.audit_events` (compliance, 1y retention, Control-UI AuditTab). Overlap: beide emittieren bei LLM-call + tool-call.
- **Entscheidung**: Nicht mergen. Unterschiedliche consumers, retention-policies, query-pattern. ABER: cross-write elimination nötig (heute double-write wo span + audit-event gleiche infos halten).
- **TODO (nicht deferred, aber nicht kritisch)**: ADR in `exec-17-observability-harness-traces.md` die dokumentiert warum parallel + ~50 LOC cross-write-removal.

---

## C10. Per-model ContextEngine thresholds — meta-harness statt hardcoded

- **Quelle**: session 2026-04-20 (user rejected hardcoded dict 2026-04-20)
- **Status**: Heute globales 80/85/95 für alle modelle. Kein per-model-override im code.
- **Warum**: Keine empirische grundlage für modell-spezifische thresholds ohne benchmarking. Hardcoded dict ist pseudo-empirie.
- **Richtiger pfad**: meta-harness (`agent/harness/scorer.py` + exec-harness §4g) soll via fitness-score-regression lernen welche thresholds je modell optimal sind — sobald Phase-C A/B daten liefert (braucht `exec-scheduler §8.1` scorer-worker).
- **Trigger**: A/B-data + harness fitness-regression-analysis zeigt threshold-sensitivität per model.

---

## C11. Phase-B carried-forward debt (aus `exec-hermes.md §15`)

- **Quelle**: exec-hermes Phase-B §15 debt-list, confirmed 2026-04-20
- **Offene items**:
  - `agent.user_llm_settings.preferred_runner` column — Hook im Phase-C dispatcher reserved (`variant_policy` TODO comment in `agent/runners/dispatcher.py`), aber nicht implementiert. Triggert sich selbst wenn user-facing variant-picker gebraucht wird.
  - CredentialPool multi-key-per-(user, provider) — heute nur `SingleKeyCredentialPool`. Key-rotation + pool-warmup-strategie unimplemented. Triggert bei SaaS-reselling-use-case.
  - InsightsEngine periodic aggregation — läuft on-demand in `score_session`. Event-driven rollup via NATS-consumer not built. Triggert wenn billing-dashboards latenz-sensitiv werden.
  - MemPalace/Hindsight concrete `on_pre_compress` impls — ABC contract steht (`exec-memory.md §3h`), concrete impls deferred. Triggert wenn compression ohne verbatim-archive-path als datenverlust auffällt.

---

## Session-Audit 2026-04-20 — spec landscape

- **Duplicate resolved**: `exec-transformers-js.md` → `archive/exec-transformers-js-SUPERSEDED.md` (duplicate of `exec-transformersjs.md`, latter ist active primary).
- **Superseded resolved**: `exec-merge-chat.md` → `archive/exec-merge-chat-SUPERSEDED.md` (realized on branch `claude/merge-frontend-chat-ui-2OqmH`, code on main via `frontend_merger/`).
- **Rest 47 specs**: status scan in session notes, not duplicated here.
