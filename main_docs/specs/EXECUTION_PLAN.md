# MASTER EXECUTION PLAN

> **Stand:** 10. Maerz 2026 (Doc Refresh Rev. 4)
> **Zweck:** Hoechst-Level Roadmap, Statusspiegel fuer offene Arbeit und Einstieg
> in die fuehrenden Detaildokumente. Dieses Dokument ist bewusst **kein**
> Changelog, kein Vollindex aller historischen Slices und keine zweite
> `SYSTEM_STATE.md`.
> **Historie / Ledger:** [`../archive/EXECUTION_PLAN_HISTORY.md`](../archive/EXECUTION_PLAN_HISTORY.md)

---

## 1. Was dieses Dokument besitzt

`EXECUTION_PLAN.md` ist nach dem Refresh nur noch Owner fuer:

- offene und aktive Roadmap
- Phasenstatus auf hoher Ebene
- aktuelle Verify-Gates
- Verweise auf fuehrende Mini-Plaene und Fachdokumente
- Dokument-Ownership fuer Arbeitsplanung

Es ist **nicht** mehr Owner fuer:

- lange Revisionshistorien
- erledigte Sprint-Erzaehlungen
- IST/SOLL pro Schicht
- tiefes Endpoint- oder Frontend-Detail

### Pflegepflicht fuer Specs

Die aktiven `docs/specs/*.md` muessen fortlaufend **up to date** gehalten werden.
Wenn Code-, Port-, Boundary-, Auth- oder Ownership-Realitaet sich aendert, wird
nicht nur der Code, sondern auch die fuehrende Spec aktualisiert. Historische
Erzaehlungen gehoeren ins Archiv, nicht in aktive Sources of Truth.

Dafuer gelten:

- Runtime- und Schichtenwahrheit: [`SYSTEM_STATE.md`](./SYSTEM_STATE.md)
- Sync-/Async-/Boundary-Architektur: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- API- und Transportvertraege: [`API_CONTRACTS.md`](./API_CONTRACTS.md) (Index; Details in `api/`)
- Auth / Policy / Trust: [`AUTH_SECURITY.md`](./AUTH_SECURITY.md) (Index; Details in `security/`)
- Frontend-Boundaries und State-Schnitt: [`FRONTEND_ARCHITECTURE.md`](./FRONTEND_ARCHITECTURE.md)

---

## 2. Fuehrende Detaildokumente

| Thema | Fuehrendes Dokument | Rolle |
|:------|:--------------------|:------|
| Gesamt-Roadmap | `EXECUTION_PLAN.md` | Priorisierung, Status, offene Gates |
| IST/SOLL Schichten | `SYSTEM_STATE.md` | kompakte Runtime-Wahrheit |
| Sync/Async Zielarchitektur | `ARCHITECTURE.md` | technische Leitplanken |
| API / Transport / Headers | `API_CONTRACTS.md` | Contract-Authority |
| Frontend / BFF / State | `FRONTEND_ARCHITECTURE.md` | Frontend-Authority |
| Auth / RBAC / Security | `AUTH_SECURITY.md` | Security-Authority |
| Compute-Split Go/Python/Rust | `execution/compute_delta.md` | aktiver Delta-Plan |
| Infra / Provider / Messaging | `execution/infra_provider_delta.md` | aktiver Delta-Plan |
| Storage Layer (SeaweedFS/Garage) | `execution/storage_layer_delta.md` | aktiver Delta-Plan |
| Architecture Target State | `execution/architecture_target_state_delta.md` | aktiver Delta-Plan fuer Plane-/Store-/Orchestrierungs-Zielbild und Trigger-Regeln |
| Data Aggregation Target State | `execution/a_data_aggregation_target_state_delta.md` | aktiver Delta-Plan fuer Data-Plane-Zielbild, Formate, Retrieval- und Search-Rollen |
| Source Selection / Tiering | `execution/source_selection_delta.md` | aktiver Entscheidungs-Slice fuer Baseline-/Tier-1-/Deferred-Quellenwahl |
| Quellen / Keys / Env-Onboarding | `execution/source_onboarding_and_keys.md` | operative Onboarding-Checkliste |
| Source Persistence / Snapshots | `execution/source_persistence_snapshot_delta.md` | aktiver Delta-Plan fuer Raw-Snapshots, Cadence, Retention und Cache-Abgrenzung |
| Vector Ingestion | `execution/vector_ingestion_delta.md` | aktiver Delta-Plan fuer Chunking, Embedding, Provenance und Retrieval-Abgrenzung |
| GeoMap Closeout / offene Punkte | `execution/geomap_closeout.md` | GeoMap-Checkliste + Verify-Gates |
| Graph Execution Slice | `execution/graph_execution_delta.md` | dedizierter Delta-Plan fuer Graph-Contracts, Graph-UI/Runtime und Verify-Gates |
| GeoMap Backend Slice | `execution/backend_geomap_delta.md` | dedizierter Delta-Plan fuer GeoMap-Backend/API/Store/Policy/Audit |
| Cross-cutting Verify Restpunkte | `execution/cross_cutting_verify.md` | aktive Checkliste |
| Root/Geo/References Vollabdeckung | `execution/root_geo_references_coverage.md` | File-fuer-File Coverage-Matrix |
| Agent/Memory/Context Runtime | `execution/agent_memory_context_delta.md` | aktiver Runtime-/Quality-Delta-Plan |
| Agent Security Runtime | `execution/agent_security_runtime_delta.md` | aktiver Delta-Plan fuer Retrieval/Tool/Capability/Agentic-Storage-Grenzen |
| Agent Harness Runtime | `execution/agent_harness_runtime_delta.md` | aktiver Delta-Plan fuer Harness-Minimalismus, Guardrail-Runtime und OpenSandbox-Execution-Boundary |
| Agent Backend Program | `execution/agent_backend_program_delta.md` | programmweiter Agent-Backend-Owner fuer Contracts, policy/audit/degradation und reference-adoption |
| Agent Code Mode (optional) | `AGENT_CODE_MODE.md` | Root-Owner fuer evaluate-only code-mode-Pattern und Adoption-Gates |
| Agent-GeoMap Bridge | `execution/agent_geomap_bridge_delta.md` | Companion-Slice fuer Agent<->GeoMap Contracts (Policy/Audit/Failure), ohne Agent-Core-Neuaufbau |
| Claim Verification / Evidence | `execution/claim_verification_delta.md` | aktiver Claim-/Evidence-Delta-Plan |
| UIL / Candidate Promotion | `execution/uil_candidate_promotion_delta.md` | aktiver Intake-/Promotion-Delta-Plan |
| Domain Intelligence | `execution/domain_intelligence_delta.md` | aktiver Domain-Signal-Delta-Plan |
| References Evaluate / To-Watch | `execution/references_projects_evaluate_delta.md` | aktiver Evaluate-to-Decision-Plan |
| Rust Kand Evaluation | `execution/rust_kand_evaluation_delta.md` | expliziter Bewertungs-Slice fuer `Kand` als Rust-Core-Basis |
| Frontend Refinement / Performance | `execution/frontend_refinement_perf_delta.md` | aktiver Frontend-Refinement-/Perf-Delta-Plan |
| Frontend Enhancement | `execution/frontend_enhancement_delta.md` | aktiver Delta-Plan fuer TS-Vertraege, Fehlermodell, Execution-Policies und Agent-UI-Boundaries |
| Ecosystem Optionality | `execution/ecosystem_optionality_delta.md` | aktiver Plugin-/Partner-/Payment-/Rollout-Delta-Plan |
| Future Quant / Advanced Architecture | `execution/future_quant_advanced_architecture_delta.md` | aktiver Trigger-/Adoption-Delta-Plan |
| Platform DX / Quality | `execution/platform_dx_quality_delta.md` | aktiver DX-/Quality-/Supply-Chain-Delta-Plan |
| Formal Planning (Phase 22b) | `execution/pddl_phase22b_delta.md` | aktiver Pilot-/Gate-Plan fuer PDDL/ADL-Constraint-Layer |

