# Frontend Merger — Agentic-Stack Mapping Design

**Date:** 2026-04-21
**Scope:** `frontend_merger/` — how CopilotKit + A2UI v0.9 map to routes, what actions/readables exist where, data-flow, persistence, error handling, testing.
**Related:** exec-09 Generative UI, exec-10 Multi-Agent, exec-15 Memory Control UI, exec-06 Agent Chat Integration.
**Status:** Design approved — awaiting implementation plan.

---

## 1. Goal

Introduce the **agentic frontend stack** (CopilotKit + A2UI v0.9) into `frontend_merger/` as two complementary layers — CopilotKit for *agent ↔ frontend integration* (hooks, actions, chat UI), A2UI for *widget-rendering* (generative UI in chat messages and a standalone main-canvas).

Tambo was removed on this date (2026-04-21) in favour of Google's A2UI v0.9 (launched April 2026), which CopilotKit natively supports (launch-partnership).

**Non-goals:**
- Replacing our existing `AgentChatPanel` (ai-sdk based) with `CopilotChat`/`CopilotSidebar` — we only use CopilotKit hooks, not UI components.
- Consolidating `/files` + `/memory` into `/control` — keeps routes as they are; Files + Memory get TopBar buttons of their own.
- Full live-data-streaming implementation in phase-1 — only the pattern contract.

## 2. Tech Stack (6 packages, all MIT/Apache-2.0, self-host free)

| Package | Role | Notes |
|---|---|---|
| `@copilotkit/react-core` | Provider + hooks (`useCopilotAction`, `useCopilotReadable`) | v1.56.2 — primary runtime binding |
| `@copilotkit/react-ui` | Pre-built chat components (`CopilotChat`, `CopilotSidebar`, `CopilotPopup`, `Markdown`, `Suggestions`, etc.) | v1.56.2 — installed as alternative, **not mounted** in v1; low-level components may be adopted selectively |
| `@copilotkit/runtime` | Next.js API route handler — bridges runtime-URL to LLM / agents | v1.56.2 — used for `/api/copilotkit` |
| `@copilotkit/a2ui-renderer` | A2UI v0.9 renderer (primary): `A2UIProvider`, `A2UIRenderer`, hooks, `basicCatalog` | v1.56.2 — deep integration with CopilotKit chat |
| `@a2ui/react` | Google's official A2UI v0.9 React bindings | v0.9.1 — installed as alternative renderer |
| `@a2ui/web_core` | A2UI v0.9 protocol core (transitive via above, pinned explicitly) | v0.9.2 |

**Not installed:** `@tambo-ai/react` (removed).

## 3. Layer Stack

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. LLM + Orchestration — python-agent + LiteLLM (existing infra) │
│    OpenRouter / provider-agnostic via LiteLLM gateway            │
├──────────────────────────────────────────────────────────────────┤
│ 2. Transport                                                     │
│    (a) SSE /api/agent/chat      — ai-sdk-style, existing         │
│    (b) CopilotKit runtime /api/copilotkit — new, AG-UI protocol  │
├──────────────────────────────────────────────────────────────────┤
│ 3. Agent-Frontend Integration — CopilotKit hooks (NO UI mounted) │
│    useCopilotAction, useCopilotReadable                          │
├──────────────────────────────────────────────────────────────────┤
│ 4. Widget-Rendering — CopilotKit's A2UI renderer                 │
│    A2UIProvider (basicCatalog), A2UIRenderer (per surface)       │
├──────────────────────────────────────────────────────────────────┤
│ 5. Chat UI — existing AgentChatPanel (ai-sdk, custom)            │
│    Mounted via GlobalChatOverlay (Sheet-based)                   │
└──────────────────────────────────────────────────────────────────┘
```

## 4. Provider Hierarchy

```tsx
app/layout.tsx
 └─ <Providers>                        (QueryClient, Theme, etc — existing)
     └─ <CopilotKit runtimeUrl="/api/copilotkit">
         └─ <A2UIProvider catalog={basicCatalog}>
             └─ <GlobalCopilotContext>    (registers global actions + readables)
                 ├─ <GlobalTopBar />
                 ├─ <main>{children}</main>   (per-route actions/readables register here)
                 └─ <GlobalChatOverlay>
                     └─ <AgentChatPanel messageRenderer={A2UIMessageRenderer} />
