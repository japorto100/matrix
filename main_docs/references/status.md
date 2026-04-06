# Reference Source Status

> **Stand:** 09. Maerz 2026  
> **Zweck:** Aktive Provider-/Quellen-Status-Matrix fuer implementierte,
> gescaffoldete und geplante Source-Gruppen.

---

## SDMX-Provider

> **Selection-Regel:** `IMF IFS`, `World Bank`, `OECD`, `UN` und `BIS` bilden die
> globale Baseline. Offizielle Zentralbank-/Institutionenquellen werden nur als
> dokumentierte Tier-1-Ausnahmen aktiv gehalten.
> **Tier-1-Begruendung:** siehe `sources/macro-and-central-banks.md`.

| Provider | Status | Symbolformat | Exchange | Notes |
|:---------|:-------|:-------------|:---------|:-----|
| IMF IFS | Implementiert | `IMF_IFS_<FREQ>_<REF_AREA>_<INDICATOR>`, `POLICY_RATE` | `imf` | Phase 14a |
| ECB | Implementiert | ECB-spezifisch | `ecb` | ecbsdmx |
| OECD | Implementiert | `OECD_<LOCATION>_<SUBJECT>_<MEASURE>_<FREQUENCY>`, `GDP` | `oecd` | 14a.2 MEI |
| World Bank | Implementiert | `WB_WDI_<FREQ>_<SERIES>_<REF_AREA>`, `POPULATION` | `worldbank` | 14a.2 WDI |
| UN | Implementiert | `UN_<DATAFLOW>__<KEY>` | `un` | 14a.2; REST path `data/{dataflow}/{key}`, canonical symbol uppercased by gateway |
| ADB | Scaffold | `ADB_*` | `adb` | 14a.2; im Wiring registriert und env-seitig gefuehrt, `GetSeries` bleibt bewusst unimplementiert bis zu dokumentiertem Regional-Gap |

### Persistenzprofil: SDMX-Provider

| Quelle | Persistenzklasse | Cadence-Hinweis | Retention | Arbeitsregel |
|:-------|:-----------------|:----------------|:----------|:-------------|
| `IMF IFS`, `OECD`, `World Bank`, `UN` | `api-hot` | `daily` bis `weekly`, bevorzugt `conditional-poll` falls moeglich | `ephemeral` plus optional `snapshot` fuer kuratierte Referenzserien | cache-first; raw persistence nur bei Debug-/Replay-Bedarf |
| `ECB` | `api-hot` | `daily` bis `intraday` je Serie | `ephemeral` | rates-/fx-nahe Serien cache-first; spaeter selektive snapshotting fuer Referenzserien moeglich |
| `ADB` | `api-hot` -> spaeter optional `api-snapshot` | nur bei dokumentiertem Regional-Gap | `ephemeral` | kein weiterer Persistenzpfad vor aktiver `GetSeries`-Implementierung |

---

## TimeSeries / EM Central Banks

> **Selection-Regel:** EM-/offizielle Zentralbankquellen bleiben selektive
> Tier-1-Quellen bei klarem FX-/Rates-/Policy-Mehrwert; kein blanket coverage pro Land.
> **Tier-1-Begruendung:** siehe `sources/macro-and-central-banks.md`.

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| BCB (Brazil) | Implementiert | `bcb` | Phase 14b |
| Banxico | Implementiert | `banxico` | Phase 14b |
| BoK (Korea) | Implementiert | `bok` | Phase 14b |
| BCRA (Argentina) | Implementiert | `bcra` | Phase 14b |
| TCMB (Turkey) | Implementiert | `tcmb` | Phase 14b |
| RBI (India) | Implementiert | `rbi` | Phase 14b |
| FRED | Implementiert | `fred` | Phase 14b.2; request-scoped API-Key-Transport im Gateway verifiziert |
| OFR | Implementiert | `OFR_<DATASET>-<SERIES_IDENTIFIER>` | `ofr` | 14b.2; official STFM `series/full` mnemonic query |
| NYFed | Implementiert | `NYFED_{SOFR|TGCR|BGCR|EFFR|OBFR}` | `nyfed` | 14b.2; official Markets API reference rates |

### Persistenzprofil: TimeSeries / EM Central Banks

