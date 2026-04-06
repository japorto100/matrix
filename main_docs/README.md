# Fusion Docs Index

> **Stand:** 09. Maerz 2026
> **Zweck:** Einstiegspunkt fuer Menschen und Agenten in die aktive
> Dokumentationsoberflaeche. Root-Docs sind hier bewusst nach Rolle klassifiziert,
> damit offene Arbeit, normative Architektur und historisches Material nicht mehr
> vermischt werden.

---

## 1. Zuerst lesen

| Dokument | Rolle |
|:---------|:------|
| `docs/specs/EXECUTION_PLAN.md` | aktive Roadmap, Phasenstatus, offene Verify-Gates |
| `docs/specs/SYSTEM_STATE.md` | kompakte IST/SOLL-Wahrheit |
| `docs/specs/API_CONTRACTS.md` | Index; Details in `api/` (Boundary- und Transport-Contracts) |
| `docs/specs/AUTH_SECURITY.md` | Index; Details in `security/` (Auth-, Policy-, Secrets-Authority) |
| `docs/specs/FRONTEND_ARCHITECTURE.md` | Frontend-/BFF-/State-Authority |

### Arbeitsregel

- Specs muessen **laufend aktuell gehalten** werden.
- Historische Fortschritte gehoeren in Archive/Ledger, nicht in aktive
  Master-Specs.
- Root-Docs duplizieren keine Spezifikationen, sondern ergaenzen sie fachlich.

---

## 2. Root-Docs mit `active` Rolle

| Dokument | Kurzrolle |
|:---------|:----------|
| `GO_GATEWAY.md` | Gateway-Integration, Provider-/Tool-/Boundary-Perspektive |
| `gct-gateway-connections.md` | verdichtete Arbeitsreferenz fuer GCT-Absorption / Gateway-Grenze |
| `specs/geo/GEOMAP_OVERVIEW.md` | GeoMap-Masterdokument |
| `specs/geo/GEOMAP_MODULE_CATALOG.md` | GeoMap-Modul-/Optionskatalog |
| `INDICATOR_ARCHITECTURE.md` | Compute-/Indikatorfachdokument |
| `RUST_LANGUAGE_IMPLEMENTATION.md` | Rust-Placement und Compute-Implementation |
| `Portfolio-architecture.md` | Portfolio-/Analytics-Fachdokument |
| `UNIFIED_INGESTION_LAYER.md` | UIL-/Candidate-/promotion-Fachdokument |
| `MEMORY_ARCHITECTURE.md` | Memory-/KG-/semantic-memory-Fachdokument |
| `CONTEXT_ENGINEERING.md` | retrieval-/context-assembly-Fachdokument |
| `AGENT_ARCHITECTURE.md` | Agent-Rollen, Orchestrierung, Laufzeit |
| `AGENT_TOOLS.md` | Tooling-/Capability-/WebMCP-/Browser-Fachdokument |
| `AGENT_CODE_MODE.md` | evaluate-only Owner fuer optionales code-mode Runtime-Pattern |
| `archive/KG_MERGE_AND_OVERLAY_ARCHITECTURE.md` | archivierte Merge-/Overlay-Referenz (Normen in aktive Docs verteilt) |
| `CLAIM_VERIFICATION_ARCHITECTURE.md` | claim/evidence/belief pipeline |
| `GAME_THEORY.md` | Simulation-/game-theory-/control-theory-Fachdokument |
| `specs/geo/GEOMAP_FOUNDATION.md` | GeoMap Basemap, Geocoding, PMTiles, Rendering (konsolidiert) |
| `specs/geo/GEOMAP_VERIFY_GATES.md` | GeoMap E2E-Abnahme, Draw-Workflow, Performance-Baseline |
| `references/status.md` | aktive Quellen-/provider-status-Matrix |
| `FRONTEND_COMPONENTS.md` | UI-surface-/component-Fachdokument |

---

## 3. Root-Docs mit `reference` Rolle

| Dokument | Warum Referenz, nicht Root-Authority |
|:---------|:-------------------------------------|
| `Advanced-architecture-for-the-future.md` | Langfrist-Radar, nicht aktuelle Verfassung |
| `ENTROPY_NOVELTY.md` | wichtige Theorie- und Signalreferenz, aber kein Master-Owner |
| `POLITICAL_ECONOMY_KNOWLEDGE.md` | Domain-Seed / KG-Futter |
| `FRONTEND_DESIGN_TOOLING.md` | UI-/tooling-Referenz statt Architektur-Owner |
| `Future-Quant-trading.md` | Zukunfts-/Ideensammlung |
| `REFERENCE_PROJECTS.md` | externer Referenzindex |
| `references/README.md` | verteilter Referenzkatalog (Projekte, Libraries, Quellen) |
| `SUPERAPP.md` | strategische Referenz, nicht aktiver Architektur-Owner |
| `web3/README.md` | Web3-Layer-Index (Oracles, DeFi, Wallet) – SOTA 2026 |
| `REMOTE_DEV_SETUP.md` | Setup-/Betriebsreferenz |
| `archive/KG_ONTOLOGY.md` | formale Ontologie-Referenz (archiviert) |
| `ADR-001-streaming-architecture.md` | fokussierte ADR fuer Streaming |

