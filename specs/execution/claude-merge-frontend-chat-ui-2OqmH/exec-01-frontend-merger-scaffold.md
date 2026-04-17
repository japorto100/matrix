# exec-01: frontend_merger Scaffold

**Datum:** 17.04.2026
**Status:** ✓ done
**Commit:** `0ba9524` feat(frontend_merger): scaffold unified shell for Matrix + Agent + Control UIs

## Warum

Drei isolierte Next.js Apps (`nextjs-chat`, `agent-chat`, `control-ui`) existieren
parallel im Repo. Fuer `tradeview-fusion` Integration brauchen wir einen
Test-Harness, in dem alle drei unter einer Shell laufen — **bevor** sie ins
Hauptprojekt wandern. Ausserdem Testbed fuer Tambo / CopilotKit / a2ui
Generative-UI Experimente.

Erweitert/ersetzt nicht: `specs/execution/exec-06-agent-chat-integration.md`
und `exec-merge-chat.md`. Diese sind weiterhin die "echten" Integrations-Specs
fuer tradeview-fusion. `frontend_merger/` ist ein Scouting-Tool im matrix-Repo.

## Was gebaut wurde

### Struktur

```
frontend_merger/
├─ package.json              # Union der Deps aller 3 Apps, Versionskonflikte aufgeloest
├─ tsconfig.json             # Path-Aliases @/*, @matrix/*, @agent/*, @control/*
├─ biome.json
├─ next.config.ts            # standalone output, WASM fuer matrix rust-crypto
├─ next-env.d.ts
├─ components.json           # shadcn config
├─ tailwind.config.ts
├─ postcss.config.mjs
├─ Dockerfile                # podman-kompatibel (oven/bun builder + node runtime)
├─ .dockerignore
├─ .gitignore
├─ env.example.merger        # siehe exec-02
├─ README.md
├─ bun.lock
├─ playwright.config.ts
├─ tests/smoke.spec.ts       # siehe exec-04
└─ src/
   ├─ app/
   │  ├─ layout.tsx          # GlobalTopBar + Providers + AgentProviders + GlobalChatOverlay
   │  ├─ page.tsx            # Landing + Generative-UI Canvas
   │  ├─ globals.css         # Merge aus matrix+control globals (inkl. Memory-KG Tokens)
   │  ├─ matrix/page.tsx
   │  ├─ control/[[...tab]]/page.tsx
   │  ├─ memory/[[...tab]]/page.tsx
   │  ├─ files/[[...tab]]/page.tsx
   │  └─ api/                # Union der BFF-Routen
   │     ├─ agent/{chat,approve,completion,models}/
   │     ├─ audio/{synthesize,transcribe}/
   │     ├─ matrix/{credentials,media}/
   │     ├─ control/[...path]/
   │     ├─ files/{[id],overview,search,upload-intent,...}/
   │     └─ memory/[...path]/
   ├─ components/
   │  ├─ GlobalTopBar.tsx    # [Matrix] [Control] Links + [Agent] Sheet-Toggle
   │  ├─ providers.tsx       # ThemeProvider + QueryClient + NuqsAdapter
   │  └─ ui/                 # 43 shadcn primitives (nextjs-chat Superset)
   ├─ features/
   │  ├─ agent/              # aus agent-chat/ (ohne ui/, lib/server/)
   │  │  ├─ AgentChatPanel.tsx, SplitChatShell.tsx, types.ts
   │  │  ├─ components/{AgentChat*, GlobalChatOverlay, tambo/, canvas/, artifacts/}
   │  │  ├─ hooks/{useChatSession,useAgentVoice,useMcpTools,useWebMcp*,...}
   │  │  ├─ context/atoms.ts
   │  │  ├─ lib/{frontend-tools,webmcp-polyfill,providers,...}
   │  │  ├─ providers/AgentProviders.tsx  # CopilotKit + TamboProvider
   │  │  └─ stores/globalChatStore.tsx     # Zustand: open/mode/badgeCount
   │  ├─ matrix/             # aus nextjs-chat/src/{components,lib}/matrix/
   │  ├─ control/            # aus control-ui/src/features/control/
   │  ├─ files/              # aus control-ui/src/features/files/
   │  └─ memory/             # aus control-ui/src/features/memory/
   ├─ hooks/use-mobile.tsx
   └─ lib/
      ├─ utils.ts            # cn(), getErrorMessage(), EMOJI_STRIP_RE
      ├─ query-client.ts
      ├─ search-params.ts
      ├─ server/{gateway,control-proxy,file-audit}.ts
      ├─ kg-graph/
      ├─ queries/
      └─ storage/
```