| Quelle | Persistenzklasse | Cadence-Hinweis | Retention | Arbeitsregel |
|:-------|:-----------------|:----------------|:----------|:-------------|
| `BCB`, `Banxico`, `BoK`, `BCRA`, `TCMB`, `RBI`, `FRED`, `OFR`, `NYFed` | `api-hot` | `hourly` bis `daily` je Serie; `conditional-poll` wo der Contract es hergibt | `ephemeral` | Hot-cache ist der Standard; raw snapshots nur fuer spaeter definierte audit-/replay-nahe Spezialserien |

---

## Market / Realtime Provider

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| Finnhub | Implementiert | `finnhub` | produktnaher Quote-/Stream-Default; request-scoped Credential-Transport im Gateway verifiziert, Live-/Browser-Verify noch offen |

### Persistenzprofil: Market / Realtime

| Quelle | Persistenzklasse | Cadence-Hinweis | Retention | Arbeitsregel |
|:-------|:-----------------|:----------------|:----------|:-------------|
| `Finnhub` | `api-hot` und fuer Streams `stream-only` | quotes `poll`/on-demand; stream surfaces kontinuierlich | `ephemeral` | Quotes laufen jetzt auf einem kurzen TTL-Hot-Cache; keine blinde raw persistence, spaeter nur gezielte snapshot capture fuer audit-/debug- oder feature-begruendete Pfade |

---

## Internal / Bridge / Geo Context Connectoren

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| Finance Bridge | Implementiert | `financebridge` | im Wiring registriert; `FINANCE_BRIDGE_URL`, `FINANCE_BRIDGE_URLS`, `FINANCE_BRIDGE_HTTP_TIMEOUT_MS`; Batch-4 Smoke-/Failover-Tests dokumentiert |
| Indicator Service | Implementiert | `indicatorservice` | im Wiring registriert; `INDICATOR_SERVICE_URL`, `INDICATOR_SERVICE_TIMEOUT_MS`; JSON-/IPC-Transport und Error-Pfad getestet |
| Soft Signals | Implementiert | `softsignals` | im Wiring registriert; `GEOPOLITICAL_SOFT_SIGNAL_URL`, `GEOPOLITICAL_SOFT_SIGNAL_TIMEOUT_MS`; JSON-/IPC-Transport und Error-Pfad getestet |
| Geopolitical Next Proxy | Implementiert | `geopoliticalnext` | im Wiring registriert; `GEOPOLITICAL_FRONTEND_API_URL`, `GEOPOLITICAL_FRONTEND_API_TIMEOUT_MS`; dient als Go->Next Geo/BFF-Proxy und bleibt env-led |
| ACLED | Implementiert | `acled` | im Wiring registriert; Basis-URL/Timeout + Credentials in Go-Env; erster `api-snapshot`-Pfad mit Raw-JSON, normalized snapshot und `source_snapshot_metadata`-Statuswechsel auf `normalized` steht |
| GDELT | Implementiert | `gdelt` | im Wiring registriert; `GDELT_BASE_URL`, `GDELT_HTTP_TIMEOUT_MS`, `GDELT_HTTP_RETRIES`; Happy- und Error-Path getestet |
| CFR Context Catalog | Implementiert | `cfr` | im Wiring registriert; bewusst statischer Kontext-Katalog statt Live-Fetcher |
| CrisisWatch | Implementiert | `crisiswatch` | im Wiring registriert; RSS-/Cache-Variablen in Go-Env; erster `api-snapshot`-Pfad mit Raw-XML, normalized snapshot und `source_snapshot_metadata`-Statuswechsel auf `normalized` steht, Persisted-Cache bleibt parallel bestehen |
| Game Theory | Implementiert | `gametheory` | im Wiring registriert; `GEOPOLITICAL_GAMETHEORY_URL`, `GEOPOLITICAL_GAMETHEORY_TIMEOUT_MS`; Transportpfad env-gesteuert |
| Memory Service | Implementiert | `memory` | im Wiring registriert; `MEMORY_SERVICE_URL`, `MEMORY_SERVICE_TIMEOUT_MS`; KG-/health client tests vorhanden |
| Agent Service | Implementiert | `agentservice` | im Wiring registriert; `AGENT_SERVICE_URL`, `AGENT_SERVICE_TIMEOUT_MS`; run-/health transport tests vorhanden |

### Persistenzprofil: Internal / Bridge / Geo Context

