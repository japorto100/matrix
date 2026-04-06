# FRONTEND ARCHITECTURE

> **Stand:** 16. Maerz 2026 (Rev. 3 — Shell-Refactor, Control/Files/AgentChat-Surfaces ergaenzt)
> **Zweck:** Frontend-Authority fuer Next.js/BFF-Boundaries, Shell-Architektur,
> State-Schichten, UI-Ownership und die aktuelle Rolle des Browsers.
> **Nicht dieses Dokuments:** Vollstaendige Roadmap, historische Bugchronik oder
> Backend-Changelog.

---

## 1. Frontend-Leitformel

Das Frontend ist eine **lokale User-Intelligence-Surface** auf Basis von Next.js 16,
aber **nicht** die zweite Domain-Truth des Systems.

- Browser spricht Next.js
- Next.js spricht fuer Domainpfade Go
- React bleibt interaktiv und client-first dort, wo Charting, Streaming und
  Workspace-Interaktion dominieren
- Domain- und Provider-Logik wandert nicht zurueck in `src/lib/providers`

---

## 2. Tech Stack

| Bereich | Aktueller Stand |
|:--------|:----------------|
| Framework | Next.js `^16.1.1` App Router |
| React | `^19.0.0` |
| Styling | Tailwind 4 + shadcn/ui + Framer Motion |
| Theming | `next-themes` — 4 Themes: `light`, `dark`, `blue-dark`, `green-dark`; Theme-Picker in TradingHeader + CommandPalette |
| Charts | **Strategie (21. Maerz 2026):** `lightweight-charts` 5.x (Financial Time Series: Candles, Equity, Drawdown, Rolling Metrics), `recharts` (NUR Grouped/Stacked Bar Comparisons), `ChartGPU` (Scatter/Efficient Frontier, Heatmap/Korrelation, Pie/Donut — wenn benoetigt, WebGPU-only, v0.3.x noch nicht installiert), `d3-geo` + d3-geo-voronoi + d3-inertia (GeoMap). `@nivo/heatmap` verworfen — ChartGPU uebernimmt Korrelationsmatrix. |
| Server State | TanStack Query `^5.82.0` |
| Table | TanStack Table `^8.21.3` |
| Virtualization | TanStack Virtual `^3.13.21` |
| Throttling | TanStack Pacer `^0.20.0` |
| Local/domain state | React state + Zustand `^5.0.6` (`tradingWorkspaceStore`, `geopoliticalMapStore`) |
| Auth | Auth.js / next-auth v5 beta; Passkey-Support aktiv |
| Validation | Zod vorhanden; breiterer Contract-Einsatz Folgearbeit (FE2) |

### Caching / Fetching Default

- Server-seitig: Next.js `"use cache"` dort, wo Daten wirklich cachebar sind
- Client-seitig: TanStack Query fuer polling, cache invalidation und SSE-nahe Datenaktualisierung
- Streaming- und Live-Market-Pfade bleiben standardmaessig `no-store` bzw. stream-first

---

## 3. Shell-Architektur (Route Group `(shell)`)

Alle primaeren Workspaces laufen durch eine gemeinsame Shell (`app/(shell)/layout.tsx`):

```tsx
// app/(shell)/layout.tsx
<GlobalChatProvider>
  <div className="flex h-screen flex-col overflow-hidden">
    <GlobalTopBar />
    <GlobalKeyboardProvider />
    <GlobalChatOverlay />
    <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
  </div>
</GlobalChatProvider>
```

Die Shell stellt bereit:

| Komponente | Rolle |
|:-----------|:------|
| `GlobalChatProvider` | Agent-Chat-Kontext fuer alle Shell-Surfaces |
| `GlobalTopBar` | oberste App-Navigation, immer sichtbar |
| `GlobalKeyboardProvider` | globale Keyboard-Shortcuts fuer alle Surfaces |
| `GlobalChatOverlay` | Agent-Chat-Panel als Overlay ueber allen Workspaces |

**Konsequenz:** `(shell)` ist eine Architektur-Grenze. Pages ausserhalb der Shell
(z.B. `/auth/*`) erhalten diese globalen Dienste nicht.

