# Observability tier strategy — OTel + OpenObserve + 3-tier model

**Date:** 2026-04-24
**Task:** `#46` exec-17 Observability (+ follow-up `#93`)
**Scope:** Architektur-entscheidung wo OTel-instrumentation hingehört in matrix, und klarstellung der rollenteilung zwischen OpenTelemetry (standard) und OpenObserve (backend-produkt).

## §1 Clarification — OTel ≠ OpenObserve

Häufige verwechslung in der team-diskussion, deshalb hier explizit:

| | **OpenTelemetry (OTel)** | **OpenObserve** |
|---|---|---|
| **Was** | Standard / protokoll / SDKs | Backend-produkt / storage + UI |
| **Typ** | Spec (CNCF) + library | Running server (rust binary, AGPL) |
| **Rolle** | **Produzent**-seite: code instrumentieren, OTLP spans/metrics/logs erzeugen | **Konsument**-seite: OTLP empfangen, speichern, visualisieren |
| **Vendor** | vendor-neutral | ZincLabs (ein vendor) |
| **In matrix** | `go.opentelemetry.io/otel`, `opentelemetry-python`, `@vercel/otel` | `:5080` UI, `:5081` OTLP gRPC receiver |

**Analogie:** OTel = HTTP protokoll. OpenObserve = ein konkreter web-server (wie nginx).

### Vendor-neutrality — OpenObserve ist austauschbar

OTel's ganze design-philosophie ist vendor-neutrality. Services exportieren OTLP, und der **konsument** ist swappable:

```
go-appservice + python-agent + (later) Next.js BFF
  └─ OTel SDK produziert OTLP
     └─ Exportiert an OTEL_EXPORTER_OTLP_ENDPOINT
        └─ Dort empfängt: OpenObserve :5081 (heute)
                          ODER Jaeger :4317
                          ODER Grafana Tempo :4317
                          ODER Datadog Agent :4318
                          ODER Honeycomb direct OTLP
                          ODER New Relic OTLP
                          ODER SigNoz :4317
```

**Switch-kosten bei backend-wechsel**:
- `OTEL_EXPORTER_OTLP_ENDPOINT` umstellen
- Auth-header format ändern (jeder vendor hat eigenen auth-mechanismus)
- Kein application-code-change

**Was nicht portabel ist**: `OPENOBSERVE_USER/PASSWORD` basic-auth ist openobserve-spezifisch. Datadog nutzt `DD_API_KEY`, Honeycomb nutzt `X-Honeycomb-Team` header, Jaeger hat meist kein auth im OTLP-path. Das ist auth-layer, nicht OTel-layer.

**Verify-item für #46**: bestätigen dass unser setup diese portability respektiert. Wenn ein TODO auftaucht wo OpenObserve-API direkt gecalled wird (nicht OTLP), ist das ein architektur-leak.

## §2 3-tier frontend-observability model

Nach research (siehe sources unten) ist die SOTA 2026 ein 3-tier aufbau. Alle sind unabhängig aktivierbar:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 1 — Backend OTel (server-to-server)                              │
│   go-appservice + python-agent                                         │
│   STATUS: ✅ implementiert (telemetry/tracer.go, shared/app_factory.py)│
└────────────────────────────────────────────────────────────────────────┘
                              │ OTLP gRPC :5081
                              ▼
                         OpenObserve
                              ▲
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 2 — Next.js BFF (server-side)                                    │
│   @vercel/otel in src/instrumentation.ts                              │
│   STATUS: PART OF #46 (diese task)                                    │
└────────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ W3C traceparent propagation
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 3 — Browser RUM (client-side)                                    │
│   @opentelemetry/sdk-trace-web via BFF-proxy (nie direct!)            │
│   STATUS: #93 follow-up                                                │
└────────────────────────────────────────────────────────────────────────┘
```

### Warum tier 2 jetzt in #46

- Gleiches pattern wie tier 1 (OTel SDK + OTLP gRPC + basic-auth)
- Gleicher backend (OpenObserve :5081)
- Server-side, keine security-komplikationen
- @vercel/otel ist drop-in (eine instrumentation.ts file, ein dep)
- trading-project pattern bereits vorhanden als referenz

### Warum tier 3 als separate task (#93)

Tier 3 ist **fundamental anders** in security + architektur:

1. **Keine creds im browser** — industry consensus (Grafana, Dash0, Groundcover, Elastic 2026): OTLP direkt vom browser mit creds ist eine vuln. Muss via BFF-proxy laufen.
2. **Eigener BFF endpoint** — `/api/telemetry` route im next.js die OTLP vom browser empfängt, auth-header anhängt, an OpenObserve weiterleitet.
3. **CSP / CORS setup** — browser OTLP macht neue cross-origin requests, muss in Content-Security-Policy headers.
4. **User consent / privacy** — RUM erfasst user-interactions, fetch-URLs, timing. DSGVO-frage: opt-in pflicht?
5. **Browser SDK maturity** — `@opentelemetry/sdk-trace-web` ist "stable" aber viele instrumentations noch "experimental" (laut offiziellem repo)

Das alles verdient eigenes spec-scope.

## §3 Security pattern für tier 3 (wenn wir #93 angehen)

**NIEMALS direct:**
```
Browser → OpenObserve :5081   // creds im bundle = leak via DevTools
```

**IMMER via proxy:**
```
Browser → /api/telemetry (Next.js BFF)
           ├─ prüft session / origin
           ├─ rate-limits
           ├─ attached OPENOBSERVE_USER/PASSWORD basic-auth
           └─ forward an OpenObserve :5081