| Quelle | Persistenzklasse | Cadence-Hinweis | Retention | Arbeitsregel |
|:-------|:-----------------|:----------------|:----------|:-------------|
| `financebridge`, `indicatorservice`, `softsignals`, `geopoliticalnext`, `memory`, `agentservice` | `api-hot` | `on-demand` | `ephemeral` | service transport bleibt cache-/response-first; keine Source-Snapshot-Persistenz auf diesem Layer |
| `acled`, `gdelt`, `crisiswatch` | `api-snapshot` | `poll` je Feed/Window, typischerweise `hourly` bis `daily` | `snapshot` | fuer alle drei existiert jetzt ein erster Raw- plus normalized-snapshot-Pfad; naechster Schritt ist die saubere Ableitung normalisierter Downstream-Sichten |
| `cfr` | `api-hot` | `manual` oder `weekly` | `ephemeral` | statischer Kontextkatalog, kein schwerer snapshot-first Pfad |
| `gametheory` | `api-hot` | `on-demand` | `ephemeral` | interner service output, kein externer raw snapshot |

---

## News / Headline Connectoren

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| RSS Feed Basket | Implementiert | `news-rss` | ueber `NEWS_RSS_FEEDS`, `NEWS_HTTP_TIMEOUT_MS`, `NEWS_HTTP_RETRIES`; derzeit Default auf MarketWatch Top Stories; Retry-Test fuer RSS-Client vorhanden |
| Finviz RSS | Implementiert | `finviz-rss` | ueber `FINVIZ_RSS_BASE_URL` plus globale `NEWS_*`-Timeout/Retry-Pfade; symbolbasierter RSS-Headline-Connector |
| GDELT News | Implementiert | `gdelt-news` | nutzt denselben `GDELT_BASE_URL`-, Timeout- und Retry-Vertrag; erster `api-snapshot`-Pfad mit Raw-JSON, normalized snapshot und `source_snapshot_metadata`-Statuswechsel auf `normalized` steht |

### Persistenzprofil: News / Headline Connectoren

| Quelle | Persistenzklasse | Cadence-Hinweis | Retention | Arbeitsregel |
|:-------|:-----------------|:----------------|:----------|:-------------|
| `RSS Feed Basket`, `Finviz RSS` | `api-snapshot` | `poll` typischerweise `15m` bis `hourly` | `snapshot` | headline batches sollten spaeter deduped und als normalisierte feed snapshots gehalten werden |
| `GDELT News` | `api-snapshot` | `poll` oder `on-demand` je dossier/query | `snapshot` | erster Raw- plus normalized-snapshot-Pfad steht; vectorization erst nach Textnormalisierung |

---

## Geplante Tier-1 / Specialist Feeds

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| FINMA Enforcement | Geplant | `finma-enforcement` | Tier-1-Research-/Compliance-Kandidat; noch kein aktiver Runtime-Contract, deshalb keine Env-Pflicht |
| SEC Enforcement RSS | Geplant | `sec-enforcement-rss` | Tier-1-Narrativ-/Enforcement-Feed; Onboarding erst nach dokumentiertem Produkt-Trigger |
| FINRA Margin Statistics | Geplant | `finra-margin` | Stability-/Leverage-Spezialist; erst nach klarem Risk-/NBFI-Slice in aktiven Rollout heben |
| BIS Early Warning Indicators | Geplant | `bis-ewi` | globale Stability-Baseline im Quellenkatalog, aber noch kein aktiver Go-Connector |
| BIS RCAP | Geplant | `bis-rcap` | Tier-1-Supervisory-/Basel-Spezialfeed; kein aktives Onboarding ohne Policy-/Compliance-Trigger |
| FSB NBFI Report | Geplant | `fsb-nbfi` | Research-/Context-Layer fuer NBFI und Shadow Banking; kein Runtime-Connector bis konkreter Produktbedarf |
| GLEIF LEI API | Geplant | `gleif-lei` | globaler Free-Stack-Baustein fuer Legal-Entity-Identifier, Entity-Resolution und Cross-Jurisdiction-Matching |
| OpenOwnership Register | Geplant | `openownership` | Free-Stack-Erweiterung fuer Beneficial-Ownership-/UBO-Context; Coverage je Jurisdiktion variabel |
| UK Companies House API | Geplant | `companieshouse-uk` | offizieller frei zugaenglicher Registry-Feed als erster Country-Registry-Connector |