---

## 4. Frontend-Boundaries

### Browser -> Next.js

- alle User-Interaktionen laufen ueber Pages, Server Components, Client
  Components, Route Handlers oder Server Actions
- keine direkten Browser-Calls an Go, Python oder externe Market-Provider

### Next.js -> Go Gateway

- `api/v1/*`, `api/market/*`, `api/fusion/*`, `api/geopolitical/*`, `api/memory/*`
  und weitere Domainpfade bleiben BFF-/Thin-Proxy-Flaechen
- Route-Handler duplizieren keine Policy-, Routing- oder Provider-Logik

### Verbotene Rueckfaelle

- kein direkter Datenzugriff aus dem Browser auf `lib/providers`
- keine stillen Frontend-Provider-Fallbacks, wenn Go oder Downstreams fehlschlagen
- keine dauerhafte Ablage produktiver Provider-Secrets im Browser als einzige Wahrheit

---

## 5. Auth- und Credential-Modell im Frontend

### Session / Identity

- Auth.js / next-auth v5 beta ist aktiv
- Passkey-Support aktiv (`auth/passkeys/*`, `lib/auth/passkey-client.ts`)
- Security-/Session-/Passkey-Flows leben im Frontend und Auth-Layer, nicht in
  Domain-BFF-Routen

### Provider-Credentials fuer Market-Pfade

- lokale UI-Eingabe fuer read-only Provider-Keys bleibt fuer UX erlaubt
- `SettingsPanel` synchronisiert diese Keys in einen serverlesbaren, kontrolliert
  gesetzten Cookie fuer Next-Market-Routen
- Next.js rekonstruiert daraus den Gateway-Header `X-Tradeview-Provider-Credentials`
- Browser bleibt **nicht** der direkte Upstream fuer echte Provider-API Calls

### KG-Encryption

- `lib/kg/encrypted-indexeddb.ts` — clientseitiger KG-Zugriff ist verschluesselt
  (IndexedDB + Encryption Key, der ueber `/api/auth/kg/encryption-key` bereitgestellt wird)

---

## 6. State-Schichten

| Schicht | Typische Inhalte | Owner |
|:--------|:-----------------|:------|
| UI-local state | Drawer offen/zu, Tabs, Eingabefelder, Chart-Interaktionen | React local state |
| Domain workspace state | `tradingWorkspaceStore`: `currentSymbol`, `favorites`, `layout`; `geopoliticalMapStore`: drawing mode, viewport, events | Zustand |
| Agent-Chat state | Chat history, active session, tool events | `GlobalChatProvider` / `features/agent-chat/context/` |
| Server state | Quotes (OHLCV), Orderbook-Snapshots, portfolio analytics, composite signals, memory status | TanStack Query |
| Live stream state | Candle-Updates, Orderbook-Updates via SSE → `queryClient.setQueryData` | `useMarketStream`, `useOrderbookStream` |
| Persistence / preferences | profile keys, settings, lokale UX-Praeferenzen, Favorites, Layout | `lib/storage` + Browser |

### Regel

- Query-/server state nicht in ad hoc `useEffect`-Ketten vergraben
- Workspace- und UI-State nicht in den BFF-Routen verstecken
- echte Domain-Truth nicht im Client simulieren

---

## 7. Struktur und Ownership

### Aktiver Zuschnitt

```text
src/
  app/              Next.js app + BFF/API layer
    (shell)/        Shell Route Group: trading, geopolitical-map, control, files
    auth/           Auth surfaces (ausserhalb Shell)
    api/            BFF Route Handlers
  chart/            Chart engine and rendering-specific logic (drawing/, engine/)
  components/       Shared UI: GlobalTopBar, GlobalChatOverlay, CommandPalette,
                    SettingsPanel, trading-chart/, fusion/, ui/
  data/             Shared data helpers (marketData.ts, providers/)
  features/         Domain surfaces (pro Feature isoliert)
  hooks/            Global shared hooks (use-mobile, use-toast)
  lib/              Shared browser/server helpers
  state/            (Placeholder — aktuell noch leer)
  types/            Global type shims (d3, world-atlas etc.)
```

