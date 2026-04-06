# SYSTEM STATE (IST / SOLL)

> **Stand:** 17. Maerz 2026
> **Zweck:** Kompakte Wahrheit ueber aktuellen Runtime-Stand, Schichten,
> Transportpfade und offene Zielbilder. Dieses Dokument ist **kein** Changelog und
> **keine** Roadmap.
> **Roadmap-Owner:** [`EXECUTION_PLAN.md`](./EXECUTION_PLAN.md)
> **Hinweis:** `SYSTEM_STATE.md` bleibt bewusst bestehen als kurze Runtime-Truth.
> Architektur- und Daten-Details sind in eigene Owner-Specs ausgelagert.

---

## 1. Executive Snapshot

| Schicht | IST | SOLL |
|:--------|:----|:-----|
| Frontend / BFF | Next.js 16 App Router mit Thin-Proxy-/BFF-Routen | nur noch kontrollierte BFF-Flaechen, keine versteckte Business-Logik |
| Go Gateway | zentrale Frontdoor fuer Market, Geo, Memory, Portfolio-nahe und interne Service-Routen | klare Control Plane fuer Auth, Policy, Audit, Routing, Streaming und spaeter async orchestration |
| Python Services | interne Compute-/ML-/Agent-/Memory-Services hinter Go | Python wird logisch in `compute`, `agent` und `indexing` getrennt |
| Rust | lokaler Compute-Layer, aktuell vor allem via `python-backend/rust_core` | staerkere Produktionsgrenze fuer Hot Paths, selektiv auch direkter Go↔Rust-Pfad |
| GCT / go-crypto-trader | externer Read-/Execution-nahe Crypto-Upstream hinter dem Gateway | read-only Slices selektiv absorbieren, keine blinde Volluebernahme |
| Stores | SQLite/Prisma lokal, JSON-Fallbacks an einzelnen Stellen, Redis/DB/NATS optional oder vorbereitend | `Postgres` als SoR, `SeaweedFS` fuer Artefakte, `Valkey` fuer Cache/Locks, `pgvector` fuer document-centric retrieval, `FalkorDB` fuer graph-centric retrieval, `DuckDB` fuer Analytics-/Replay-Pfade |

### Wichtigste offene Runtime-Drifts (kompakt)

- Next erwartet `/api/v1/agent/chat`, die Go-Route ist nicht ueberall konsistent
  verdrahtet.
- `/api/v1/portfolio/order` ist in Policy-/Middleware-Teilen referenziert, aber
  nicht in jedem Laufzeitpfad konsistent gemappt.
- Capability-Enforcement ist in Teilbereichen noch fail-open/flag-gated.

---

## 2. Versions- und Runtime-Fakten

| Bereich | Aktueller Stand |
|:--------|:----------------|
| Next.js | `16.1.1` |
| React | `19` |
| TanStack Query | `5.82.x` |
| Auth.js / next-auth | `5.0.0-beta.30` |
| Go | `1.26.1` |
| Python | `>=3.11` (praktisch 3.12+ orientiert) |
| FastAPI | `0.116.1` |
| Rust Bridge | `maturin` + PyO3 crate `tradeviewfusion-rust-core` |

### Hauptports

| Dienst | Port |
|:-------|:-----|
| Next.js | `3000` |
| Go Gateway | `9060` |
| finance-bridge | `8081` |
| geopolitical-soft-signals | `8091` |
| indicator-service | `8092` |
| memory-service | `8093` |
| GCT gRPC | `9052` |
| GCT JSON-RPC | `9053` |
| optional Python gRPC | HTTP-Port `+1000` |

---

## 3. Aktuelle Systemformel

### Sync / User Path

`Browser -> Next.js -> Go Gateway -> Python and/or GCT and/or provider -> Go -> Next.js -> Browser`

### Heavy Compute Richtung

`Go Gateway -> Python reference / agent / ML layer -> Rust kernels today`

### Zielrichtung fuer Hot Paths

`Go Gateway -> Rust compute boundary -> Python consumes features / orchestrates ML / simulation`

### Asynchrone Richtung

NATS/JetStream, Connect-/service-boundaries und laengere Workflow-Themen sind
vorbereitet, aber noch nicht die dominante Alltags-Laufzeit des Systems.

### Zielbild fuer Python-Domains

- `compute` — Indicators, Aggregation, Feature Engineering, Backtesting-nahe Analytics
- `agent` — Retrieval, Context, Verification, Tooling, Simulation
- `indexing` — Parse, Normalize, Chunk, Embed, Graph-Extract, Reindex

---

## 4. Ownership pro Schicht

