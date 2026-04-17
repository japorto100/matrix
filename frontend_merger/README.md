# frontend_merger

Unified shell that mounts the three Matrix-repo frontends under one Next.js app.

This is a **test-harness inside the matrix repo**, not the integration target. The
real integration lives in `tradeview-fusion` (separate repo). The merger exists
so Tambo / CopilotKit / a2ui experiments and the shared `GlobalTopBar` can be
tried out without touching the three isolated apps.

## Layout

```
├─ Top-Bar ────────────────────────────────────────────────────┐
│  [Matrix] [Control]  [Agent ⇄ Sheet]              · clock   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   /        → Landing + Tambo/CopilotKit canvas               │
│   /matrix  → Full-page Matrix Chat (Space-Rail + Timeline)   │
│   /control → Full-page Control UI (Memory / KG / Files)      │
│   /memory  → Memory Browser                                  │
│   /files   → Files Surface                                   │
│                                                               │
│   Agent Chat is a Sheet overlay, not a route. Toggled from   │
│   the TopBar on any page.                                    │
└───────────────────────────────────────────────────────────────┘
```

## Structure

```
frontend_merger/
├─ package.json         # union der deps der drei apps
├─ tsconfig.json        # path aliases @/ @matrix/ @agent/ @control/
├─ biome.json
├─ next.config.ts       # standalone output, WASM fuer matrix rust-crypto
├─ Dockerfile           # Bun build → Node runtime, podman-kompatibel
└─ src/
   ├─ app/
   │  ├─ layout.tsx     # GlobalTopBar + Providers + AgentProviders + GlobalChatOverlay
   │  ├─ page.tsx       # Testbed / Generative-UI canvas
   │  ├─ matrix/        # Matrix-Route
   │  ├─ control/       # Control-Route (catch-all)
   │  ├─ memory/        # Memory-Route
   │  ├─ files/         # Files-Route
   │  └─ api/           # BFF-Routen (agent, audio, matrix, control, files, memory)
   ├─ components/
   │  ├─ GlobalTopBar.tsx
   │  ├─ providers.tsx  # ThemeProvider + QueryClient + NuqsAdapter
   │  └─ ui/            # shadcn primitives (nextjs-chat superset)
   ├─ features/
   │  ├─ agent/         # aus agent-chat/ (ohne ui/)
   │  ├─ matrix/        # aus nextjs-chat/src/{components,lib}/matrix/
   │  ├─ control/       # aus control-ui/src/features/control/
   │  ├─ files/         # aus control-ui/src/features/files/
   │  └─ memory/        # aus control-ui/src/features/memory/
   ├─ hooks/            # use-mobile
   └─ lib/
      ├─ utils.ts       # cn, getErrorMessage, EMOJI_STRIP_RE
      ├─ query-client.ts
      ├─ search-params.ts
      ├─ server/        # gateway, control-proxy, file-audit
      ├─ kg-graph/
      ├─ queries/
      └─ storage/
```

## Dev

```bash
bun install
bun run dev          # http://localhost:3003
bun run typecheck
bun run lint
bun run build
```

Isolierte Apps laufen parallel weiter:
- `nextjs-chat`: 3000
- `control-ui`:  3001
- `agent-chat`:  3002
- `frontend_merger`: **3003**

## Container (podman / docker)

Dockerfile ist podman-kompatibel (kein Docker-spezifisches Feature).

```bash
podman build -t frontend-merger:local .
podman run --rm -p 3003:3003 frontend-merger:local
```

oder docker:

```bash
docker build -t frontend-merger:local .
docker run --rm -p 3003:3003 frontend-merger:local
```

## Env (optional)

```
MATRIX_HOMESERVER_URL=http://localhost:8448
MATRIX_USER_ID=@alice:matrix.local
MATRIX_ACCESS_TOKEN=syt_...
MATRIX_DEVICE_ID=ABCDE
AGENT_GATEWAY_URL=http://localhost:8090
NEXT_PUBLIC_TAMBO_API_KEY=...
```

Ohne Matrix-Credentials zeigt `/matrix` einen Konfigurationshinweis.

## Status

- `bun install`: ✓ 1100+ Pakete
- `tsc --noEmit`: ✓ 0 errors
- `biome check`: ✓ 0 errors
- `bun run build`: ✓ 25 Routen, 16 static pages
- Standalone server: ✓ alle Routen HTTP 200

## Konflikte, die beim Merge aufgeloest wurden

| Paket | Quelle | Entscheidung |
|---|---|---|
| `@tiptap/*` | nextjs-chat ^3.21, control-ui ^3.22 | `~3.21.0` (mentionSuggestion-Typen) |
| `@tiptap/suggestion` | (transitive aus novel@1) | **explicit** `~3.21.0` um novel's 2.x zu ueberstimmen |
| `recharts` | matrix 2.15.4, control ^3.8 | `^3.8.1` (chart.tsx shadcn-wrapper entfernt) |
| `react-resizable-panels` | matrix ^4.7, aktuell 4.10 | v4-Breaking → resizable.tsx entfernt |
| `framer-motion` vs `motion` | matrix hatte beide | nur `motion` (alle Imports nutzen `motion/react`) |
| `lucide-react` | agent 0.525, matrix 1.7 | `^1.7.0` |
| `react-shiki` | agent 0.6, matrix 0.9 | `^0.9.2` |
| shadcn `ui/` primitives | 3x drift | nextjs-chat-Superset (46 Dateien) |
| `D:/matrix/shared` | geloescht am 13.04.2026 | nicht mehr genutzt |

## Was fehlt / nicht Ziel dieses Merges

- Tambo-Playground-UI (Beispiel-Trigger auf der Landing) — folgt
- Nuqs SearchParams Migration fuer Control-Surfaces
- E2E Tests gegen Go Gateway + Python agent-service