### Features-Ownership

| Feature | Inhalt | Anmerkung |
|:--------|:-------|:----------|
| `features/trading/` | Trading workspace, Panels, Hooks, `tradingWorkspaceStore` | TRF1–TRF42 erledigt (10.03.2026) |
| `features/geopolitical/` | GeoMap workspace, rendering, shell, timeline, Phase12 | weiter splitting sinnvoll |
| `features/agent-chat/` | AgentChatPanel, GlobalChatContext, Hooks, Components | cross-cutting ueber Shell-Surfaces |
| `features/control/` | ControlPage, Agent/Session/Skill/Eval-Views, Hooks | neuer Admin/Debug-Workspace |
| `features/files/` | FilesPage, File Upload/Search/Reindex, Hooks | UIL-Upload-Surface |
| `features/memory/` | MemoryStatusBadge | Memory-UI-Statusanzeige |
| `features/auth/` | Auth UI-Komponenten | Login, Register, Passkeys |

### Lib-Schichten

| Schicht | Inhalt |
|:--------|:-------|
| `lib/server/*` | server-only helpers fuer Route Handler und Stores (Prisma, Geopolitical Stores, Orders, Portfolio, Passkeys, Credentials, Audit) |
| `lib/agent/` | `frontend-tools.ts` — Werkzeugdefinitionen fuer den Frontend-Agent |
| `lib/auth/` | Passkey-Client, Runtime-Flags |
| `lib/geopolitical/` | Validation, Dedup, Confidence, Drawing-Primitives, Ingestion-Contracts, Types |
| `lib/kg/` | `encrypted-indexeddb.ts` — clientseitiger verschluesselter KG-Zugriff |
| `lib/memory/` | `kg-wasm-client.ts` — KuzuDB WASM-Client fuer Browser-KG |
| `lib/orders/` | Portfolio, Risk, Snapshot-Service, Types |
| `lib/news/` | Aggregator, Sources, Types |
| `lib/storage/` | Adapter, Preferences, Remote Preferences, Profile Key |
| `lib/providers/` | nur noch Legacy-/Metadaten-/Typ-Kontext, nicht produktive Datenabfrage |

### Zu `lib/providers`

`src/lib/providers` ist **nicht** mehr die normative Datenebene fuer Quotes, OHLCV,
Streams oder Search. Aktive Rolle: Typen/Response-Shapes, begrenzte Metadaten
wie `PROVIDER_REGISTRY`, Legacy-Reste.

---

## 8. Frontend-Surfaces und Routen

### Aktive Shell-Routen (`app/(shell)/`)

| Route | Surface | Code-Pfad | Anmerkung |
|:------|:--------|:----------|:----------|
| `/trading` | Trading Workspace | `app/(shell)/trading/page.tsx` | Haupt-Workspace; TRF1–TRF42 |
| `/geopolitical-map` | GeoMap Workspace | `app/(shell)/geopolitical-map/page.tsx` | Phase 12 aktiv |
| `/control` | Agent Control Center | `app/(shell)/control/[[...tab]]/page.tsx` | Agents, Sessions, KG, Evals, Skills, Tools |
| `/files` | File Management / UIL Upload | `app/(shell)/files/[[...tab]]/page.tsx` | Upload, Search, Reindex |

### Auth-Routen (ausserhalb Shell)

| Route | Surface | Anmerkung |
|:------|:--------|:----------|
| `/auth/register` | Registrierung | |
| `/auth/passkeys` | Passkey Management | |
| `/auth/security` | Security-Einstellungen | |
| `/auth/admin/users` | Admin User Management | |
| `/auth/kg-encryption-lab` | KG Encryption Lab | Dev/Lab |
| `/auth/passkeys-lab` | Passkeys Lab | Dev/Lab |

### BFF-API-Namespaces (`app/api/`)