---

## BulkFetcher / DiffWatcher

> **Selection-Regel:** offizielle Diff-/Sanctions-Feeds sind bevorzugte Baselines;
> normalisierte oder abgeleitete Feeds bleiben nur dort aktiv, wo die offizielle
> Maschinen-Schnittstelle noch keinen stabilen Runtime-Pfad hat.
> **Tier-1-Begruendung:** siehe `sources/market-data.md`, `sources/legal-and-regulatory.md` und `sources/financial-stability-and-nbfi.md`.

| Source | Status | Notes |
|:-------|:-------|:-----|
| CFTC COT | Implementiert | 14c.1; official historical compressed zip path on CFTC bulk fetcher; erster Raw-Snapshot- und Metadata-Bootstrap im Go-Storage aktiv |
| FINRA ATS | Scaffold | 14c.2; official FINRA OTC Transparency contract narrowed to `weeklySummary` POST / file-download flow; Go scaffold now uses OAuth/Bearer + JSON POST, but payload/file-download hardening and live verify remain open |
| LBMA Gold Fix | Scaffold | 14c.3 |
| FXCM Sentiment | Scaffold | 14c.3 |
| OFAC SDN | Implementiert | 14d.1; offizieller XML-Diff-Watcher + GeoMap sanctions pack; erster Raw-Snapshot- und Metadata-Bootstrap im Go-Storage aktiv |
| UN Sanctions | Implementiert | 14d.2; offizieller UN consolidated XML watcher + GeoMap sanctions pack; erster Raw-Snapshot- und Metadata-Bootstrap im Go-Storage aktiv |
| SECO Sanctions | Implementiert | 14d.2; offizieller SECO-XML-Download jetzt als Primaerpfad im Watcher, mit OpenSanctions-Fallback fuer transiente Fetch-Probleme; erster Raw-Snapshot- und Metadata-Bootstrap im Go-Storage aktiv |
| EU Sanctions | Implementiert | 14d.2; JSON watcher im GeoMap sanctions pack, derzeit ueber normalisierten OpenSanctions-Feed; offizielle FSF XML/CSV-Files bestaetigt, stabiler Runtime-Fetch-Contract noch offen |
| GeoMap Source Pack | Implementiert | 14g.1; sanctions watcher aggregation + candidate mapping + admin fetch path verifiziert |

### Persistenzprofil: BulkFetcher / DiffWatcher

| Quelle | Persistenzklasse | Cadence-Hinweis | Retention | Arbeitsregel |
|:-------|:-----------------|:----------------|:----------|:-------------|
| `CFTC COT` | `file-snapshot` | `weekly` oder `on-change` | `snapshot` | compressed bulk files zuerst raw speichern, danach normalisieren |
| `OFAC SDN`, `UN Sanctions`, `SECO Sanctions` | `file-snapshot` | `daily` bis `on-change`, bevorzugt `conditional-poll` falls Head-/etag moeglich | `snapshot` bis `audit` | offizielle XML-Downloads gehoeren object-first in Storage; normalized sanctions records danach ableiten |
| `EU Sanctions` | aktuell `api-snapshot`, Ziel `file-snapshot` | `daily` bis `on-change` | `snapshot` | solange OpenSanctions-JSON primaer ist, snapshot-faehiger normalized path; nach offiziellem FSF-Switch object-first |
| `FINRA ATS` | `api-snapshot` | `weekly` oder dataset-spezifisch | `snapshot` | POST-/download responses spaeter replay-faehig halten; file-download-Zweig noch offen |
| `LBMA Gold Fix`, `FXCM Sentiment` | `api-snapshot` oder `file-snapshot` spaeter | nur bei Trigger | `snapshot` | kein aktiver Persistenzpfad vor echtem Product Trigger |
| `GeoMap Source Pack` | abgeleiteter normalized snapshot | je Watcher-Lauf | `snapshot` | Aggregat ist kein Rohfeed, sondern abgeleitetes, map-fertiges Paket |

---

## Credential-bearing Quellen