---

## 4. Root-Docs mit `bridge / superseded-reference` Rolle

Diese Dateien bleiben zunaechst erhalten, sind aber **nicht** mehr gleichrangige
aktive Verfassung.

| Dokument | Status |
|:---------|:-------|
| `archive/ai_retrieval_knowledge_infra_full.md` | Retrieval-/Discovery-Quelle (archiviert) |
| `MRKTEDGE.AI-deep research chatgptp2.md` | verfeinerter externer Benchmark, historisch/reference |
| `REFERENCE_SOURCE_STATUS.md` | Root-Bridge zur kanonischen Matrix unter `docs/references/status.md` |

---

## 5. Root-Docs mit `archived / operational note` Rolle

Diese Dokumente bleiben nur noch als bewusst markierte Alt-/Arbeitsreferenz
sichtbar und sollen nicht mehr als aktive Architekturquelle gelesen werden.

| Dokument | Status |
|:---------|:-------|
| `archive/Master_master_architecture_2026_IMPORTANT.md` | ehemals normative Gesamtsynthese; Inhalte in aktive Specs/Root-Docs transferiert |
| `archive/Master_master_diff_merge_matrix.md` | ehemals Verteil-/Konsolidierungsmatrix; historischer Audit-Trace |
| `archive/MASTER_ARCHITECTURE_SYNTHESIS_2026.md` | ehemals Bridge-/Vorlagedokument; historischer Rationale-Snapshot |
| `ALADDIN-INSIGHTS-FROM-GEMINI-RESEARCH.md` | Aladdin-Benchmark-Inhalte auf Root-MDs verteilt. Archiv: `docs/archive/ALADDIN-INSIGHTS-FROM-GEMINI-RESEARCH.md` |
| `TOOL_SEARCH.md` | externe Tool-Feature-Notiz, keine Projektverfassung |
| `archive/MRKTEDGE.AI-deep research chatgpt.md` | archivierte erste MRKTEDGE-Benchmarkfassung |
| `Deep_research_addition_palantir.md` | nach Extraktion in `docs/archive/Deep_research_addition_palantir.md` archiviert |
| `archive/webapp.md` | archivierte operative Frontend-Arbeitsnotiz |

Historische und ausgezogene Inhalte liegen unter `docs/archive/`.

---

## 6. Aktuelle Fusion-/Ablösekandidaten

| Kandidat | Zielrichtung |
|:---------|:-------------|
| `MRKTEDGE.AI-deep research chatgptp2.md` | als einzige aktive MRKTEDGE-Benchmark-Referenz behalten; Altfassung liegt im Archiv |
| *(erledigt)* | `specs/geo/GEOMAP_FOUNDATION.md` konsolidiert BASEMAP_POLICY, GEOCODING_STRATEGY, PMTILES_CONTRACT, ADR-002 |
| *(erledigt)* | `ai_retrieval_knowledge_infra_full.md` in `archive/` verschoben und in aktive Docs verteilt |
| *(erledigt)* | `Master_master_architecture_2026_IMPORTANT.md`, `Master_master_diff_merge_matrix.md`, `MASTER_ARCHITECTURE_SYNTHESIS_2026.md` nach strikt-vollstaendigem Transfer archiviert |
| `TOOL_SEARCH.md` | nach Tool-/Agent-Runtime-Verteilung langfristig aus Root entfernen oder enger verdichten |

---

## 7. Specs

| Datei | Rolle |
|:------|:------|
| `docs/specs/EXECUTION_PLAN.md` | Roadmap / offene Arbeit |
| `docs/specs/SYSTEM_STATE.md` | IST/SOLL Truth |
| `docs/specs/API_CONTRACTS.md` | Index; Details in `api/` |
| `docs/specs/AUTH_SECURITY.md` | Index; Details in `security/` |
| `docs/specs/FRONTEND_ARCHITECTURE.md` | frontend ownership |
| `docs/specs/ARCHITECTURE.md` | technische Zielarchitektur |
| `docs/specs/DOCUMENTATION_ARCHITECTURE.md` | Ebenen, Read Order, Split-Regeln |
| `docs/specs/execution/cross_cutting_verify.md` | offene Verify-Checkliste |
| `docs/specs/execution/compute_delta.md` | compute delta |
| `docs/specs/execution/infra_provider_delta.md` | infra/provider delta |
| `docs/specs/execution/source_onboarding_and_keys.md` | Quellen-/Key-Onboarding |
| `docs/specs/execution/geomap_closeout.md` | GeoMap closeout |

---

## 8. Archive

| Ort | Rolle |
|:----|:------|
| `docs/archive/` | historische Ledger, abgeschlossene Arbeitsdokumente, fruehere Planstaende |
| `docs/archive/EXECUTION_PLAN_HISTORY.md` | ausgelagerte Masterplan-Historie |

---

## 9. Fuer Agenten

1. Starte mit den `docs/specs/*.md` Sources of Truth.
2. Lies danach nur die thematisch fuehrenden Root-Docs.
3. Verwende `bridge / superseded-reference` Docs nur dann, wenn du fehlende
   Herleitung oder Kontext brauchst.
4. Nutze `archived / operational note` Docs nicht als normative Quelle.