```

BFF auth macht auch: zero-trust für browser-seite, keine credential-rotation-belastung für browser-clients, natural CORS endpoint.

## §4 Konkrete tasks

### #46 (aktuell in progress) — reframed scope

**Umfasst jetzt:**
1. OpenObserve container recreation mit env (in progress)
2. Go-appservice `.env.development` ergänzen mit OPENOBSERVE_*
3. Go-traces E2E smoke: start go mit OTEL_ENABLED=true, request → check openobserve UI zeigt span
4. Python-agent traces E2E smoke: gleicher flow
5. **Tier 2 NEU**: Next.js BFF via @vercel/otel
   - `bun add @vercel/otel` in frontend_merger
   - `src/instrumentation.ts` mit opt-in-toggle
   - `OTEL_ENABLED` + `OTEL_EXPORTER_OTLP_ENDPOINT` in frontend_merger/.env.development
   - OTel auth-header config für basic-auth gegen openobserve
   - Smoke: next.js BFF call → openobserve zeigt span
6. Vendor-portability verify: grep nach direkt OpenObserve-API-calls außerhalb des OTel-stacks (sollte keine geben — wenn ja, ADR dafür)

### #93 (neu, folge-task)

**Titel:** "exec-17 Tier-3 Browser RUM via BFF-proxy"

**Umfasst:**
1. BFF `/api/telemetry` POST-route bauen (attached creds, forwards OTLP)
2. @opentelemetry/sdk-trace-web + fetch/xhr auto-instrumentations installieren
3. `frontend_merger/src/observability/otel.client.ts` — client-side setup, sendet an `/api/telemetry`
4. Mount in layout.tsx via `<script>` oder client-component
5. CSP-header update für own-origin OTLP
6. Opt-in flag + privacy/consent copy
7. Smoke: browser-click → network-request an `/api/telemetry` → OpenObserve UI zeigt browser-span mit traceparent-link zu go-appservice-span

**Priorität**: nice-to-have. Backend-observability reicht für ops. Browser RUM erst wenn wir explizit user-experience-latency jagen.

## §5 Was NICHT in scope ist (bewusst)

- **Direct browser OTLP export** — verworfen, security-risk
- **Extra MCP-server für OpenObserve** — nice-to-have aber nicht blocking. Wenn wir OpenObserve-spans via Claude Code inspecten wollen, wäre ein dedicated mcp-openobserve-server eine option. Tracke als separate idea, nicht jetzt.
- **Grafana / Jaeger dashboards** — OpenObserve UI ist ausreichend
- **LLM-specific tracing** (OpenLLMetry etc.) — separat evaluieren in exec-17 Phase-3 wenn wir prompt-level traces brauchen

## Sources

- [Next.js OpenTelemetry guide](https://nextjs.org/docs/app/guides/open-telemetry) — `@vercel/otel` ist recommended default
- [OpenTelemetry Browser SDK repo](https://github.com/open-telemetry/opentelemetry-browser) — browser SDK status
- [OpenTelemetry client-apps official](https://opentelemetry.io/docs/platforms/client-apps/)
- [Groundcover — Frontend Observability with RUM](https://www.groundcover.com/blog/real-user-monitoring) — reverse-proxy pattern
- [Dash0 — Website Monitoring with OTel](https://www.dash0.com/guides/website-monitoring-with-opentelemetry-and-dash0)
- [Grafana Frontend Observability + RUM](https://grafana.com/products/cloud/frontend-observability/)
- [Elastic — OTel browser instrumentation (EDOT)](https://www.elastic.co/observability-labs/blog/edot-browser-rum)
- [OpenTelemetry OTLP exporter spec](https://opentelemetry.io/docs/specs/otel/protocol/exporter/) — auth via headers pattern

## Cross-refs

- `specs/execution/superpower-impl-log.md §2` — observability cluster entries
- `specs/execution/exec-17-observability-harness-traces.md` — full spec
- `docs/superpowers/findings/2026-04-24-env-layout-decision.md` — env-scope entscheidung (voraussetzung für tier-2 setup)
- `docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md` — postgres audit vs OpenObserve OTel trennung