| Provider | Auth-Art | Env-Variable(n) | Pflicht-Check |
|:---------|:---------|:----------------|:--------------|
| Finnhub | API Key | `FINNHUB_API_KEY` | `go-backend/.env.example`, `.env.development`, `.env.production`; request-scoped Override via Next Cookie/Header verifiziert |
| FRED | API Key | `FRED_API_KEY` | `go-backend/.env.example`, `.env.development`, `.env.production`; request-scoped Override im Go-Connector verifiziert |
| ACLED | Token + Account-Daten | `ACLED_API_TOKEN`, `ACLED_EMAIL`, `ACLED_ACCESS_KEY` | `go-backend/.env.example`, `.env.development`, `.env.production` |
| Banxico | API Token | `BANXICO_API_TOKEN` | `go-backend/.env.example`, `.env.development`, `.env.production`; request-scoped Override im Go-Connector verifiziert |
| BoK ECOS | API Key | `BOK_ECOS_API_KEY` | `go-backend/.env.example`, `.env.development`, `.env.production`; request-scoped Override im Go-Connector verifiziert |
| FINRA ATS | OAuth/Bearer | `FINRA_API_CLIENT_ID`, `FINRA_API_CLIENT_SECRET`, `FINRA_API_BEARER_TOKEN`, `FINRA_OAUTH_TOKEN_URL` | `go-backend/.env.example`, `.env.development`, `.env.production`; offizieller POST-/Bearer-Scaffold vorhanden, Live-Run und Dataset-Haertung noch offen |

Neue auth-pflichtige Quellen muessen zusaetzlich in
`../specs/execution/source_onboarding_and_keys.md` nachgezogen werden.

### Aktuelle Delivery-Prioritaeten

- `P1`: `finnhub`, `fred`, `banxico`, `bok` env-/transportseitig weitgehend geschlossen; Live-/Browser-Verify spaeter bei laufendem Stack
- `P2`: `EU Sanctions` auf primaeren offiziellen Runtime-Pfad heben; `SECO` ist technisch auf offiziellen XML-Primärpfad mit Fallback umgestellt
- `P3`: `FINRA ATS` nur nach belastbarem offiziellem Contract aus dem Scaffold holen
- `P4`: `ADB` nur bei echtem regionalem Coverage-Gap aktivieren

### Restmatrix fuer bereits eingebaute Quellen

- `wirklich fertig ohne offenen Runtime-Switch`:
  - `ecb`, `bcb`, `bcra`, `tcmb`, `rbi`, `imf`, `oecd`, `worldbank`, `un`, `ofr`, `nyfed`, `cftc cot`
  - `financebridge`, `indicatorservice`, `softsignals`, `geopoliticalnext`, `acled`, `gdelt`, `cfr`, `crisiswatch`, `gametheory`, `memory`, `agentservice`
  - `rss feed basket`, `finviz rss`, `gdelt news`
  - `ofac sdn`, `un sanctions`, `geomap source pack`
- `nur live/browser verify offen`:
  - `finnhub`, `fred`, `banxico`, `bok`
- `official runtime switch offen`:
  - `eu sanctions`
- `scaffold hardening offen`:
  - `finra ats`
- `bewusst scaffold bis Trigger`:
  - `adb`

### SPS-Arbeitsstand

- `SPS1`: aktive Quellenfamilien auf Persistenzklassen geschnitten
- `SPS2-SPS4`: produktnahe Bootstrap-Integrationen fuer `OFAC`, `UN`, `SECO` und `CFTC` stehen; dieselbe Storage-Env-Contract-Linie wie bei Artefakten ist code-seitig angebunden
- `SPS2-SPS4`: `GDELT News`, `ACLED` und `CrisisWatch` besitzen jetzt erste `api-snapshot`-Pfade; alle drei setzen bereits auf normalized snapshots mit Statuswechsel auf `normalized`
- `SPS8`: fuer `ACLED`, `GDELT News` und `CrisisWatch` ist die Kette `raw -> normalized snapshot` jetzt code-seitig belegt
- `SPS3`: `Finnhub`, `FRED`, `Banxico`, `BoK`, `OFR` und `NYFed` nutzen jetzt im
  Gateway denselben JSON-TTL-Hot-Cache und sind damit nicht mehr nur
  dokumentarisch `api-hot`
- `SPS8`/Storage-Layer: `source_snapshot_metadata` kann jetzt Snapshots pro
  Quelle statusgefiltert listen und den neuesten Snapshot fuer Downstream-
  Consumer aufloesen