```

Hierarchical pattern (Ansatz B): global actions in `GlobalCopilotContext`, route-level actions registered in each route's component (unmounted on navigation-away).

## 5. Routes + TopBar

| Route | TopBar Button | Content |
|---|---|---|
| `/` | (Logo → home) | Landing, A2UI main-canvas (`surfaceId="main"`) |
| `/matrix` | **Matrix** (existing) | Matrix-Chat UI |
| `/files` | **Files** (NEW) | File-browser |
| `/memory` | **Memory** (NEW) | Agent-memory + KG |
| `/control` | **Control** (existing) | Admin-console (agents, skills, sessions, tools, security, system, sandbox, audit, mcp, a2a, api) |
| (overlay) | **Agent** (existing) | `GlobalChatOverlay` with `AgentChatPanel` |

**No route consolidation.** Files and Memory stay as independent routes — they serve user-content, not admin/agent-llm concerns that Control addresses.

**GlobalTopBar change:** `NAV_LINKS` array extended with `{ href: "/files", label: "Files", icon: <Files/> }` and `{ href: "/memory", label: "Memory", icon: <Brain/> }`. Uses lucide-react icons.

## 6. Action + Readable Registry

### 6.1 Global (all routes, in `GlobalCopilotContext`)

**Actions:**
- `navigateTo(route: string)` — programmatic navigation (agent says "go to control/agents")
- `toggleAgentSidebar()` — open/close GlobalChatOverlay

**Readables:**
- `currentRoute` → `{ pathname, segment, subtab }` from `useCurrentRoute()` hook
- `currentChatAttachments` → list of files user currently attached in AgentChatPanel (for "save" flow)

### 6.2 Landing (`/`)

No route-level actions. A2UI main-canvas does the rendering — agent streams widget-tree directly.

### 6.3 Files (`/files`)

**Actions:**
- `saveAttachmentToStorage(attachmentId: string)` — move an attachment from chat-state to blob-storage (garage) and refetch file-list

**Readables:**
- `recentFiles` → top 10 files (id, name, mime, size) so agent can reference them

**User context-menu on FileCard:**
- **"Add to Chat"** — calls `globalChat.openChat(ctx={type:"file", id})` — injects file-context into AgentChatPanel

**Deferred (user said not needed, agent can do via prompt):** summarize, tag, delete, show-in-KG, upload-from-url.

### 6.4 Memory (`/memory`)

Phase-1: readable `selectedMemoryNode` for agent-awareness. Actions deferred.

### 6.5 Control (`/control`)

**Actions:**
- `openControlTab(tab: string)` — agent sends user to `/control/<tab>` (agents/skills/sandbox/etc.)

**Readables:**
- `activeControlTab` → parsed from pathname

## 7. Data Flow (4 Flows)

### Flow A — Chat text (baseline, no widget)
```
User types → ai-sdk /api/agent/chat (SSE)
  → python-agent: LLM via LiteLLM → text_delta packets
  → AgentChatPanel renders progressively
```

### Flow B — Chat widget (A2UI inline)
```
User: "Show NVDA chart"
  → ai-sdk /api/agent/chat (SSE)
  → python-agent: LLM with A2UI system-prompt + catalog
  → Output: A2UI v0.9 messages (beginRendering / updateComponents / updateDataModel / endRendering)
  → AgentChatPanel detects A2UI parts → dispatch via useA2UIActions
  → A2UIProvider updates state for surfaceId = "chat-msg-<id>"
  → A2UIMessageRenderer renders Card/Chart inline in message bubble
```

### Flow C — Dashboard widget (A2UI standalone main-canvas, persistent)
```
User: "Build me a trading dashboard" (or useCopilotAction trigger)
  → CopilotKit runtime /api/copilotkit → python-agent
  → python-agent streams A2UI v0.9 messages targeting surfaceId = "main"
  → A2UIProvider dispatches
  → A2uiCanvas on `/` renders Surface
  → usePersistentSurface hook persists:
    (a) localStorage synchronously (instant re-display on page load)
    (b) Postgres async (cross-device via /api/surfaces/{surfaceId})
```

### Flow D — Frontend action (CopilotKit hook)
```
User: "Open Control > Agents"
  → Agent (via LLM) selects: action=openControlTab, args={tab:"agents"}
  → CopilotKit runtime forwards action to frontend
  → useCopilotAction handler: router.push("/control/agents")
  → Route-change — no LLM output rendered; action returns { navigated: true } to agent