| Schicht | Owner | Nicht primaer hier |
|:--------|:------|:-------------------|
| Next.js | UX, BFF, Session-Kontext, server/client composition | Provider-Routing, Domain-Truth, direkte Python- oder GCT-Aufrufe |
| Go Gateway | Policy, AuthZ/AuthN-Enforcement, Request-Korrelation, provider routing, streaming, audit, thin orchestration | grosse ML-/LLM- oder Research-Logik |
| Python | logisch getrennt in `compute`, `agent`, `indexing`; ML, retrieval/context assembly, soft-signals, simulation und indexing workers | Browser-frontdoor, offene externe Fetch-Wildwest-Logik |
| Rust | numerische Hot Paths, Indikator-Kerne, Batch-/Monte-Carlo-/Signal-Kernels | Policy, BFF, breit volatile Research-Logik |
| GCT | crypto-specific read/order infrastructure hinter Gateway | allgemeine Makro-/Geo-/Agent-Plattformlogik |

---

## 5. Wichtige Boundaries

### Frontend

- Markt-, Geo-, Memory- und Strategiepfade laufen Go-first.
- Next.js ist BFF/Thin-Proxy, nicht zweite Backend-Truth.
- Browserseitig gespeicherte Provider-Keys werden fuer Market-Pfade zusaetzlich
  kontrolliert an serverlesbare Next/Go-Pfade gespiegelt.

### Go Gateway

- zentrale Security-/CORS-/Request-ID-Middleware
- request-scoped Provider-Credentials fuer read-only Providerpfade eingefuehrt
- gemeinsame `MarketTarget`-/Resolver-Grenze fuer Quote / Orderbook / SSE read
- BaseConnector-/Capability-/Retry-/Error-Class-Foundation vorhanden
- Gateway-Qualitaetsbaseline aktuell gruen: `golangci-lint run ./...`,
  `go build ./...`, gruppierte `go test`, gruppierte `go test -race` und
  `govulncheck ./...`

### Python

- Services laufen intern hinter Go
- Go↔Python IPC ist gRPC-first moeglich, HTTP-Fallback bleibt vorhanden
- Python bleibt fuer Agentik, Retrieval, ML, Research und Simulation zentral

### Rust

- PyO3 Bridge ist aktiv
- Zielbild ist selektiv weniger Python im Hot Path, nicht weniger Python im
  Research-/Agent-Layer

---

## 6. Auth / Security Baseline

| Thema | IST |
|:------|:----|
| Session-Modell | Auth.js / next-auth v5 beta Baseline aktiv |
| Session-Lebensdauer | `8h` Session-`maxAge` mit `10min` Soft-Lock als primaerer Idle-Schutz |
| Rollen | `viewer`, `analyst`, `trader`, `admin` Richtung vorhanden |
| Go-Enforcement | JWT-/RBAC-/RateLimit-Scaffolds und Security-Header vorhanden; produktive Policy-Richtung klar |
| GCT-Hardening | GCT-Prefix, Hardening-Checks, Audit-Scaffolds, AES-GCM-Helfer vorhanden |
| Provider-Credentials | user-supplied read-only credential path fuer erste Market-Pfade aktiv; `finnhub`, `fred`, `banxico` und `bok` request-scoped verifiziert |

### Wichtig

- Frontend ist **nicht** mehr der normative Aufbewahrungsort fuer Provider-Secrets.
- Markt-Provider-Credentials werden fuer den aktuellen Slice kontrolliert ueber
  Next.js und Go request-scoped transportiert.
- Finale Vault-/DB-/broker-grade Credential-Domain ist noch nicht abgeschlossen.

---

## 7. Daten, Stores und Persistenz

| Bereich | IST | Richtung |
|:--------|:----|:---------|
| App-DB | Prisma + SQLite lokal | fuer UI-/BFF-nahe Daten lokal weiter ok; Go-owned Domain- und Metadata-Layer mittelfristig in backend-owned relationale DB ziehen |
| Memory | memory-service aktiv; KG/vector/episodic Infrastruktur existiert | weiter haerten statt neu erfinden |
| Source Persistence | Rohdownloads und source-spezifische Snapshot-Klassen jetzt als eigene Architekturfrage erkannt, aber noch nicht vollstaendig als produktive Storage-Pipeline umgesetzt | klare Trennung `cache` vs. `raw snapshot` vs. `normalized snapshot` ueber Object Storage + relationalen Snapshot-Index |
| GCT / Audit | JSONL + SQLite-nahe Audit-Bausteine vorhanden | spaeter Gateway-owned Domain-Audit / execution-state |
| Valkey / Redis-kompatibel | als Working-Memory-/cache-Baustein vorgesehen, teils bereits genutzt oder vorbereitet | zentraler Hot-Path Cache / working memory; `Valkey` ist Zieldefault |
| NATS JetStream | vorbereitet / teilweise implementiert | spaeter async backbone fuer Replay / fanout / compute lanes |
| DuckDB | noch nicht produktive Default-Schicht | spaetere lokale/serverseitige Analytics-, Replay- und Worker-SQL-Engine |
| MotherDuck | nicht aktiv | nur spaetere DuckDB-Concurrency-/Cloud-Stufe |
| Druid | nicht aktiv | nur spaetere verteilte Realtime-Analytics-Sonderklasse |

### Klare Zielregel

Eine kuenftige Gateway-DB entsteht **nicht** als Kopie des GCT-Datenmodells,
sondern nur dort, wo das Gateway selbst Domain-Truth besitzt:

- orders / order-status / fills
- balances / positions / reconciliation
- idempotency / retry / workflow-state
- broker-credential metadata
- spaetere execution- und backtest-Artefakte

Zusaetzliche Persistenzregel fuer Quellen:

- Hot cache reduziert Latenz, ist aber kein Source of Truth
- Raw snapshots liegen object-first
- Snapshot-Metadaten und Parserstatus liegen relational
- Vector-/retrieval-faehige Artefakte entstehen erst nach Normalisierung

Ownership-Regel fuer den mittelfristigen DB-Schnitt:

- Was Go als Write-Owner oder Policy-Owner kontrolliert, soll mittelfristig
  nicht dauerhaft im frontend-/Prisma-nahen DB-Pfad bleiben
- staging/prod Zielbild ist ein backend-owned relational metadata/index layer
  fuer Go-owned Betriebs- und Snapshot-Daten

---

## 8. Epistemische Schichten

Diese Trennung ist fuer den Gesamtzustand verbindlich, auch wenn sie noch nicht
ueberall vollstaendig implementiert ist:

- **truth**: kanonische oder stark verifizierte Fakten
- **belief**: plausibler, aber unsicherer Arbeitsstand
- **scenario**: hypothetische Simulations- und Planungszweige

Die Trennung soll in Memory, Agentik, Claim-Verifikation, GeoMap und Simulation
sichtbar bleiben. Kein Layer soll diese Zustaende stillschweigend vermischen.

---

## 9. Agent / Memory / Simulation

| Bereich | IST | Richtung |
|:--------|:----|:---------|
| Agent Runtime | agent-service / tooling / context assembly baseline vorhanden | E2E-Verify und echte Runtime-Hardening offen |
| Langlauf-Orchestrierung | LangGraph spaeter im Python-Agent-Layer; Temporal nur gezielt spaeter | keine voreilige Doppel-Einfuehrung |
| Memory | semantische / episodische / KG-nahe Schicht vorhanden | Wahrheit, belief, overlay, scenario sauberer trennen; Vector-Ingestion nur aus normalisierten und provenance-markierten Inputs |
| Game Theory / Simulation | erste Baseline-Endpunkte vorhanden | GeoMap-gekoppelter Simulationsmodus, nicht bloes Zusatzwidget |

---

## 10. Offene Architekturspalten

### Noch nicht sauber abgeschlossen

- letzte Verify-Gates in Auth, Streaming, GeoMap, Agent-Runtime und Provider-Rollout
- klare Produktionsgrenze Go↔Rust fuer schwere Compute-Pfade
- Entscheidung, welche Provider user-supplied Credentials annehmen duerfen
- Gateway-owned Persistenz fuer echte Broker-/execution-Flows

### Bereits klar entschieden

- Go bleibt Control Plane
- Next.js bleibt BFF / Thin-Proxy
- Python bleibt Agentik-/ML-/Simulations-Schicht
- Rust ist gezielte Beschleunigung, nicht Selbstzweck
- Open Web ist Discovery, nicht automatischer Truth-Layer

---

## 11. Source of Truth nach Thema

| Thema | Dokument |
|:------|:---------|
| Roadmap / offene Arbeit | `EXECUTION_PLAN.md` |
| Schichtenzustand | `SYSTEM_STATE.md` |
| Architektur-Baseline und Plane-Schnitt | `architecture/ARCHITECTURE_BASELINE.md` |
| Go Gateway Grenzkontrakte | `architecture/GO_GATEWAY_BOUNDARY.md` |
| Agent Runtime und Policy | `architecture/AGENT_RUNTIME_ARCHITECTURE.md` |
| Memory-Schichten und Storage-Ownership | `architecture/MEMORY_AND_STORAGE_BOUNDARIES.md` |
| Orchestrierung/Messaging-Entscheidungen | `architecture/ORCHESTRATION_AND_MESSAGING.md` |
| Datenaggregation und Datenzonen | `data/DATA_ARCHITECTURE.md` |
| Aggregation IST + Gaps | `data/AGGREGATION_IST_AND_GAPS.md` |
| Storage + Persistenz-Klassen | `data/STORAGE_AND_PERSISTENCE.md` |
| UIL Grenzkontrakte | `data/UNSTRUCTURED_INGESTION_UIL.md` |
| Provider-Status-Matrix | `data/SOURCE_STATUS.md` |
| API / headers / SSE / contracts | `API_CONTRACTS.md` |
| Frontend / state / BFF ownership | `FRONTEND_ARCHITECTURE.md` |
| Auth / policy / secrets / GCT hardening | `AUTH_SECURITY.md` |
| Compute split Go/Python/Rust | `execution/compute_delta.md` |
| Infra / messaging / provider rollout | `execution/infra_provider_delta.md` |
| Source persistence / snapshots | `execution/source_persistence_snapshot_delta.md` |
| Vector ingestion / retrieval boundary | `execution/vector_ingestion_delta.md` |