- `SPS6`: Cadence-Hinweise pro aktiver Quellenfamilie dokumentiert
- `SPS7`: Retention-Klassen pro aktiver Quellenfamilie dokumentiert
- offen bleiben vor allem:
  - Erweiterung des bestehenden lokalen Bootstraps fuer `OFAC`, `UN`, `SECO`, `CFTC` auf den finalen Object-Storage-Pfad
  - spaeterer `EU`-Switch auf offiziellen file-snapshot Pfad
  - `FINRA ATS` replay-faehige snapshot-Persistenz nach weiterem hardening

### Deferred Live-/Storage-Verify

- [ ] `OFAC`, `UN`, `SECO`, `CFTC`: echter Object-Storage-Write/Read gegen
  laufenden SeaweedFS-Stack
- [ ] `OFAC`, `UN`, `SECO`, `CFTC`: Snapshot-Fehlerpfade gegen laufenden
  Object-Storage pruefen (`timeout`, fehlender bucket, unterbrochener write)
- [ ] `ACLED`, `CrisisWatch`: Object-Storage-Live-Write/Read und Snapshot-
  Fehlerpfade gegen laufenden Stack pruefen
- [ ] `GDELT News`: Object-Storage-Live-Write/Read und Snapshot-Fehlerpfade
  gegen laufenden Stack pruefen
- [ ] `finnhub`, `fred`, `banxico`, `bok`: produktiver Live-/Browser-Verify bei
  laufendem Stack
- [ ] `EU Sanctions`: offizieller Runtime-Switch plus anschliessender
  Live-Verify
- [ ] `FINRA ATS`: offizieller payload-/download-Zweig plus anschliessender
  Live-Run mit Credentials

---

## Aenderungshistorie

