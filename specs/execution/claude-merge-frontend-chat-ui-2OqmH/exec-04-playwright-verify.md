# exec-04: Playwright Headless Smoke — frontend_merger

**Datum:** 17.04.2026
**Status:** ✓ 8/8 grün gegen Prod-Build

## Setup

- `@playwright/test@1.59.1` als devDep in `frontend_merger/`.
- `chromium-headless-shell v1217` via `bunx playwright install chromium`.
- System-Deps via `bunx playwright install-deps chromium` (alles schon vorhanden).
- `playwright.config.ts` mit `baseURL = http://127.0.0.1:3003`, `trace:
  retain-on-failure`, `screenshot: only-on-failure`.

## Tests (`frontend_merger/tests/smoke.spec.ts`)

| # | Test | Prueft |
|---|---|---|
| 1 | `landing: Agent Testbed loads with 3 surface cards` | `/` lädt, Heading "Agent Testbed", Links zu /matrix + /control, Tambo-Canvas `#tambo-canvas` sichtbar |
| 2 | `top bar: Matrix + Control links + Agent toggle render` | `[data-testid=link-matrix|link-control|link-agent]` alle sichtbar |
| 3 | `agent toggle: Sheet opens via Agent button + closes` | Click → `[role="dialog"]` erscheint, Click → verschwindet |
| 4 | `/matrix: shows config hint without credentials` | Heading "Matrix nicht konfiguriert" (Server-Component, env-lookup failed) |
| 5 | `/control/skills: renders without crash` | HTTP 200, TopBar persistent |
| 6 | `/memory: renders without crash` | HTTP 200, TopBar persistent |
| 7 | `/files: renders without crash` | HTTP 200, TopBar persistent |
| 8 | `tambo canvas placeholder visible on landing` | `#tambo-canvas` + `aria-label="Generative UI canvas"` |

## Ergebnis

```
$ bunx playwright test --project=chromium
Running 8 tests using 1 worker
  8 passed (30.9s)
```

## Wichtiger Befund: Dev-Mode Hydration-Issue

**Alle 8 Tests gehen gegen `bun run start` (Prod-Build). Gegen `bun run dev`
(Turbopack-Dev-Mode) schlaegt Test #3 fehl:**

- Symptom: Agent-Button-Click fuert `onClick` nicht aus. `aria-pressed` bleibt
  false, `[role="dialog"]` erscheint nicht.
- Root Cause: `document.querySelector('[data-testid=link-agent]')` in der VM
  hat **0 React-Fiber Keys** (`__reactFiber*` / `__reactProps*` sind nicht am
  DOM-Element). React hat den Baum **nicht hydratisiert**.
- Nicht gefunden: kein page-error, kein 4xx im Network-Tab, keine Hydration-
  Warning im dev-server log. Nur Websocket-HMR scheitert wegen
  Cross-Origin-Policy (`127.0.0.1` nicht in `allowedDevOrigins`).
- Produktions-Build zeigt das Verhalten **nicht** — Hydration laeuft sauber,
  Click toggelt zustand korrekt.

**Schlussfolgerung:** Dev-Mode-Issue ist Turbopack-/Chunking-spezifisch, nicht
produktiv-relevant. Kein Blocker fuer Release.

**Offen:** Ursache im Dev-Mode final zu diagnostizieren (separater Ticket).
Moegliche Kandidaten: `optimizePackageImports`-Interaktion, Heavy-Tree
Hydration mit 100+ Components unter CopilotKit/Tambo/AG-UI Providern, Turbopack
Chunk-Splitting Latenz in HMR-Phase.

## Wie der User das verifizieren kann

```bash
cd frontend_merger
cp env.example.merger .env.local
bun install
bun run build
bun run start &                            # oder: node .next/standalone/server.js
bunx playwright test --project=chromium
```

Oder gegen Dev-Mode (mit bekanntem Fail bei Test #3):

```bash
bun run dev &
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3003 bunx playwright test
```

## Dateien hinzugefuegt

```
frontend_merger/
├─ playwright.config.ts
└─ tests/smoke.spec.ts
```

`@playwright/test` als devDependency in `package.json` hinzugefuegt.