```

### Channels

- Flows A/B → `/api/agent/chat` (existing ai-sdk SSE, may need a2ui_part parsing)
- Flows C/D → `/api/copilotkit` (new CopilotKit runtime endpoint with LiteLLM-proxy adapter)

## 8. Persistence Pattern (widget-tree ≠ live-data)

### 8.1 Widget-Tree (structure) — persistent

- **Storage:** Postgres (source of truth) + localStorage (fast cache)
- **Table:** `agent.user_surfaces(user_id, surface_id, surface_json, schema_version, updated_at)`
- **Migration:** `python-backend/alembic/versions/027_user_surfaces.py`
- **Routes:** `/api/surfaces/[surfaceId]/route.ts` (GET, PUT)
- **Hook:** `usePersistentSurface(surfaceId)` — subscribes to A2UI state, writes to localStorage sync + Postgres async
- **Conflict:** last-write-wins
- **Schema-drift guard:** `schemaVersion` in stored JSON; mismatch → localStorage drop, fresh-start, silent

### 8.2 Live Data — NOT persisted, live-streamed

Two patterns supported:

**Pattern L1: Agent-driven updates (A2UI-native)**
- Agent opens long-running SSE/WebSocket
- Emits periodic `updateDataModel` messages (per A2UI v0.9 spec)
- A2UI data-bindings auto-update — no component re-render needed, only bound paths react

**Pattern L2: Client-side live-source (TanStack Query v5)**
- Widget data-binding references a client-side query-key
- Example:
  ```json
  {
    "type": "Chart",
    "dataSource": { "type": "sse", "url": "/api/prices/stream?symbol=NVDA" }
  }
  ```
- A2UI renderer resolves `dataSource` at runtime — opens SSE via `useQuery` + `experimental_streamedQuery` (TanStack v5)

**MVP scope:** only static-data widgets (snapshot from agent). Patterns L1/L2 implemented in phase-2.

## 9. Error Handling (CopilotKit-native where possible)

### 9.1 Failure modes

1. **Backend down / python-agent unreachable** — CopilotKit returns `error` event; we toast + disable actions; A2UI surfaces from localStorage remain visible
2. **Malformed A2UI JSON** — `A2UIRenderer fallback` prop catches; unknown widget-type renders "Unknown widget: <name>"; malformed JSON parsed-with-skip in SSE-consumer
3. **Action-handler exception** — wrapped; returns `{ error: msg }` to agent (via CopilotKit), agent can retry or apologise in chat; toast for user
4. **Persistence / schema-drift** — schema-version check on load, fail-safe fresh-start; background-retry queue for failed Postgres-writes

### 9.2 Leveraging built-in

- `onCopilotError` provider-level handler (from `@copilotkit/react-core`) — central error-stream subscription
- CopilotKit streams `event: "error"` and `on_copilotkit_error` events from runtime
- `CopilotDevConsole` (from `@copilotkit/react-ui`) optional in dev for debugging
- A2UI Renderer `fallback` and `onRenderError` props

### 9.3 Graceful degradation

```
Full failure (backend + cache both dead)
  → UI renders minimal: TopBar + Landing + static cards
  → AgentChatPanel shows "Agent offline"
  → A2uiCanvas shows idle fallback
  → User can navigate between routes; routes load their own features