| Datum | Aenderung |
|:------|:----------|
| 28. Feb 2026 | Initial — Phase 14 Status-Matrix |
| 01. Mär 2026 | 14c.3 LBMA/FXCM, 14d.2 UN/SECO/EU, 14g.1 GeoMap Source Pack |
| 09. Mär 2026 | Finnhub/FRED/Banxico/BoK Credential-Transport (request-scoped) verifiziert |
| 10. Mär 2026 | OECD, World Bank, UN, NYFed und OFR Batch-2 Happy/Error-Pfade mit Gateway-Tests verifiziert |
| 10. Mär 2026 | OFAC, UN, SECO und EU Sanctions-Watcher inkl. GeoMap sanctions pack / admin fetch erneut verifiziert; SECO/EU aktuell ueber normalisierte OpenSanctions-Feeds |
| 10. Mär 2026 | CFTC COT Bulk-Fetcher auf offiziellen Historical-Compressed-ZIP-Pfad gehoben und mit ZIP-/Parser-Tests verifiziert |
| 10. Mär 2026 | Source-Tiering geschlossen: Tier-1-Mehrwerte fuer Macro, Market, Legal, Stability und Sovereign in `sources/*.md` dokumentiert |
| 10. Mär 2026 | Delivery-Reihenfolge nach Source-Selection festgezogen: P1 Credential-Live-Gates, P2 offizielle SECO/EU-Pfade, P3 FINRA ATS, P4 ADB nur bei Coverage-Gap |
| 10. Mär 2026 | P2-Contract-Review geschaerft: SECO offizieller XML-Pfad bestaetigt, EU FSF XML/CSV/RSS bestaetigt; beide Runtime-Migrationen bleiben bis zu stabilem offiziellen Fetch-Contract auf OpenSanctions-Defaults |
| 10. Mär 2026 | P3-Contract-Review geschaerft: FINRA ATS offizieller Contract auf OTC Transparency `weeklySummary` POST / ATS file-download flow eingegrenzt; aktueller Go-Stub bleibt bewusst Scaffold |
| 10. Mär 2026 | P4-ADB bereinigt: Wiring-/Env-Kette explizit gemacht; Connector bleibt bewusst Scaffold bis dokumentierter Regional-Gap + `GetSeries`-Implementierung |
| 10. Mär 2026 | FINRA ATS-Scaffold haelt jetzt Env-Overrides fuer URL/Timeout ein; `go test ./internal/connectors/finra` gruen |
| 10. Mär 2026 | SECO-Watcher kann neben OpenSanctions-JSON nun auch die offizielle SECO-XML-Struktur parsen; `go test ./internal/connectors/seco` gruen |
| 10. Mär 2026 | SECO-/EU-Watcher sind jetzt ueber Env-URL-Overrides testbar; `go test ./internal/connectors/seco ./internal/connectors/eu` gruen |
| 10. Mär 2026 | FINRA ATS-Scaffold auf offiziellen OAuth/Bearer + `weeklySummary` POST gehoben; Paket-Tests fuer Bearer- und Client-Credentials-Flow gruen |
| 10. Mär 2026 | FINRA ATS Request-Haertung ergaenzt: Default-Felder, Default-Limit und Sort-/Partition-Guards getestet; `go test ./internal/connectors/finra` weiter gruen |
| 10. Mär 2026 | SECO-Default auf offiziellen XML-Primärpfad mit OpenSanctions-Fallback gehoben; `go test ./internal/connectors/base ./internal/connectors/seco ./internal/connectors/finra` gruen |
| 12. Maerz 2026 | Persistenzprofile fuer aktive Quellenfamilien dokumentiert; mittelfristiger backend-owned relational metadata/index layer fuer Go-owned Snapshot-/Provider-Daten als Zielpfad verankert |
| 12. Maerz 2026 | Go-Storage-Bootstrap fuer Quellenpersistenz erweitert: `source_snapshot_metadata` im lokalen Metadata-Store plus gruenem `go test ./internal/storage` |
| 12. Maerz 2026 | Erster produktnaher Snapshot-Bootstrap fuer `SECO`: Raw-Datei plus `source_snapshot_metadata` ueber neuen DiffWatcher-Fetch-Hook; `go test ./internal/connectors/base ./internal/connectors/seco ./internal/storage` gruen |
| 12. Maerz 2026 | Snapshot-Bootstrap auf `OFAC`, `UN` und `CFTC` ausgeweitet; gemeinsamer lokaler Recorder fuer Diff-/Bulk-Fetcher, `go test ./internal/connectors/base ./internal/connectors/ofac ./internal/connectors/un ./internal/connectors/seco ./internal/connectors/cftc ./internal/storage` gruen |
| 12. Maerz 2026 | Snapshot-Recorder auf denselben Storage-Env-Contract wie Artefakte gehoben; S3-/Seaweed-kompatibler Recorder-Test gruen, echter Live-Stack-Verify weiter offen |
| 12. Maerz 2026 | `GDELT News` als erster `api-snapshot`-Connector auf Raw-JSON plus `source_snapshot_metadata` gehoben; `go test ./internal/connectors/news ./internal/connectors/base ./internal/storage ./internal/app` gruen |
| 12. Maerz 2026 | `ACLED` und `CrisisWatch` ebenfalls auf Raw-Snapshot plus `source_snapshot_metadata` gehoben; `go test ./internal/connectors/news ./internal/connectors/crisiswatch ./internal/connectors/acled ./internal/connectors/base ./internal/storage ./internal/app` gruen |
| 12. Maerz 2026 | `ACLED` als erster `api-snapshot`-Connector auf `normalized snapshot` plus Statuswechsel `fetched -> normalized` gehoben; `cd go-backend && go test ./internal/connectors/acled ./internal/connectors/base ./internal/storage ./internal/app` gruen |
| 12. Maerz 2026 | `GDELT News` ebenfalls auf `normalized snapshot` plus Statuswechsel `fetched -> normalized` gehoben; `cd go-backend && go test ./internal/connectors/news ./internal/connectors/base ./internal/storage ./internal/app` gruen |
| 12. Maerz 2026 | `CrisisWatch` ebenfalls auf `normalized snapshot` plus Statuswechsel `fetched -> normalized` gehoben; `cd go-backend && go test ./internal/connectors/crisiswatch ./internal/connectors/news ./internal/connectors/acled ./internal/connectors/base ./internal/storage ./internal/app` gruen |
| 12. Maerz 2026 | `Finnhub`, `FRED`, `Banxico`, `BoK`, `OFR` und `NYFed` auf gemeinsamen `api-hot` JSON-TTL-Cache gehoben; dedizierte Cache-Tests pro Connector plus Wiring-/Env-Vertraege fuer `*_CACHE_TTL_MS` nachgezogen |
| 12. Maerz 2026 | `source_snapshot_metadata` um Listen-/Latest-Queries fuer statusgefilterte Snapshot-Reads erweitert; `go test ./internal/storage` gruen |