---

## 3. Phase Board

| Phase | Status | Kurzlage | Fuehrende Execution-Owner |
|:------|:-------|:---------|:--------------------------|
| 0 Foundation / Go-first Boundary | **CLOSED** | Go-first, Thin-Proxy, Request-ID, Observability-Baseline und Gateway-Foundation stehen | `execution/infra_provider_delta.md`, `execution/cross_cutting_verify.md` |
| 1 Auth / Security | **BASELINE COMPLETE, residual verify open** | produktive Baseline steht; einzelne advanced E2E-/MFA-/recovery-Gates bleiben offen | `execution/cross_cutting_verify.md` |
| 2 Rust Core | **BASELINE COMPLETE** | Rust-Core vorhanden; Produktionsgrenze Go↔Rust wird weiter geschaerft | `execution/compute_delta.md` |
| 3 Streaming | **BASELINE COMPLETE, browser verify open** | Go-SSE, Snapshot- und Alert-Bausteine aktiv; Rest sind Live-/Browser-Gates | `execution/cross_cutting_verify.md`, `execution/infra_provider_delta.md` |
| 4 GeoMap v2 | **BASELINE COMPLETE, closeout open** | Code und Doc-Fundament stehen; Doc-Abarbeitung ueber `docs/geo/*` + E2E/Perf via `GEOMAP_VERIFY_GATES.md` | `execution/geomap_closeout.md`, `execution/cross_cutting_verify.md` |
| 4a Graph Execution | **PLANNED** | Graph-spezifische Contracts, Runtime-Verhalten, UI-Interaktion und Verify-Gates werden dediziert gefuehrt, um Scope-Drift aus GeoMap-Closeout zu vermeiden | `execution/graph_execution_delta.md`, `execution/geomap_closeout.md` |
| 4b GeoMap Backend | **PLANNED** | GeoMap-Backend-API/Store/Policy/Audit-Arbeit wird als eigener Slice gefuehrt, getrennt von Graph-UI- und Agent-Core-Themen | `execution/backend_geomap_delta.md`, `execution/geomap_closeout.md`, `execution/cross_cutting_verify.md` |
| 5 Portfolio Bridge / Analytics | **BASELINE COMPLETE, browser verify open** | Portfolio-/Analytics-Slices geliefert; Browser-/cache-/query-Gates und GCT-Onboarding offen | `execution/cross_cutting_verify.md`, `execution/infra_provider_delta.md` |
| 6 Memory | **CLOSED** | Phase-6 Baseline und Live-Verify abgeschlossen | `execution/agent_memory_context_delta.md` |
| 7 Indicator Catalog Core | **BASELINE COMPLETE, residual browser verify open** | Kernindikatoren geliefert; Rest sind Frontend-/Browser-Gates | `execution/compute_delta.md`, `execution/cross_cutting_verify.md` |
| 8 Pattern Detection | **BASELINE COMPLETE, final acceptance open** | Implementiert und manuell geprueft; finale pytest-/browserbasierte Abnahme offen | `execution/compute_delta.md`, `execution/cross_cutting_verify.md` |
| 9 Unified Ingestion Layer | **CLOSED, promotion verify open** | Go-owned UIL-Frontdoor und reclassify/metadata-Slice stehen; Candidate-/Promotion-Follow-ups ueber `execution/uil_candidate_promotion_delta.md` | `execution/uil_candidate_promotion_delta.md` |
| 10 Agent Runtime | **CODE COMPLETE, verify open** | Agent-/Context-/Tool-Baseline steht; Runtime- und E2E-Verifikation offen; Agent-Security-Boundaries laufen ueber dedizierten Runtime-Slice | `execution/agent_memory_context_delta.md`, `execution/agent_security_runtime_delta.md`, `execution/cross_cutting_verify.md` |
| 10p Agent Backend Program | **PLANNED** | Plattformweiter Agent-Backend-Owner fuer lifecycle/policy/audit/degradation und reference-driven adoption von OGI/Onyx/Perplexica/AgentZero/Tambo | `execution/agent_backend_program_delta.md`, `execution/agent_memory_context_delta.md`, `execution/agent_security_runtime_delta.md`, `execution/agent_harness_runtime_delta.md` |
| 10a Agent-GeoMap Bridge | **PLANNED** | GeoMap-relevante Agent-Schnittstellen (Action-Class, Approval, Audit, Failure envelope) werden als schlanker Bridge-Slice gefuehrt | `execution/agent_geomap_bridge_delta.md`, `execution/backend_geomap_delta.md`, `execution/agent_security_runtime_delta.md` |
| 12a NLP Upgrade | **CLOSED** | Embedding-/HDBSCAN-Clusterpfad implementiert und verifiziert | `execution/agent_memory_context_delta.md`, `execution/claim_verification_delta.md` |
| 13 Portfolio Advanced | **VERIFIED** | Kelly / Regime / VaR / VPIN-Pfade live verifiziert | `execution/cross_cutting_verify.md`, `execution/compute_delta.md` |
| 14 Provider Expansion | **CODE COMPLETE, rollout verify open** | breite Providerbasis steht; gruppenweise Success-/Error-Path-Verifikation plus Pflege von `docs/references/sources/*`, `references/status.md` und Quellen-/Key-Onboarding offen; aktuelle Reihenfolge: `P1` Credential-Live-Gates, `P2` offizielle `SECO`/`EU`-Pfade, `P3` `FINRA ATS`, `P4` `ADB` nur bei echtem Coverage-Gap | `execution/infra_provider_delta.md`, `execution/source_onboarding_and_keys.md`, `execution/references_projects_evaluate_delta.md` |
| 15 Advanced Indicators / Regime | **PARTIALLY VERIFIED** | Volatility/Regime live verifiziert; weitere Produktionshaertung bleibt | `execution/compute_delta.md`, `execution/cross_cutting_verify.md`, `execution/domain_intelligence_delta.md` |
| 16 Backtesting / Eval Hardening | **BASELINE COMPLETE** | Kernpfade stehen; Release-/OOS-Gates offen | `execution/cross_cutting_verify.md`, `execution/references_projects_evaluate_delta.md` |
| 17 Game Theory | **IN PROGRESS** | Baseline-Endpunkte vorhanden; Systemvertiefung und Domain-Gates laufen ueber `execution/domain_intelligence_delta.md` | `execution/domain_intelligence_delta.md` |
| 18 Options / Dark Pool / DeFi | **BASELINE COMPLETE** | Kernendpunkte stehen; echte Provider-/Live-Daten-Abnahme offen | `execution/infra_provider_delta.md`, `execution/cross_cutting_verify.md` |
| 19 Compute / Rust Service Follow-up | **PLANNED** | spaetere harte Rust-/Compute- und messaging-nahe Folgearbeit | `execution/compute_delta.md`, `execution/infra_provider_delta.md` |
| 20 ML Pipeline | **BASELINE COMPLETE** | Feature-/Classify-/Fusion-/Bias-Pfade stehen; Kalibrierung offen. TanStack DB (MON-5) bei Bedarf local-first fuer Paper Orders / Watchlist evaluieren. | `execution/compute_delta.md`, `execution/agent_memory_context_delta.md` |
| 21 Frontend Refinement | **PLANNED** | Aufraeumen, Zod Contracts, weitere Strukturverbesserungen; Trading-Page God-Component-Aufloesung (URL-Routing, Hooks, Store, Query); TS-/Error-/Execution-Policy-Haertung ueber Frontend-Enhancement-Slice | `execution/frontend_refinement_perf_delta.md`, `execution/frontend_enhancement_delta.md`, `execution/trading_page_refactor_delta.md`, `execution/cross_cutting_verify.md` |
| 22 Advanced Frontend / Perf | **PLANNED** | spaetere UI-/chart-/GPU- oder workspace-lastige Themen | `execution/frontend_refinement_perf_delta.md`, `execution/geomap_closeout.md` |
| 22a Agent Chat UI | **SCAFFOLD DONE** | Streaming Chat-UI ueber Go Gateway → Python/Anthropic; TanStack AI Adoption-Entscheid bei Phase-Start; Typen + Stub in `src/features/agent-chat/`; Ollama/vLLM Provider-Interface (AC7-9); Rig-rs + async-openai als Rust-Backend-Option Phase 22+ | `execution/agent_chat_ui_delta.md` |
| 22b Formal Planning (PDDL / ADL) | **PLANNED, gated pilot open** | PDDL/ADL als formales Constraint-Layer fuer temporale/numerische Workflows; Fokus auf Pilot "Morning Research Run"; JSON Tool Schemas bleiben primaer, PDDL nur bei nachgewiesenem Mehrwert | `AGENT_TOOLS.md` Sek. 15, `execution/pddl_phase22b_delta.md` |
| 22c Agent Harness / Sandbox Runtime | **PLANNED** | Konsolidierter Harness-Layer (Constrain/Inform/Verify/Correct), OpenSandbox als verpflichtende Agent-Execution-Boundary, Guardrail-Runtime und eval-getriebene Regression-Gates | `AGENT_HARNESS.md`, `execution/agent_harness_runtime_delta.md`, `execution/agent_security_runtime_delta.md` |
| 23 Platform Readiness | **CODE COMPLETE, promotion-governance verify open** | Capability Registry / Governance / readiness basis vorhanden; UIL-/Promotion-Governance ueber `execution/uil_candidate_promotion_delta.md` | `execution/uil_candidate_promotion_delta.md`, `execution/root_geo_references_coverage.md` |
| 23a Platform DX / Quality Hardening | **PLANNED** | Reproduzierbares Setup, Hook-/Test-/Security-Gates und Supply-Chain-Hygiene operationalisieren; beinhaltet **Service-Config-Konsolidierung** (hardcodierte Ports/URLs → Env-Vars, Single-Source-of-Truth per Layer) | `execution/platform_dx_quality_delta.md`, `execution/frontend_refinement_perf_delta.md`, `execution/service_config_consolidation_delta.md` |
| 24 Ecosystem Optionality | **CODE COMPLETE, hardening verify open** | Plugin/Partner/Payment/Rollout-Spezifikationen vorhanden; Runtime-Hardening und reversible Rollout-Gates ueber dedizierten Owner offen | `execution/ecosystem_optionality_delta.md`, `execution/references_projects_evaluate_delta.md`, `execution/infra_provider_delta.md`, `execution/source_onboarding_and_keys.md` |
| 25 Future Quant Expansion | **PLANNED** | Trigger-basierte Uebernahme aus `Future-Quant-trading.md` (AFML/QT/PfF) nur mit Evidence und Owner-Routing | `execution/future_quant_advanced_architecture_delta.md`, `execution/compute_delta.md`, `execution/domain_intelligence_delta.md` |
| 26 Advanced Architecture Adoption | **PLANNED** | Uebertragbare GenAI/LLM-Architekturmuster aus `Advanced-architecture-for-the-future.md` in konkrete, gate-faehige Slices ueberfuehren | `execution/future_quant_advanced_architecture_delta.md`, `execution/agent_memory_context_delta.md`, `execution/claim_verification_delta.md` |