### Design-Entscheidungen

1. **Agent = Sheet-Overlay, nicht Route.** Der `[Agent]`-Button in der TopBar
   togglet `GlobalChatOverlay` (Sheet / Split / Rail via `globalChatStore`
   Zustand) — funktioniert auf *jeder* Seite (inkl. Landing, /matrix,
   /control). Matrix + Control sind dagegen eigene Fullscreen-Routen.

2. **Landing als Generative-UI Canvas.** `src/app/page.tsx` ist bewusst leer
   gehalten — `#tambo-canvas` Drop-Zone fuer Tambo `ChartWidget` /
   `PortfolioCard` + CopilotKit `a2ui-renderer`.

3. **Separate AgentProviders an der Wurzel.** `AgentProviders` (CopilotKit
   + TamboProvider) wrappt die ganze App, damit Tambo-Components auf jeder
   Route rendern koennen (nicht nur im Agent-Sheet selbst).

4. **Path-Rewriting beim Copy.** Alle `@/` Imports, die innerhalb eines
   Source-Projekts zeigten, wurden auf `@agent/*`, `@matrix/*`, `@control/*`
   umgeschrieben. `@/components/ui/*` und `@/lib/utils` bleiben merger-root-Ziele.

### Versionskonflikte aufgeloest

| Paket | Konflikt | Entscheidung |
|---|---|---|
| `@tiptap/*` | nextjs-chat ^3.21, control-ui ^3.22 | `~3.21.0` (mentionSuggestion-Typen) |
| `@tiptap/suggestion` | novel@1 zog 2.27.2 transitiv rein | **explicit** `~3.21.0` |
| `framer-motion` vs `motion` | matrix hatte beide | nur `motion` (alle Imports via `motion/react`) |
| `lucide-react` | 0.525 / 1.7 | `^1.7.0` |
| `recharts` | 2.15.4 exact vs ^3.8.1 | `^3.8.1` — `chart.tsx`/`resizable.tsx`/`sidebar.tsx` shadcn-wrapper entfernt (v2-API) |
| `react-shiki` | 0.6 / 0.9 | `^0.9.2` |
| `@formkit/auto-animate` | 0.8 / 0.9 | `^0.9.0` |

### Nicht Teil von diesem Scaffold

- `features/shared_chat/` — vom User explizit uebersprungen, Matrix/Agent
  Overlap minimal.
- Microsoft Semantic-Kernel / Adaptive-Cards — **nicht** in deps, Tambo +
  CopilotKit a2ui-renderer decken Generative-UI ab.
- PR-Erstellung — warte auf User-OK.

## Verify

Siehe `exec-04-playwright-verify.md`. Zusammenfassung:

- `bun install`           ✓ 1100+ Pakete
- `tsc --noEmit`          ✓ 0 Fehler
- `biome check`           ✓ 0 Fehler
- `bun run build`         ✓ 25 Routen, 16 static pages, standalone
- `node server.js`        ✓ HTTP 200 auf /, /matrix, /control/skills, /memory, /files
- Playwright smoke (prod) ✓ 8/8
- `docker build`          – Docker-Daemon nicht startbar in dev-VM, aber
                            Standalone-Bundle via Node verifiziert →
                            identischer Code-Pfad wie Container-Runtime.

## Referenzen

- `specs/execution/exec-06-agent-chat-integration.md` — Integrations-Spec fuer tradeview-fusion
- `specs/execution/exec-merge-chat.md` — Dual-Panel-Layout Spec
- `frontend_merger/README.md` — Benutzer-facing Doku