```

**Goal:** no whitescreen, no endless spinner, no uncaught exception. App always navigable.

## 10. Components to Build / Modify

### New files

| Path | Purpose |
|---|---|
| `src/features/agent/providers/GlobalCopilotContext.tsx` | Global `useCopilotAction(navigateTo, toggleAgentSidebar)` + `useCopilotReadable(currentRoute, currentChatAttachments)` |
| `src/features/agent/components/A2uiMessageRenderer.tsx` | `createA2UIMessageRenderer({theme})` wrapper — plugs into AgentChatPanel |
| `src/features/agent/hooks/useCurrentRoute.ts` | Returns `{pathname, segment, subtab}` |
| `src/features/agent/hooks/usePersistentSurface.ts` | localStorage + Postgres sync for A2UI surfaces |
| `src/app/api/copilotkit/route.ts` | CopilotKit runtime endpoint (OpenAIAdapter → LiteLLM :4000) |
| `src/app/api/surfaces/[surfaceId]/route.ts` | GET/PUT persistent surface JSON |
| `python-backend/alembic/versions/027_user_surfaces.py` | `agent.user_surfaces` table |

### Modified files

| Path | Change |
|---|---|
| `src/app/layout.tsx` | Wrap with `<CopilotKit runtimeUrl>`; `@copilotkit/react-ui/styles.css` imported |
| `src/features/agent/providers/AgentProviders.tsx` | Nest `<A2UIProvider>` inside `<CopilotKit>` conditional |
| `src/features/agent/AgentChatPanel.tsx` | Wire `messageRenderer={A2UIMessageRenderer}` |
| `src/app/page.tsx` | `<A2uiCanvas surfaceId="main" />` (already done) |
| `src/features/control/ControlPage.tsx` | `useCopilotReadable(activeControlTab)` + `useCopilotAction(openControlTab)` |
| `src/features/files/FilesPage.tsx` | `useCopilotAction(saveAttachmentToStorage)` + `useCopilotReadable(recentFiles)` |
| `src/features/files/components/FileCard.tsx` | Context-menu: "Add to Chat" |
| `src/components/GlobalTopBar.tsx` | `NAV_LINKS` extended with Files + Memory |

### Packages

Already installed — no `bun add` needed:
- `@copilotkit/react-core`, `-react-ui`, `-runtime`, `-a2ui-renderer`
- `@a2ui/react`, `@a2ui/web_core`

## 11. Testing Strategy

### Unit (Vitest)
- `GlobalCopilotContext.test.tsx` — action-registration calls correct args
- `useCurrentRoute.test.ts` — pathname segmentation
- `A2uiMessageRenderer.test.tsx` — renders from JSON, unknown-widget → fallback
- `usePersistentSurface.test.ts` — localStorage R/W, schema-version mismatch → fresh-start

### Component (Vitest + React Testing Library)
- `A2uiCanvas.test.tsx` — fallback when no surface, renders when dispatched
- `AgentChatPanel.test.tsx` — A2UI-part message renders widget inline
- `FileCard.test.tsx` — "Add to Chat" context-menu triggers `globalChat.openChat`

### Integration (MSW)
- `api/copilotkit/route.test.ts` — POST → mock-LiteLLM → CopilotKit wire format
- `api/surfaces/save.test.ts` — PUT with schema-version → 200

### E2E (Playwright) — extend existing 8 tests

New tests:
- **#9** `[Files]` + `[Memory]` buttons visible + navigate correctly
- **#10** Landing `<A2uiCanvas>` idle-state renders placeholder
- **#11** Chat message with mock A2UI-part renders widget (mock SSE)
- **#12** File-card context-menu → "Add to Chat" → chat opens with chip

### Manual smoke (in VERIFY-GATES.md)

- Phase 1: provider setup (0 console errors, tree has providers)
- Phase 2: actions (mock-mode — navigate, toggle-sidebar)
- Phase 3: widget rendering (mock SSE → A2UI widget)
- Phase 4: persistence (widget survives reload via localStorage)
- Phase 5: file-actions (attach PDF → "save" → visible in /files; "Add to Chat" → context injected)

### Priority

**Must-have before merge:** existing 8 Playwright tests still green + new #9 + #10; manual Phase 1 + Phase 3.
**Nice-to-have:** #11 + #12, manual Phase 4 + 5, integration tests.
**Skip for MVP:** live-data patterns (L1/L2) — pattern contract only, no implementation.

## 12. Implementation Sequence

1. **Provider hierarchy** — CopilotKit + A2UI wrapping in layout (low-risk, typecheck-guard)
2. **GlobalCopilotContext** — action/readable registration (global only)
3. **A2uiMessageRenderer** integration in AgentChatPanel
4. **TopBar: Files + Memory buttons**
5. **FileCard: "Add to Chat" context-menu**
6. **Files-page: save-attachment action + recentFiles readable**
7. **Control-page: openControlTab action + activeControlTab readable**
8. **Main-canvas A2uiCanvas** (already done)
9. **Persistent surface hook + /api/surfaces BFF-route** + Alembic migration
10. **CopilotKit runtime /api/copilotkit route** (OpenAIAdapter → LiteLLM)
11. **Tests** (unit + E2E incremental as features land)

## 13. Out-of-Scope (explicit)

- Matrix-chat integration with CopilotKit (phase-2, exec-10 territory)
- Live-data streaming implementation (pattern contract only, phase-2)
- Agent-side a2ui-agent-sdk (python) wiring — tracked in exec-09 Python side
- Custom A2UI widget-catalog beyond `basicCatalog` (phase-2, when live-data patterns land)
- User-auth integration with CopilotKit (uses our existing Matrix auth)
- Route consolidation (`/files`, `/memory` stay root-level)
- Replacing AgentChatPanel with CopilotSidebar/Chat (user prefers custom chat)

## 14. Risks + Open Questions

| Risk | Mitigation |
|---|---|
| CopilotKit runtime adapter complexity (custom vs OpenAIAdapter) | Start with OpenAIAdapter + LiteLLM baseURL — covers 90% of cases |
| A2UI v0.9 is new (launched April 2026) — API churn risk | Pin to v0.9.x, monitor upstream for breaking changes |
| AG-UI protocol handshake between CopilotKit and python-agent | Python-agent needs to conform to AG-UI spec for `/api/copilotkit` path; ai-sdk path (`/api/agent/chat`) stays as-is |
| Schema-version drift in persisted surfaces | `schemaVersion` field + drop-on-mismatch |
| Live-data patterns unspecified in A2UI docs | Defer to phase-2; start with static widgets only |
| `@copilotkit/react-ui` styles.css conflict with globals.css | Import order: `react-ui/styles.css` BEFORE `globals.css` (done) |

## 16. Deep-Dive Findings (Addendum 2026-04-21)

After writing the initial spec, a deep-dive through `frontend_merger/`, `go-appservice/`, and `python-backend/` revealed concrete current-state that affects implementation choices. Addendum rather than rewrite, because the overall mapping is still sound.

### 16.1 Python-Agent SSE Packet Format (existing)

`python-backend/agent/streaming.py` defines the **Vercel AI-SDK v6 Data-Stream-Protocol** packets:

- `thread-id` — session identifier
- `text-start` / `text-delta` / `text-end` — progressive text
- `tool-start` / `tool-result` / `tool-error` — tool execution
- `step-start` — graph-step marker
- `reasoning-delta` — chain-of-thought tokens
- `message-meta` — metadata (tokens, usage)
- `finish` / `error` / `approval-request` — terminal states

**No `a2ui-part` or `widget-update` packet exists.** SSE response-header is `text/event-stream` with `x-vercel-ai-ui-message-stream: v1` (set by BFF route `frontend_merger/src/app/api/agent/chat/route.ts`).

**Endpoint:** `POST /api/v1/agent/chat` in `python-backend/agent/app.py:605`, returning `StreamingResponse` via `_stream_agent_loop`.

### 16.2 Go-Appservice Proxy Layer (existing)

`go-appservice/internal/handler/server.go:111-146` mounts:

- `/api/v1/agent/chat` → proxy to python-agent
- `/api/v1/agent/approve` — HITL approval
- `/api/v1/agent/tools/chart-state` — GET chart data
- `/api/v1/agent/tools/portfolio-summary` — GET portfolio data
- `/api/v1/agent/tools/set_chart_state` — PUT chart-state mutation
- `/api/v1/mcp/*` — MCP tool-proxy
- `/api/v1/control/*` — Control-UI proxy
- `/api/v1/memory/*` — Memory-KG endpoints (seed, query, nodes, sync, episode, episodes, search, health)

**No `/api/copilotkit` endpoint** — must be added. Placement options:
- (a) In go-appservice (Go proxy layer — consistent with existing `/api/v1/*`)
- (b) In Next.js BFF (`frontend_merger/src/app/api/copilotkit/route.ts` — closer to CopilotKit-runtime lib)

Recommendation: **(b)** — CopilotKit-runtime is JS/TS-native (`@copilotkit/runtime`), lives naturally in Next.js. Go-appservice remains protocol-agnostic.

### 16.3 Existing Tool-Output → Widget Pattern (in frontend)

`frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx` already maps tool-names to React components:

```ts
const TOOL_RENDERERS = {
  get_chart_state:     ChartWidget,     // from a2ui/ChartWidget (ex-tambo/)
  get_portfolio_summary: PortfolioCard,  // from a2ui/PortfolioCard
  sandbox_execute:     SandboxArtifact, // exec-12
  file_analyze:        SandboxArtifact, // exec-12
};
```

**Implication:** We have the "agent emits → rich widget" pattern already. Tambo-removal preserved the widgets; A2UI just extends the rendering target.

### 16.4 No Prior A2UI or CopilotKit Integration

Grep confirmed: no `a2ui-agent-sdk` in python-backend, no `@copilotkit/*` imports outside of the just-installed provider/renderer files. This is a **greenfield addition**, not a migration.

**Implication:** No legacy API-contracts to preserve; we can pick the cleanest pattern.

## 17. A2UI Integration: Ansatz X vs. Y

Two ways to carry A2UI-widget-messages from python-agent to frontend:

### Ansatz X — New packet-types (SOTA, first-class A2UI)

Add new dataclasses to `python-backend/agent/streaming.py`:

```python
@dataclass
class A2UISurfaceStartPacket:
    surface_id: str
    catalog: str = "basic"
    type: Literal["a2ui-surface-start"] = "a2ui-surface-start"

@dataclass
class A2UIUpdateComponentsPacket:
    surface_id: str
    components: dict  # A2UI component-tree JSON
    type: Literal["a2ui-update-components"] = "a2ui-update-components"

@dataclass
class A2UIUpdateDataModelPacket:
    surface_id: str
    path: str         # JSONPath
    value: dict       # JSON value
    type: Literal["a2ui-update-data-model"] = "a2ui-update-data-model"

@dataclass
class A2UISurfaceEndPacket:
    surface_id: str
    type: Literal["a2ui-surface-end"] = "a2ui-surface-end"
```

Frontend SSE-parser (`useChatSession`) must recognize these types and dispatch to `A2UIProvider` via `useA2UIActions`. Cleaner separation, A2UI is first-class stream citizen.

- **Pros:** SOTA 2026 pattern; direct A2UI v0.9 spec mapping; no tool-dispatch overhead; streamable diffs for live-data
- **Cons:** More python + frontend code; two parallel "render paths" (text + A2UI)
- **Effort:** 5-10 files touched

### Ansatz Y — A2UI-via-tool-result (incremental, minimal diff)

Agent emits A2UI-tree as the **`output` of a virtual tool-call** `render_a2ui_surface`:

```python
# In agent loop:
yield sse(ToolStartPacket(tool_name="render_a2ui_surface", tool_call_id=uuid4()))
yield sse(ToolResultPacket(
    tool_call_id=tcid,
    result={"type": "a2ui", "surface_id": "main", "tree": {...}}
))
```

Frontend `ToolOutputRenderer` gets extended: when `tool_name == "render_a2ui_surface"` → `<A2UIRenderer surfaceId={result.surface_id} inlineTree={result.tree} />`.

- **Pros:** Reuses existing tool-infrastructure; one render-path; minimal diff; no SSE-parser changes
- **Cons:** "Virtual tool" is a semantic hack; updateDataModel for live-data requires new packet-types anyway (bandaid; can't stream incremental updates cleanly)
- **Effort:** 2-3 files touched

### Recommendation: Hybrid

**Phase-1 (this implementation):** Ansatz Y for static widgets (MVP).
- Reuses `ToolOutputRenderer`
- Python-agent emits tree as tool-result
- Works out-of-the-box with `A2UIRenderer`'s `fallback` component

**Phase-2 (when live-data lands):** Migrate to Ansatz X for streaming.
- Add `a2ui-*` packet-types
- Frontend SSE-parser dispatches via `useA2UIActions`
- `updateDataModel` packets enable live price/metric updates

This keeps initial diff small, defers complexity to when it's needed, and the Phase-2 migration is additive (new packet-types alongside existing). §12 implementation-sequence adjusts accordingly.

### 17.1 Updated §12 Implementation Sequence (applying Y-first)

Revised steps (replace original §12):

1. **Provider hierarchy** — CopilotKit + A2UI wrap in `layout.tsx` + env-gated
2. **GlobalCopilotContext** — global `useCopilotAction/Readable`
3. **A2uiMessageRenderer** wired into `AgentChatPanel` (ingest-point for A2UI-tool-result)
4. **ToolOutputRenderer extension** — new case `tool_name === "render_a2ui_surface"` → A2UIRenderer with inline tree
5. **TopBar: Files + Memory buttons**
6. **Python-agent: add system-prompt A2UI-catalog-awareness** — python side doesn't need new SDK yet; LLM is instructed to emit A2UI-trees via existing tool-output channel
7. **FileCard "Add to Chat" context-menu**
8. **Files-page: `saveAttachmentToStorage` action + `recentFiles` readable**
9. **Control-page: `openControlTab` action + `activeControlTab` readable**
10. **`/api/copilotkit` runtime endpoint** — Next.js BFF, `OpenAIAdapter` + LiteLLM `baseURL`
11. **Persistent surface hook + `/api/surfaces/[surfaceId]` BFF** + Alembic migration `027_user_surfaces`
12. **Main-canvas A2uiCanvas** (already done; surface-dispatch from agent still Y-pattern)
13. **Tests** — unit + E2E incremental
14. **(Phase-2) A2UI native packet-types + SSE-parser-extend** — only when live-data patterns needed

## 18. Addendum 2 — Frontend/Backend Clarification + Gitnexus Findings

After gitnexus reindex (21250 symbols, 300 execution flows), targeted queries surfaced additional current-state details. Also resolves a conceptual clarification requested mid-design.

### 18.1 Frontend- vs. Backend-Split of the 6 Packages

The 6 packages are **primarily frontend tools** — not "backend tools". Only `@copilotkit/runtime` lives backend-side (as a thin BFF-proxy), nothing else.

| Package | Side | Role |
|---|---|---|
| `@copilotkit/react-core` | **Frontend** | React provider + hooks |
| `@copilotkit/react-ui` | **Frontend** | UI components (CopilotChat, Sidebar, Popup, Markdown) |
| `@copilotkit/a2ui-renderer` | **Frontend** | Consumes A2UI JSON → React widgets |
| `@a2ui/react` | **Frontend** | Google A2UI renderer (alternative) |
| `@a2ui/web_core` | **Frontend** | A2UI protocol parsing + state |
| `@copilotkit/runtime` | **Backend (Next.js BFF)** | Thin proxy/adapter to LLM/agent — no logic |
| `a2ui-agent-sdk` (python, NOT installed) | Backend | Helper for agent-side widget-JSON emission (deferred to phase-2) |

**The agent "brain" stays in python-agent.** CopilotKit + A2UI are the lingua franca between the brain and the user's browser.

### 18.2 Python-Agent Runner Duality (gitnexus finding)

Two runners exist, selected by `agent/runners/dispatcher.py` via `AGENT_USE_LANGGRAPH` env:

- `python-backend/agent/graph/runner.py:run_agent_loop` — LangGraph StateGraph runner (default in dev)
- `python-backend/agent/runners/simple.py:run_simple_agent_loop` — legacy simple-loop fallback

**Implication for A2UI-emission (Ansatz Y):** The virtual tool-result `render_a2ui_surface` needs to work in **both runners** — emitted via `ToolResultPacket` from the streaming layer that both runners share (`python-backend/agent/streaming.py`). No runner-specific code needed; streaming-layer extension covers both.

### 18.3 Go-Appservice Proxy Test Coverage (gitnexus finding)

`go-appservice/internal/handlers/http/agent_chat_handler_test.go` covers:
- `TestAgentChatHandler_MethodNotAllowed`
- `TestAgentChatHandler_ProxiesSSEStream` (SSE pass-through)

**Implication:** SSE-proxy pattern is production-ready and tested. Flow B (Chat-Widget-Antwort) can ride on existing `/api/v1/agent/chat` → no Go-side changes needed if A2UI-packets are sent as `ToolResultPacket` (transparent to proxy).

**New `/api/copilotkit` endpoint lives in Next.js BFF only**, not in Go — consistent with §16.2 recommendation.

### 18.4 Archive-Code Duplicates (ignore during implementation)

Gitnexus finds duplicates of `ToolOutputRenderer.tsx` and related files in `archive/agent-chat/*` and `archive/nextjs-chat/*`. These are **pre-merger legacy** and **must NOT be touched** — modifications to frontend_merger only.

**Implication:** Grep-based refactors must exclude `archive/` directory explicitly.

### 18.5 TradingTool Base-Class Pattern (python-agent)

`python-backend/agent/tools/base.py:TradingTool` is the abstract base for all agent-side tools. Existing pattern:

```python
class TradingTool(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str: ...
    @abc.abstractmethod
    async def execute(self, ...) -> dict: ...
```

Tools are registered via `agent/tools/registry.py:ToolRegistry`.

**Implication for Ansatz Y:** The virtual `render_a2ui_surface` tool should extend `TradingTool` for consistency. Its `execute()` returns `{"type": "a2ui", "surface_id": ..., "tree": ...}`. No new tool-infrastructure needed.

## 19. Updated §12/§17.1 Implementation Sequence (final)

Combining all clarifications:

1. **Provider hierarchy** — `layout.tsx` wraps children with `<CopilotKit runtimeUrl>` (env-gated) → `<A2UIProvider catalog={basicCatalog}>` → `<GlobalCopilotContext>`
2. **GlobalCopilotContext** — `useCopilotAction(navigateTo, toggleAgentSidebar)` + `useCopilotReadable(currentRoute, currentChatAttachments)`
3. **A2uiMessageRenderer** — wired into `AgentChatPanel` as ingest-point for A2UI-tool-result (via existing `ToolOutputRenderer` extension, NOT new SSE-parser)
4. **ToolOutputRenderer extension** — new case `tool_name === "render_a2ui_surface"` → delegates to `<A2UIRenderer surfaceId={result.surface_id} inlineTree={result.tree} fallback={WidgetError}/>`
5. **TopBar: Files + Memory buttons** — `GlobalTopBar.tsx` NAV_LINKS extended
6. **Python-agent tool registration** — new `RenderA2uiSurfaceTool(TradingTool)` in `python-backend/agent/tools/a2ui_surface.py`, registered via `ToolRegistry`. System-prompt gets A2UI-catalog-awareness (which widgets exist, how to emit).
7. **FileCard "Add to Chat"** — context-menu item triggers `globalChat.openChat({type:"file", id})`
8. **Files-page actions** — `useCopilotAction(saveAttachmentToStorage)` + `useCopilotReadable(recentFiles)` in `FilesPage.tsx`
9. **Control-page actions** — `useCopilotAction(openControlTab)` + `useCopilotReadable(activeControlTab)` in `ControlPage.tsx`
10. **`/api/copilotkit` runtime endpoint** — Next.js BFF `src/app/api/copilotkit/route.ts` using `@copilotkit/runtime` `CopilotRuntime` + `OpenAIAdapter` with `baseURL=http://localhost:4000` (LiteLLM gateway). Provider-agnostic via LiteLLM.
11. **Persistent surface infrastructure** — `usePersistentSurface` hook + `/api/surfaces/[surfaceId]` BFF (GET/PUT) + Alembic migration `027_user_surfaces` (python-backend)
12. **Main-canvas** — `<A2uiCanvas surfaceId="main" />` on `/` (done ✓), integrates with persistent surface hook
13. **Tests** — Playwright #9-#12 + Vitest unit/component for new hooks/components, incremental as features land
14. **(Phase-2 / deferred)** — native A2UI SSE-packets (`a2ui-surface-start/update-components/update-data-model/end`) when live-data-streaming becomes necessary; `a2ui-agent-sdk` python install; A2UI-catalog-extension via `createReactComponent`

### Non-touched (explicit)

- `archive/agent-chat/*`, `archive/nextjs-chat/*` — ignore
- `/matrix` route — out-of-scope, phase-2
- Go-appservice — no changes; existing proxy handles SSE transparently

## 15. References

- A2UI v0.9 spec: https://a2ui.org/specification/v0.9-a2ui/
- A2UI data-flow: https://a2ui.org/concepts/data-flow/
- CopilotKit vs A2UI (layer-stack): https://www.copilotkit.ai/blog/ag-ui-and-a2ui-explained-how-the-emerging-agentic-stack-fits-together
- CopilotKit + A2UI build-guide: https://www.copilotkit.ai/blog/build-with-googles-new-a2ui-spec-agent-user-interfaces-with-a2ui-ag-ui
- Google A2UI announcement: https://developers.googleblog.com/a2ui-v0-9-generative-ui/
- exec-09 Protocols + Generative UI: `specs/execution/exec-09-protocols-generative-ui.md`
- exec-10 Multi-Agent Orchestrator (ownership, cross-access): `specs/execution/exec-10-multi-agent.md`