| Namespace | Owner | Anmerkung |
|:----------|:------|:----------|
| `/api/v1/*` | Go Gateway Proxy | Thin BFF; kein Domain-Logik im Handler |
| `/api/market/*` | Next.js BFF | OHLCV, Quotes, Stream, Search, Provider-Credentials |
| `/api/fusion/*` | Next.js BFF | Orders, Alerts, Portfolio, Preferences, Trade-Journal, Strategy, Risk |
| `/api/geopolitical/*` | Next.js BFF | Events, Candidates, Contradictions, Drawings, Timeline, Seed, Stream |
| `/api/memory/*` | Next.js BFF | KG-Nodes, Sync, Seed, Episodes, Search, Health |
| `/api/agent/chat` | Next.js BFF | Route vorhanden; Go-Downstream-Contract noch Drift (P0) |
| `/api/control/*` | Next.js BFF | Agents, Sessions, Skills, Evals, KG-Context, Tool-Events, Overview, Security |
| `/api/files/*` | Next.js BFF | Upload-Intent, CRUD, URL, Search, Reindex |
| `/api/admin/users` | Next.js BFF | Admin-Benutzerverwaltung |
| `/api/auth/*` | Auth.js + Passkey Handlers | Registrierung, Passkeys, Revocations |

### Produkt-Richtung

- Research-/decision-surface als wichtiger Einstieg
- Trading-Workspace als tiefer Power-User-Modus
- Control-Workspace als interne Agent- und System-Monitoring-Surface
- Files als UIL-Eingabe-Surface

---

## 9. Realtime und Streaming

| Thema | Regel |
|:------|:------|
| Market streaming | Go-SSE ist der Standardpfad |
| Client updates | SSE-Events → `queryClient.setQueryData` — kein separater State-Layer |
| Konkrete Hooks | `useMarketStream` (Candles/OHLCV), `useOrderbookStream` (Bids/Asks) |
| SSE-Pattern | `EventSource` + named event (`"candle"`, `"orderbook"`) + Query-Key pro Symbol |
| Geopolitical stream | `api/geopolitical/stream` — SSE-Pfad fuer Geo-Events |
| Legacy fallback | nur explizit gegated, nicht implizit |
| Alerts | Richtung server-side in Go, nicht rein clientseitig |

---

## 10. Offene Frontend-Arbeit

### Noch wichtig

- `/api/agent/chat` — Go-Contract-Drift schliessen (P0); Next-Route existiert bereits
- weitere BFF-Routen und Legacy-Helfer konsequent auf Go-first-/thin-proxy-Regeln pruefen
- `lib/providers` weiter von alten Produktivpfaden befreien
- mehr Response-Validierung an der Frontend-Grenze (FE2: Zod-Contracts)
- GeoMap-Workspace weiter in kleinere, klarere Ownership-Bloecke schneiden
- TanStack Query Defaults vereinheitlichen: `staleTime`/`gcTime`/retry-Audit (FE7)
- Query-Key-Konzept fuer alle Surfaces konsolidieren (FE9)
- Dead File `src/features/trading/useIndicatorActions.ts` entfernen (`git rm`)
- `/control` und `/files` Routen formal in SYSTEM_STATE und CAPABILITY_REGISTRY aufnehmen

### Noch nicht sinnvoll

- neue Frontend-Minis nur fuer einzelne UI-Slices
- Rueckbau der BFF-Schicht zugunsten direkter Browser->Go Kommunikation
- Wiederaufleben lokaler Provider-Manager-Logik im Client

---

## 11. Querverweise

| Frage | Dokument |
|:------|:---------|
| Welche API-/Header-/SSE-Vertraege gelten? | `docs/specs/API_CONTRACTS.md` |
| Welche UIL-Routen gelten? | `docs/specs/api/API_UIL_ROUTES.md` |
| Welche Runtime-/Port-Realitaet gilt? | `docs/specs/SYSTEM_STATE.md` |
| Welche Security-Grenzen gelten? | `docs/specs/security/AUTH_MODEL.md` |
| Welche Roadmap-Punkte sind offen? | `EXECUTION_PLAN.md` |
| KG-Browser-Schicht? | `docs/specs/architecture/MEMORY_AND_STORAGE_BOUNDARIES.md` |
| Agent-Runtime? | `docs/specs/architecture/AGENT_RUNTIME_ARCHITECTURE.md` |
