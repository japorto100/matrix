# SOURCE STATUS

> **Stand:** 16. Maerz 2026  
> **Zweck:** Kompakter IST-Status aller aktiven, scaffoldeten und geplanten Datenquellen.
> **Source-of-Truth-Rolle:** Navigationsdokument; vollstaendige Persistenz-, Credential-
> und Delivery-Details in `docs/references/status.md`.

---

## 1. SDMX-Provider

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| IMF IFS | Implementiert | `imf` | Phase 14a |
| ECB | Implementiert | `ecb` | ecbsdmx |
| OECD | Implementiert | `oecd` | 14a.2 MEI |
| World Bank | Implementiert | `worldbank` | 14a.2 WDI |
| UN | Implementiert | `un` | 14a.2 |
| ADB | Scaffold | `adb` | Bewusst Scaffold bis dokumentierter Regional-Gap |

---

## 2. TimeSeries / EM Central Banks

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| BCB (Brazil) | Implementiert | `bcb` | Phase 14b |
| Banxico | Implementiert | `banxico` | Credential-Transport verifiziert |
| BoK (Korea) | Implementiert | `bok` | Credential-Transport verifiziert |
| BCRA (Argentina) | Implementiert | `bcra` | Phase 14b |
| TCMB (Turkey) | Implementiert | `tcmb` | Phase 14b |
| RBI (India) | Implementiert | `rbi` | Phase 14b |
| FRED | Implementiert | `fred` | Credential-Transport verifiziert |
| OFR | Implementiert | `ofr` | 14b.2 |
| NYFed | Implementiert | `nyfed` | 14b.2 SOFR/EFFR/OBFR |

---

## 3. Market / Realtime

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| Finnhub | Implementiert | `finnhub` | produktnaher Default; Live-/Browser-Verify offen |

---

## 4. Internal / Bridge / Geo Context

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| Finance Bridge | Implementiert | `financebridge` | Batch-4 Smoke-/Failover-Tests |
| Indicator Service | Implementiert | `indicatorservice` | JSON-/IPC-Transport getestet |
| Soft Signals | Implementiert | `softsignals` | IPC-Transport getestet |
| Geopolitical Next Proxy | Implementiert | `geopoliticalnext` | Go->Next Geo/BFF-Proxy |
| ACLED | Implementiert | `acled` | Raw- + normalized-snapshot-Pfad aktiv |
| GDELT | Implementiert | `gdelt` | Happy- und Error-Path getestet |
| CFR Context Catalog | Implementiert | `cfr` | Statischer Kontext-Katalog |
| CrisisWatch | Implementiert | `crisiswatch` | Raw- + normalized-snapshot-Pfad aktiv |
| Game Theory | Implementiert | `gametheory` | Transportpfad env-gesteuert |
| Memory Service | Implementiert | `memory` | KG-/health client tests vorhanden |
| Agent Service | Implementiert | `agentservice` | Run-/health transport tests vorhanden |

---

## 5. News / Headline Connectoren

| Provider | Status | Exchange | Notes |
|:---------|:-------|:---------|:-----|
| RSS Feed Basket | Implementiert | `news-rss` | Default: MarketWatch Top Stories |
| Finviz RSS | Implementiert | `finviz-rss` | symbolbasierter Headline-Connector |
| GDELT News | Implementiert | `gdelt-news` | Raw- + normalized-snapshot-Pfad aktiv |

---

## 6. BulkFetcher / DiffWatcher

| Source | Status | Notes |
|:-------|:-------|:-----|
| CFTC COT | Implementiert | Official historical ZIP; Raw-Snapshot + Metadata-Bootstrap aktiv |
| OFAC SDN | Implementiert | XML-Diff-Watcher + GeoMap sanctions pack; Snapshot-Bootstrap aktiv |
| UN Sanctions | Implementiert | XML watcher; Snapshot-Bootstrap aktiv |
| SECO Sanctions | Implementiert | Offizieller XML-Pfad + OpenSanctions-Fallback; Snapshot-Bootstrap aktiv |
| EU Sanctions | Implementiert (via OpenSanctions) | Offizieller FSF XML/CSV-Pfad bestaetigt; Runtime-Switch offen |
| GeoMap Source Pack | Implementiert | sanctions watcher aggregation + candidate mapping |
| FINRA ATS | Scaffold | OAuth/Bearer + weeklySummary POST; file-download hardening offen |
| LBMA Gold Fix | Scaffold | 14c.3; kein aktiver Persistenzpfad |
| FXCM Sentiment | Scaffold | 14c.3; kein aktiver Persistenzpfad |

---

## 7. Geplante Tier-1 / Specialist Feeds

| Provider | Status | Notes |
|:---------|:-------|:-----|
| FINMA Enforcement | Geplant | Tier-1 Research-/Compliance-Kandidat |
| SEC Enforcement RSS | Geplant | Narrativ-/Enforcement-Feed |
| FINRA Margin Statistics | Geplant | Risk-/NBFI-Slice |
| BIS Early Warning Indicators | Geplant | globale Stability-Baseline |
| BIS RCAP | Geplant | Tier-1 Supervisory-/Basel-Spezialfeed |
| FSB NBFI Report | Geplant | Research-/Context-Layer Shadow Banking |
| GLEIF LEI API | Geplant | Legal-Entity-Identifier, Entity-Resolution |
| OpenOwnership Register | Geplant | Beneficial-Ownership-/UBO-Context |
| UK Companies House API | Geplant | erster Country-Registry-Connector |

---

## 8. Delivery-Prioritaeten

| Prio | Provider | Aktion |
|:-----|:---------|:-------|
| P1 | Finnhub, FRED, Banxico, BoK | Live-/Browser-Verify bei laufendem Stack |
| P2 | EU Sanctions | offiziellen Runtime-Switch schliessen (FSF XML/CSV) |
| P3 | FINRA ATS | nach offiziellem Contract aus Scaffold heben |
| P4 | ADB | nur bei dokumentiertem Regional-Gap |

---

## 9. Offene Live-Verifies (Storage-Verify)

- [ ] OFAC, UN, SECO, CFTC: echter Object-Storage-Write/Read gegen SeaweedFS
- [ ] ACLED, CrisisWatch, GDELT News: Object-Storage-Live-Write/Read
- [ ] Finnhub, FRED, Banxico, BoK: produktiver Live-/Browser-Verify
- [ ] EU Sanctions: offizieller Runtime-Switch + Live-Verify
- [ ] FINRA ATS: offizieller payload-/download-Zweig + Live-Run

---

## 10. Querverweise

- `docs/references/status.md` (vollstaendige Matrix inkl. Persistenzprofile)
- `docs/specs/data/DATA_ARCHITECTURE.md`
- `docs/specs/data/STORAGE_AND_PERSISTENCE.md`
- `docs/specs/data/AGGREGATION_IST_AND_GAPS.md`
