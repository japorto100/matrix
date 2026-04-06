# GO GATEWAY — Integration & Optionen

> **Stand:** 07. März 2026  
> **Zweck:** Integrationsleitfaden für Go Gateway mit Frontend, Python/Rust-Services und Agent-Tooling.  
> **Maßgebliche Statusquellen:** `docs/specs/SYSTEM_STATE.md`, `docs/specs/EXECUTION_PLAN.md`  
> **Auth-Referenz:** `docs/specs/AUTH_SECURITY.md` (Umbrella) und
> `docs/specs/security/POLICY_GUARDRAILS.md` fuer Agent-/MCP-
> Sicherheitsanforderungen

---

## 1. Frontend-Integration (RSC + Client Components)

### Einordnung

Next.js 16 nutzt React Server Components (RSC) by default, aber im Trading-Kontext bleibt der Haupt-Workspace bewusst **Client-first** (Charting, Interaktionen, Streaming-Events).

### Aktueller Architekturrahmen

| Aspekt | Richtung |
|:---|:---|
| **Boundary** | Frontend spricht für Domain-Daten primär Go Gateway an (`/api/*` Next routes als BFF/Thin-Proxy). |
| **Realtime** | Market Streaming über Go-SSE (`stream-first`, REST-Fallback kontrolliert/gated). |
| **Client-First Bereiche** | Trading Workspace / Chart / Interactive Tooling bleiben Client Components. |
| **RSC-Einsatz** | Selektiv für initiale, read-heavy Flächen (z. B. erste Sidebar-/Summary-Daten), nicht als Dogma für alle Trading-Seiten. |

### RSC mit Go Gateway (wenn genutzt)

| Aspekt | Details |
|:---|:---|
| **Aufruf** | RSC kann Go Gateway per `fetch()` indirekt über Next-APIs oder direkt über Gateway-URL konsumieren. |
| **Auth** | Session-/Header-Weitergabe bleibt verpflichtend (Request-ID, Rolle/JWT je nach Pfad). |
| **Caching** | Für Markt-/Live-Daten standardmäßig `cache: "no-store"` oder explizite Revalidation-Strategie. |
| **Fehlerbild** | Error Boundaries + degradationsfähige API-Antworten statt stiller Fallbacks. |

### Wichtig

Go Gateway benötigt für RSC **keine Sonder-API**, sondern konsistente Auth-/Header-/Contract-Konformität auf denselben REST-Endpunkten.

---

## 1b. Provider-Expansion-Methodik (GCT-inspirierte Patterns)

> **Kontext:** Die Expansion folgt der eingeführten BaseConnector-/Adaptive-Router-Struktur. GCT wird als Robustheits-Referenz genutzt, nicht als universelles Domänenmodell für Nicht-Crypto-Quellen.

### Prinzipien

- **GCT als Pattern-Referenz**, nicht als Domain-Zwang für Macro/Geo/Legal
- **`finnhub-go` nur selektiv als Referenz**, nicht als automatischer Ersatz des eigenen Connectors; Re-Open nur bei klarer Coverage-Luecke oder Wartungsvorteil
- **Router-Metadaten (`group`, `kind`, `capabilities`)** in `go-backend/config/provider-router.yaml`
- **Capability-Matrix** pro Provider statt monolithischer Interfaces
- **Fehlerklassen** für Retry/Circuit/Fallback-Entscheidungen
- **Contract-first + gruppenweise Rollouts** (kein ad hoc Connector-Wachstum)

### Stand (März 2026)

- Base-Layer etabliert:  
  `internal/connectors/base/capabilities.go`  
  `internal/connectors/base/error_classification.go`  
  `internal/connectors/base/sdmx_client.go`  
  `internal/connectors/base/timeseries.go`  
  `internal/connectors/base/bulk_fetcher.go`  
  `internal/connectors/base/rss_client.go`  
  `internal/connectors/base/diff_watcher.go`  
  `internal/connectors/base/translation.go`  
  `internal/connectors/base/oracle_client.go`
- Priorisierte Bestands-HTTP-Connectoren sind auf gemeinsamer Base-Architektur konsolidiert.
- G4-/G3-nahe Makro-Routen sind vertikal verdrahtet über `market.NewRoutedMacroClient(...)` + Prefix-Registry.
- Prefix-Routing ist produktiv relevant (u. a. `BCB_SGS_*`, `BANXICO_*`, `BOK_ECOS_*`, `BCRA_*`, `TCMB_EVDS_*`, `RBI_DBIE_FXRES_*`, `IMF_IFS_*`, `OECD_*`, `WB_WDI_*`, `UN_*`, `ADB_*`, `OFR_*`, `NYFED_*`).

### Roadmap-Reihenfolge (weiter gültig)

1. **G4 + produktnahe Makro-Quellen** stabilisieren  
2. **G3 SDMX** weiter ausbauen (shared client, keine Einzellösungen)  
3. **G5/G6/G7** (Bulk/RSS/Diff) für Geo/Legal-Coverage  
4. **G8/G9/G10** gezielt nach Produktbedarf/Lizenz/Freigaben

### Go ↔ Python IPC

Proto liegt unter `go-backend/internal/proto/ipc/ipc.proto` (`ForwardRequest` RPC).  
Python-Services unterstützen optional gRPC (`GRPC_ENABLED=1`) mit Port-Konvention HTTP+1000.

### Weitere stabile Defaults

- **Adaptive Router-Logik** bleibt Go-owned:
  Asset-Class-Routing, Health-/Fallback-Entscheidungen und Provider-Metadaten
  gehoeren in den Gateway-Layer, nicht in zufaellige Frontend- oder Python-
  Umwege.