### Regel: Execution-Owner je Phase ist Pflicht

Wenn eine Phase keinen klaren `execution/*.md`-Owner hat, ist das ein Hinweis auf
eine fehlende Execution-Spec. In diesem Fall wird zuerst ein passendes
Execution-MD angelegt und dann die Phase referenziert.

---

## 3.1 Systematische Slice-Zuordnung (alle `execution/*.md`)

Die Zuordnung erfolgt verbindlich in vier Schritten:

1. **Slice-Inventar fixieren** (`docs/specs/execution/*.md`)
2. **Jede Slice einem Phase-/Gate-/Cluster-Kontext zuordnen**
3. **Owner-Sichtbarkeit in Phase Board oder Verify-Gates sicherstellen**
4. **Bei neuen Slices sofort diese Matrix und Abschnitt 6 synchronisieren**

| Execution-Slice | Primaere Einordnung | Operativer Sichtbarkeitsanker |
|:----------------|:--------------------|:-------------------------------|
| `execution/agent_backend_program_delta.md` | Agent Backend Program (10p) | Phase Board 10p, Execution-Spec-Strategie |
| `execution/architecture_target_state_delta.md` | Architecture Target State (cross-cutting) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |
| `execution/agent_chat_ui_delta.md` | Agent Chat UI (22a) | Phase Board 22a, Execution-Spec-Strategie |
| `execution/a_data_aggregation_target_state_delta.md` | Data Aggregation Target State (cross-cutting) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |
| `execution/agent_geomap_bridge_delta.md` | Agent-GeoMap Bridge (10a) | Phase Board 10a, Execution-Spec-Strategie |
| `execution/agent_harness_runtime_delta.md` | Agent Harness Runtime (22c) | Phase Board 22c, Verify-Gates, Execution-Spec-Strategie |
| `execution/agent_memory_context_delta.md` | Agent Runtime / Memory / Context (6/10/12a/20) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/agent_security_runtime_delta.md` | Agent Security Runtime (10/22c) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/backend_geomap_delta.md` | GeoMap Backend (4b) | Phase Board 4b, Execution-Spec-Strategie |
| `execution/claim_verification_delta.md` | Claim Verification (12a/26) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/command_keyboard_delta.md` | Frontend Command/Keyboard (21/22) | Execution-Spec-Strategie (Frontend-Cluster) |
| `execution/compute_delta.md` | Compute/Rust/Indicators (2/7/8/13/15/19/20/25) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/control_surface_delta.md` | Control Surface Runtime (frontend ops) | Execution-Spec-Strategie (Frontend/Control-Cluster) |
| `execution/cross_cutting_verify.md` | Cross-cutting Verify | Verify-Gates, Phase Board, Execution-Spec-Strategie |
| `execution/document_widgets_control_delta.md` | Files/Widget-Control Schnitt (frontend ops) | Execution-Spec-Strategie (Frontend/Control-Cluster) |
| `execution/domain_intelligence_delta.md` | Domain Intelligence / Game Theory (15/17/25) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/ecosystem_optionality_delta.md` | Ecosystem Optionality (24) | Phase Board 24, Verify-Gates, Execution-Spec-Strategie |
| `execution/frontend_context_delta.md` | Frontend Context Assembly (21/22) | Execution-Spec-Strategie (Frontend-Cluster) |
| `execution/frontend_enhancement_delta.md` | Frontend Enhancement (21) | Phase Board 21, Execution-Spec-Strategie |
| `execution/frontend_intelligence_calendar_delta.md` | Frontend Intelligence Calendar (21/22) | Execution-Spec-Strategie (Frontend-Cluster) |
| `execution/frontend_portfolio_alerts_shell_delta.md` | Frontend Portfolio/Alerts Shell (21/22) | Execution-Spec-Strategie (Frontend-Cluster) |
| `execution/frontend_refinement_perf_delta.md` | Frontend Refinement/Perf (21/22/23a) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/frontend_research_home_delta.md` | Frontend Research Home (21/22) | Execution-Spec-Strategie (Frontend-Cluster) |
| `execution/future_quant_advanced_architecture_delta.md` | Future Quant/Advanced Architecture (25/26) | Phase Board 25/26, Verify-Gates, Execution-Spec-Strategie |
| `execution/geomap_closeout.md` | GeoMap Closeout (4) | Phase Board 4, Verify-Gates, Execution-Spec-Strategie |
| `execution/graph_execution_delta.md` | Graph Execution (4a) | Phase Board 4a, Execution-Spec-Strategie |
| `execution/indicator_delta.md` | Indicator Runtime/Frontend Slice (7/8/15) | Execution-Spec-Strategie (Compute/Frontend-Cluster) |
| `execution/infra_provider_delta.md` | Infra/Provider Expansion (0/3/5/14/18/19/24) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/pddl_phase22b_delta.md` | Formal Planning Pilot (22b) | Phase Board 22b, Execution-Spec-Strategie |
| `execution/platform_dx_quality_delta.md` | Platform DX/Quality (23a) | Phase Board 23a, Verify-Gates, Execution-Spec-Strategie |
| `execution/python_runtime_eval_delta.md` | Python Runtime Eval Slice (16/20/22c) | Execution-Spec-Strategie (Runtime-Eval-Cluster) |
| `execution/references_projects_evaluate_delta.md` | References Evaluate/Gates (14/16/24) | Phase Board, Verify-Gates, Execution-Spec-Strategie |
| `execution/root_geo_references_coverage.md` | Root/Geo/References Vollabdeckung (23) | Phase Board 23, Verify-Gates, Execution-Spec-Strategie |
| `execution/rust_kand_evaluation_delta.md` | Rust Kand Evaluation (2/19) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |
| `execution/source_onboarding_and_keys.md` | Source/Key Onboarding (14) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |
| `execution/source_persistence_snapshot_delta.md` | Source Persistence/Snapshots (14) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |
| `execution/source_selection_delta.md` | Source Selection/Tiering (14) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |
| `execution/storage_layer_delta.md` | Storage Layer (14/19) | Fuehrende Detaildokumente, Execution-Spec-Strategie |
| `execution/trading_page_refactor_delta.md` | Trading Page Refactor (21) | Phase Board 21, Naechste Delivery-Slices |
| `execution/uil_candidate_promotion_delta.md` | UIL Candidate Promotion (9/23) | Phase Board 9/23, Verify-Gates, Execution-Spec-Strategie |
| `execution/vector_ingestion_delta.md` | Vector Ingestion/Provenance (14/10) | Fuehrende Detaildokumente, Verify-Gates, Execution-Spec-Strategie |

Hinweis:

- Frontend-/Control-/Runtime-nahe Slices koennen gleichzeitig mehreren Phasen dienen; massgeblich sind dann Verify-Gates + Primary Owner im jeweiligen Slice.

---

## 4. Aktueller Fokus

### A. Verify- und Rollout-Arbeit

- Phase 1: verbleibende Auth-E2E-/MFA-/Recovery-Gates schliessen
- Phase 3 bis 5: Browser-/SSE-/Portfolio-Abnahme dort schliessen, wo nur noch
  Live-Gates fehlen
- Phase 7 bis 8: Browser-/pytest-Akzeptanz fuer Indicator- und Pattern-Slices
- Phase 10: Agent-Runtime-/Tooling-Verifikation
- Phase 14: Provider-Rollout gruppenweise statt einzeln abarbeiten
- Phase 14: `docs/references/sources/*`, `references/status.md` und
  `execution/source_onboarding_and_keys.md` bei jeder neuen oder geaenderten
  Quelle mitpflegen
- Phase 14: `execution/source_persistence_snapshot_delta.md` mitpflegen, sobald
  eine Quelle nicht nur gefetcht, sondern gecacht, als Snapshot persistiert oder
  spaeter fuer Retrieval aufbereitet wird
- Storage/Persistence: den mittelfristigen Uebergang von frontend-/Prisma-nahen
  DB-Pfaden zu einer backend-owned relationalen Metadata-/Index-DB fuer
  Go-owned Daten explizit evaluieren und planen
- Phase 14: nach abgeschlossenem Source-Tiering zuerst `finnhub`/`fred`/`banxico`/`bok` live schliessen, dann offizielle `SECO`/`EU`-Pfade vor weiteren neuen Quellen
- Storage Layer: Go-owned Artefakt-Baseline ist geliefert; als naechstes SeaweedFS host-nativ und danach Garage auf dieselbe signed Gateway-Boundary heben
- Memory/Context: Retrieval- und Vector-Pfade konsumieren nur normalisierte,
  provenance-markierte Inputs, nicht direktes Source-Onboarding oder Rohdownloads
- Phase 22b: PDDL/ADL nur als constrained Pilot starten (Morning Research Run),
  mit klaren Go/No-Go-Metriken statt breitem Rollout
- Phase 22c: Harness-Boundaries mit OpenSandbox, Guardrail-Runtime und
  Regression-Gates priorisiert operationalisieren

### B. Architektur-Delta statt Rewrite

- Compute-Grenze Go/Python/Rust weiter schaerfen, ohne Mini-Planausweitung
- weitere read-only Provider und GCT-Slices auf die neue Gateway-Grenze heben
- Credential-Transport und Connector-Hardening breiter ausrollen

### C. GeoMap Doc-Abarbeitung

- **GEOMAP_OVERVIEW:** Owner-/Read-Order fuer GeoMap-Specs
- **GEOMAP_FOUNDATION / GEOMAP_MODULE_CATALOG:** Basemap/Geocoding/Rendering + d3-Modulstrategie
- **GEOMAP_VERIFY_GATES:** E2E-Abnahme, Draw-Workflow, Save-Fehlerpfad, Performance-Baseline
- **GEOMAP_PRODUCT_AND_POLICY / GEOMAP_ROADMAP_AND_MILESTONES:** Milestones, UX-Restpunkte und SOTA-Backlog
- **PHAROS_AI_REVIEW:** externer Flat-/Conflict-Referenzreview, inkl. Monitoring des fuer `2026-03-12` angekuendigten Agent-Layers
- **GeoMap Basemap-Referenzstack:** PMTiles (Protomaps), OpenMapTiles, Planetiler (alt: tilemaker), optional MapLibre Flat-Mode; Globe-Core bleibt d3-geo

Arbeits-Checkliste: `execution/geomap_closeout.md` (Doc-Abarbeitung Sek. 0).

### D. Dokumentations-Disziplin

- Masterplan bleibt schlank
- `SYSTEM_STATE.md` bleibt IST/SOLL-Spiegel
- Execution-Workpacks unter `docs/specs/execution/*.md` bleiben die aktiven
  Arbeitsdeltas; neue Workpacks nur bei klar getrenntem Backlog und Owner

### E. References-Katalog als Delivery-Pflicht

- Der `docs/references/`-Ordner ist kein lose angehaengter Lesekatalog, sondern
  Teil der Delivery fuer Provider-/Quellenarbeit
- Neue oder veraenderte Quellen sind erst dann wirklich eingeplant, wenn
  `sources/*.md`, `references/status.md` und bei Auth-Bedarf
  `execution/source_onboarding_and_keys.md` aktualisiert sind
- Evaluate-/Watch-Kandidaten fuer externe Projekte und Libraries laufen ueber
  `projects/evaluate.md` und `projects/to-watch.md`, nicht mehr ueber
  verstreute Root-Notizen

---

### F. Agentenfeste Vollabdeckung (neu)

- Vollabdeckung wird nicht mehr implizit erwartet, sondern explizit ueber
  `execution/root_geo_references_coverage.md` gesteuert
- Jede Root-/Geo-/References-MD braucht einen `COV.*`-Checkpoint mit Owner
- Neue Themen aus Root-/References-Dokumenten werden nur noch ueber klaren
  Execution-Owner (`execution/*.md`) in aktive Delivery ueberfuehrt

---

## 5. Aktive Verify-Gates

| Gate-Cluster | Fuehrendes Dokument | Restlage |
|:-------------|:--------------------|:---------|
| Auth residual E2E | `execution/cross_cutting_verify.md` | `1.v17`, `1.v18`, `1.v19`, `1.v22` |
| Streaming browser verification | `execution/cross_cutting_verify.md` | SSE reconnect / alert / browser flows |
| GeoMap closeout | `execution/geomap_closeout.md` | Doc-Abarbeitung (`docs/geo/*`), Phase-4-Gate, Milestones D/E/F, SOTA-Backlog, Tests |
| Portfolio browser verification | `execution/cross_cutting_verify.md` | Phase-5: 5.1–5.3 (Bridge, GCT-Onboarding, Panel-Flows) |
| Indicator / Pattern acceptance | `execution/cross_cutting_verify.md` | Phase 7/8 Restgates |
| Agent runtime verification | `execution/cross_cutting_verify.md` | 10.v1-10.v3 |
| Market credential flow | `execution/infra_provider_delta.md` | `MC1-MC5` |
| Provider rollout matrix | `execution/infra_provider_delta.md` | Batch 1-4 Verify-Contract |
| Source-/Key-Onboarding | `execution/source_onboarding_and_keys.md` | Env-/Doku-Pflichten fuer neue Quellen |
| Source Selection / Tiering | `execution/source_selection_delta.md` | `SS1-SS7`, `SS.V1-SS.V3` |
| Source Persistence / Snapshot Policy | `execution/source_persistence_snapshot_delta.md` | `SPS1-SPS8`, `SPS.V1-SPS.V4` |
| Architecture Target State | `execution/architecture_target_state_delta.md` | `ATS1-ATS14`, `ATS.V1-ATS.V6` |
| Data Aggregation Target State | `execution/a_data_aggregation_target_state_delta.md` | `DAT1-DAT18`, `DAT.V1-DAT.V7` |
| Vector Ingestion / Provenance | `execution/vector_ingestion_delta.md` | `VI1-VI7`, `VI.V1-VI.V4` |
| References-Katalog-Pflege | `references/status.md`, `references/sources/*`, `references/projects/*` | neue Quellen/Kandidaten muessen parallel zur Umsetzung nachgezogen werden |
| Compute split / Rust boundary | `execution/compute_delta.md`, `execution/rust_kand_evaluation_delta.md` | `G1-G8`, `RK1-RK6` |
| Agent/Memory/Context Runtime | `execution/agent_memory_context_delta.md` | `AMC1-AMC16`, `AMC.V1-AMC.V10` |
| Agent Harness Runtime | `execution/agent_harness_runtime_delta.md` | `AHR1-AHR9`, `AHR.V1-AHR.V6` |
| Claim Verification | `execution/claim_verification_delta.md` | `CV1-CV5`, `CV.V1-CV.V4` |
| UIL / Candidate Promotion | `execution/uil_candidate_promotion_delta.md` | `UIL1-UIL5`, `UIL.V1-UIL.V4` |
| Domain Intelligence | `execution/domain_intelligence_delta.md` | `DI1-DI5`, `DI.V1-DI.V3` |
| References Evaluate Decision Gates | `execution/references_projects_evaluate_delta.md` | `RPE1-RPE5`, `RPE.V1-RPE.V3` |
| Frontend Refinement / Perf | `execution/frontend_refinement_perf_delta.md` | `FE1-FE9`, `FE.V1-FE.V5` |
| Ecosystem Optionality Hardening | `execution/ecosystem_optionality_delta.md` | `ECO1-ECO8`, `ECO.V1-ECO.V5` |
| Platform DX / Quality Hardening | `execution/platform_dx_quality_delta.md` | `PDQ1-PDQ6`, `PDQ.V1-PDQ.V4` |
| Future Quant / Advanced Architecture Adoption | `execution/future_quant_advanced_architecture_delta.md` | `FQAA1-FQAA6`, `FQAA.V1-FQAA.V4` |
| Knowledgebase Integration (Entropy/Political Economy) | `execution/agent_memory_context_delta.md`, `execution/domain_intelligence_delta.md` | `AMC7-AMC16`, `AMC.V5-AMC.V10`, `DI6` |
| Root/Geo/References Coverage | `execution/root_geo_references_coverage.md` | `COV.ROOT.*`, `COV.GEO.*`, `COV.REF.*` |
| Coverage Completion Governance | `execution/root_geo_references_coverage.md`, `execution/cross_cutting_verify.md` | nur geschlossen, wenn COV-Checkpoints Evidence + Propagation Targets haben |

---

## 6. Execution-Spec Strategy

Die Execution-Specs leben unter `docs/specs/execution/`:

- `cross_cutting_verify.md` — cross-cutting verify checklist
- `compute_delta.md` — Compute-/Indicator-/Go-Python-Rust-Delta-Plan
- `infra_provider_delta.md` — Infra-, Messaging-, Provider- und Rollout-Delta-Plan
- `storage_layer_delta.md` — Storage-/Object-Layer-Auswahl und Integrationscheckliste (SeaweedFS/Garage)
- `architecture_target_state_delta.md` — Zielbild-Delta fuer Planes, Store-Rollen, Orchestrierungsstufen und Trigger-Regeln
- `a_data_aggregation_target_state_delta.md` — Zielbild-Delta fuer Data-Plane, Formate, Retrieval-Rollen und optionale Search-/Governance-Erweiterungen
- `source_selection_delta.md` — Quellenauswahl und Tiering vor technischem Onboarding
- `source_onboarding_and_keys.md` — Quellen-/Key-/Env-Onboarding-Checkliste
- `geomap_closeout.md` — GeoMap-spezifischer Arbeitsplan mit Checkliste, Verify-Gates, SOTA-Backlog
- `graph_execution_delta.md` — Graph-spezifischer Ausfuehrungsslice (Contracts, Runtime, Verify)
- `backend_geomap_delta.md` — GeoMap-Backend-spezifischer Ausfuehrungsslice (API/Store/Policy/Audit)
- `control_surface_delta.md` — Control-Surface-Execution-Slice (Ops/Runtime-Layer, Two-Tier-Mode, RBAC/Approval/Audit)
- `document_widgets_control_delta.md` — Dokument-Widget-/Control-Surface-Execution-Slice fuer Files-/Widget-Interaktionspfade
- `root_geo_references_coverage.md` — Vollabdeckungsmatrix fuer Root/Geo/References
- `agent_memory_context_delta.md` — Agent-/Memory-/Context-Runtime-Delta
- `agent_security_runtime_delta.md` — Agent-Security-Runtime-Boundary-Delta
- `agent_harness_runtime_delta.md` — Agent-Harness-/Sandbox-/Guardrail-Runtime-Delta
- `agent_backend_program_delta.md` — programmweiter Agent-Backend-Owner fuer Contracts/Policy/Audit/Degradation + reference-adoption
- `agent_geomap_bridge_delta.md` — schlanker Bridge-Slice fuer Agent<->GeoMap Contracts (Policy/Audit/Failure)
- `claim_verification_delta.md` — Claim-/Evidence-/Contradiction-Delta
- `uil_candidate_promotion_delta.md` — UIL-/Candidate-/Promotion-Delta
- `domain_intelligence_delta.md` — Game-Theory/Entropy/Political-Economy-Delta
- `references_projects_evaluate_delta.md` — References-Projects Evaluate-/Decision-Delta
- `rust_kand_evaluation_delta.md` — expliziter Bewertungs-Slice fuer `Kand` als Rust-Core-Basis
- `frontend_refinement_perf_delta.md` — Frontend-Refinement-/Performance-Delta
- `frontend_enhancement_delta.md` — Frontend-Enhancement-Delta (TS/Errors/Execution-Policies)
- `frontend_context_delta.md` — Frontend-Context-/Surface-Schnitt-Delta fuer Context-Assembly und UI-Integration
- `frontend_intelligence_calendar_delta.md` — Frontend-Execution-Slice fuer Intelligence-Calendar Surface
- `frontend_research_home_delta.md` — Frontend-Execution-Slice fuer Research-Home Surface
- `command_keyboard_delta.md` — Command-/Keyboard-Execution-Slice fuer globale Shortcuts und Command-Palette-Routing
- `indicator_delta.md` — dedizierter Indicator-Execution-Slice fuer Frontend-/Runtime-Integration und Verify-Gates
- `python_runtime_eval_delta.md` — Python-Runtime-Evaluation-Slice fuer Eval-/Betriebsgrenzen und Qualitaetsgates
- `ecosystem_optionality_delta.md` — Plugin-/Partner-/Payment-/Rollout-Delta
- `future_quant_advanced_architecture_delta.md` — Future-Quant-/Advanced-Architecture Trigger-Delta
- `platform_dx_quality_delta.md` — Platform-DX-/Quality-/Supply-Chain-Delta

Phase 25/26 sind bewusst als **trigger-basierte Optionsphasen** definiert:

- kein Start ohne nachgewiesenen Trigger (siehe `FQAA*`)
- keine direkte Prioritaet vor offenen Verify-/Hardening-Gates der Phasen 1-24

Weitere domain-spezifische Execution-Specs koennen bei Bedarf angelegt werden.

---

## 7. Root-Docs nach dem Refresh

| Cluster | Fuehrende Root-Dokumente |
|:--------|:-------------------------|
| Root-Architektur | `GO_GATEWAY.md`, `README.md` |
| Agent / Knowledge | `AGENT_ARCHITECTURE.md`, `AGENTS_BACKEND.md`, `AGENT_TOOLS.md`, `AGENT_CODE_MODE.md`, `AGENT_SECURITY.md`, `AGENT_HARNESS.md`, `MEMORY_ARCHITECTURE.md`, `CONTEXT_ENGINEERING.md`, `RAG_GRAPHRAG_STRATEGY_2026.md`, `archive/KG_MERGE_AND_OVERLAY_ARCHITECTURE.md`, `CLAIM_VERIFICATION_ARCHITECTURE.md` |
| Geo / Map | `geo/GEOMAP_OVERVIEW.md`, `geo/GEOMAP_PRODUCT_AND_POLICY.md`, `geo/GEOMAP_MODULE_CATALOG.md`, `geo/GEOMAP_VERIFY_GATES.md` |
| Compute / Domain | `INDICATOR_ARCHITECTURE.md`, `RUST_LANGUAGE_IMPLEMENTATION.md`, `Portfolio-architecture.md`, `GAME_THEORY.md` |
| Gateway / Provider | `GO_GATEWAY.md`, `gct-gateway-connections.md`, `go-research-financial-data-aggregation-2025-2026.md`, `references/status.md`, `REFERENCE_SOURCE_STATUS.md` |
| Reference / benchmark / archive | ueber `docs/README.md` und `docs/archive/` klassifiziert |

### Zusatz-Kontext fuer CLI-Agents (optional, mit Vorsicht)

- `docs/archive/` darf fuer tieferen Verlaufskontext gelesen werden, ist aber
  potenziell **outdated** und nie primaere Normquelle.
- `docs/books/` enthaelt tiefe Referenzen mit teils sehr grossen Dateien; nur
  gezielt und abschnittsweise lesen, nicht als first-read fuer operative Arbeit.
- Normative Reihenfolge bleibt: `docs/specs/*.md` -> `docs/specs/execution/*.md`
  -> Root-Owner-Dokumente -> optional `archive/books`.

---

## 8. Naechste Architektur- und Delivery-Slices

1. Provider-Credential-Transport von `finnhub` und `fred` auf weitere sinnvolle read-only
   Provider ausrollen.
2. Mehr read-only GCT-/Gateway-Slices auf dieselbe neutrale `MarketTarget`-
   Vertragsgrenze heben.
3. `docs/references/` als Pflicht-Begleitstruktur fuer Provider-, Quellen- und
   Evaluationsarbeit weiter vervollstaendigen.
4. Coverage-Matrix (`execution/root_geo_references_coverage.md`) laufend pflegen,
   so dass keine Root-/Geo-/References-MD ohne COV-Owner bleibt.
5. Agent-/Claim-/UIL-/Domain-Execution-Specs ueber ihre Verify-Gates schliessen.
6. Compute-Grenze Go↔Rust konkretisieren, ohne Python als Research-/Agent-
   Schicht zu entwerten.
7. Offene Verify-Gates systematisch schliessen, bevor neue grosse Themenflaechen
   aufgemacht werden.
8. Future-Quant- und Advanced-Architecture-Themen nur trigger- und evidence-basiert
   ueber `execution/future_quant_advanced_architecture_delta.md` in aktive Phasen heben.
9. Knowledgebase-nahe Root-Docs (`POLITICAL_ECONOMY_KNOWLEDGE.md`, `ENTROPY_NOVELTY.md`) primaer ueber Memory/KG und erst danach ueber Domain-Signalpfade operationalisieren.
10. Platform-DX-/Quality-Hardening (`execution/platform_dx_quality_delta.md`) mit
    Setup-, Hook-, Test- und Security-Gates evidence-basiert schliessen.
11. Trading-Page God-Component aufloesen: URL-Routing `/trading`, 10 Custom Hooks,
    Zustand Store, TanStack Query Wiring — vollstaendiger Plan in
    `execution/trading_page_refactor_delta.md` (Audit: `docs/trading_page_audit.md`).

---

## 9. Aenderungsregel

Bei kuenftigen Updates gilt:

- Statusaenderungen zuerst in den fuehrenden Minis und Fachdokumenten abgleichen
- danach `SYSTEM_STATE.md` und `EXECUTION_PLAN.md` synchronisieren
- historische Detailerzaehlungen nur noch in Archiv-/Ledger-Dokumente schreiben

---

## 10. Konsolidierungs-Closeout (strikt-vollstaendig)

Fuer die aktuelle Konsolidierungsrunde ist die Arbeitsreihenfolge verbindlich:

1. Restkontext aus Bridge-/Master-Docs in aktive Owner-Dokumente transferieren.
2. Root-Read-Order und Owner-Matrix aktualisieren.
3. Erst danach Bridge-/Master-Docs als archiviert markieren und in
   `docs/archive/` fuehren.

Transferstatus dieser Runde:

- Service-/Objekt-/Retrieval-/Simulation-Vertragsrest in `ARCHITECTURE.md`
  uebernommen.
- Striktes Archivkriterium in `DOCUMENTATION_ARCHITECTURE.md` verankert.
- Root-Klassifikation in `README.md` und Clusterliste in `EXECUTION_PLAN.md`
  auf archivierte Master-Docs umgestellt.