- **BaseConnector statt Copy/Paste-Connectoren**:
  gemeinsame HTTP-/Retry-/Rate-Limit-/Error-Class-Bausteine bleiben die
  Default-Richtung fuer neue strukturierte Datenquellen.
- **Quellen-Gruppen statt 1:1-Sonderfaelle**:
  REST, SDMX, Time-Series, Bulk, RSS, Diff, Translation und Oracle-/Cross-Check-
  Quellen werden gruppenweise ausgebaut, nicht als unverbundene Einzel-Clients.
- **Symbol-/Prefix-Kataloge** bleiben Gateway-nah:
  Symbol-Mapping, Prefix-Routing und spaetere Symbol-Katalog-Services gehoeren an
  dieselbe Boundary wie Routing und Provider-Capabilities.

## 1c. Streaming-Leitbild fuer Browser-nahe Marktpfade

Die operative Streaming-Richtung bleibt:

1. **Ingestion**  
   Provider-Feeds und interne Stream-Quellen normalisieren Events/Ticks auf
   Gateway-nahe Markt- und Symbolgrenzen.
2. **Processing**  
   Candle-/Depth-/Alert-Logik arbeitet auf normalisierten Events, inklusive
   Dedupe, Sortierung, Retry-/Reconnect-Folgen und spaeter Replay/Recovery.
3. **Delivery**  
   Browser-nahe Clients konsumieren standardmaessig **SSE/stream-first**; REST
   bleibt Recovery-, Snapshot- und Fallback-Pfad.

Arbeitsregeln:

- **REST + SSE** bleibt der Browser-Default; WebTransport ist Beobachtungsthema,
  nicht Primärpfad.
- **Stream-first, REST-fallback** bedeutet nicht "zwei gleichberechtigte
  Wahrheiten", sondern: Streams fuer Live-Aktualitaet, REST fuer Recovery,
  Bootstrap und kontrollierte Degradation.
- Interne Bus-/Queue-Loesungen (spaeter z. B. NATS) koennen die Processing-
  Strecke erweitern, sind aber keine Voraussetzung fuer die erste saubere
  Streaming-Grenze.
  **Aladdin-Gap (Streaming):** NATS JetStream für Ingestion, SSE/WebSocket für Delivery. OSS: gorilla/websocket, SSE (Go stdlib). Architektur-Komponenten: ws-ingestor, candle-aggregator, alert-engine (ADR-001). Priorität: Hoch.

Hardening-Schwerpunkte:

- out-of-order / verspätete Events duerfen Candle- und Orderbook-Grenzen nicht
  still korrumpieren
- reconnect/replay braucht Dedupe- und Checkpoint-Semantik
- Provider-Limits, Disconnect-Verhalten und Heartbeats muessen pro Quelle klar
  klassifiziert sein
- SSE-Fehlerpfade duerfen nicht in stilles Frontend-Polling "umkippen"

---

## 2. MCP / WebMCP / Agent-Tools

### Einordnung

MCP/WebMCP ist **nicht mehr nur theoretisch optional**, sondern bereits als Agent-Tooling-Richtung im System verankert (policy-/capability-gated Pfade über Go).

### Leitplanken für Tools

| Tool-Typ | Beispiele | Sensibilität |
|:---|:---|:---|
| **Read-Only** | Quote, OHLCV, News, Geo-Kontext | Niedrig bis mittel |
| **Portfolio/Account-nah** | Portfolio Summary, Positionen | Hoch |
| **Mutationen** | Chart-/State-Mutationen (agentisch) | Hoch (nur mit Policy + Confirm) |
| **Execution/Orders** | Order Submit/Cancel | **Kritisch** (nicht als frei aufrufbares Agent-Tool) |

### Warum „by default unsicher“ weiter gilt

- Tool-Exposition ohne starken Auth-Layer ist riskant
- Ohne RBAC/Rate-Limits/Audit entsteht direkter Missbrauchspfad
- Agent-Tooling muss wie API-Produktionssurface behandelt werden

### Mindestanforderungen (verpflichtend)

Siehe `docs/specs/AUTH_SECURITY.md`. Kurzfassung:

- Tool-Pfade über Go Gateway zentral absichern
- JWT/Session-validierte Aufrufe, rollenbasiert
- Capability-Checks pro Tool
- Harte Rate-Limits pro Session/User/Toolklasse
- Audit-Trail (wer, wann, welches Tool, welcher Kontext)
- Mutationen nur mit expliziter Governance (Policy + Confirm-Flow)

### Empfehlung

- **Read-first Agent-Tools** weiter ausbauen
- **Mutationen eng begrenzen** und policy-gated betreiben
- **Keine direkte Trading-Execution als offenes Agent-Tool**

---

## 3. Weitere Optionen

### WebTransport (QUIC/HTTP3)

- **Status:** Beobachten; noch kein Primärpfad.
- **Vorteil:** Multiplexing, keine klassischen HOL-Blockaden.
- **Aktuelle Priorität:** Niedriger als REST+SSE-Härtung.

### gRPC-Web

- **Status:** Möglich, aber derzeit nicht priorisiert.
- **Vorteil:** Binär, effizient bei passenden Workloads.
- **Nachteil:** Zusätzliche Browser-/Infra-Komplexität.
- **Empfehlung:** REST + SSE bleibt Standard für Frontend-Pfade.

### GraphQL

- **Status:** Nicht geplant.
- **Begründung:** Contract-first REST-Fläche ist überschaubar und ausreichend.

---

## 4. Was bleibt konstant

1. Go Gateway ist Single Entry Point für Kern-Domainpfade.  
2. REST + SSE ist der Default für Browser-nahe Flows.  
3. Provider-Expansion bleibt contract-first, gruppenweise und capability-basiert.  
4. Security-Enforcement (Auth/RBAC/RateLimit/Audit) ist nicht optional, sondern Plattformstandard.  
