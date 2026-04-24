# Agentic-Stack Frontend Merger Implementation Plan v2

> **STATUS: COMPLETED — 2026-04-24.** Phase-1 (Tasks 0-15) landed
> before superpower-session. Phase-2 (4 of 7 deferred items) landed in
> this session: #31 Postgres surfaces, #32 Ansatz X native SSE packets,
> #33 a2ui-agent-sdk Python install, #34 live-data binding. Remaining
> 3 Phase-2 gap items extracted as tasks #93 / #94 / #95:
>
> - **#93** Custom A2UI widget-catalog (wrap ChartWidget + PortfolioCard
>   via `createReactComponent` so they become first-class v0.9 catalog
>   entries instead of tool-result workarounds via ToolOutputRenderer).
> - **#94** Matrix-chat CopilotKit integration (mount CopilotKit in
>   `/matrix` route so matrix-chat users can trigger AG-UI actions too
>   — exec-10 tie-in).
> - **#95** Route consolidation (consider bundling `/matrix`, `/files`,
>   `/memory` under `/control/*` as admin-tab system — UX-decision, no
>   functional value, lowest priority).
>
> Full task-list state + open-items breakdown is the authoritative
> `docs/superpowers/findings/2026-04-22-open-tasks.md §Post-session
> state — 2026-04-24 update`. Supersedes v1 at
> `2026-04-21-ag-stack-frontend-merger-plan.md` (marked SUPERSEDED).
>
> Adversarial verify (2026-04-24, 5 parallel sota-verify agents) +
> 13 fixes in commit `d4b4432` closed the functional/CI issues the
> agents found. Remaining verify-findings (G4 INSERT/UPDATE race, G1
> keyword FP-rate, COALESCE sticky eval_id) are tracked in the same
> post-session open-tasks section.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire CopilotKit hooks (provider-agnostic, no UI mounted) + A2UI v0.9 widget-rendering (chat-inline + standalone main-canvas) into `frontend_merger/`, with persistent surfaces, new TopBar buttons (Files + Memory), and a virtual `render_a2ui_surface` tool on the python-agent side (Ansatz Y-first).

**Architecture:** Hierarchical provider-tree: `<CopilotKit env-gated>` → `<A2UIProvider catalog={basicCatalog}>` → `<GlobalCopilotContext env-gated>` → children. Agent-brain stays in python-agent (LangGraph + LiteLLM), Next.js hosts BFF routes (`/api/copilotkit` runtime-endpoint, `/api/surfaces/[id]` persistence later phase). Existing AgentChatPanel (ai-sdk v6) stays as chat-UI; A2UI plugs in via `ToolOutputRenderer` extension (Ansatz Y: virtual tool-result) with validation layer.

**Tech Stack:** `@copilotkit/react-core` 1.56.2, `@copilotkit/react-ui` 1.56.2 (installed as alt), `@copilotkit/runtime` 1.56.2, `@copilotkit/a2ui-renderer` 1.56.2, `@a2ui/react` 0.9.1 (alt), `@a2ui/web_core` 0.9.2. Python: extends existing `TradingTool` base + `ToolRegistry`. Postgres-persistence deferred to phase-2 until go-appservice `/api/v1/surfaces/*` exists.

**Spec:** `docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md` (commits 593290a + 5446a38 + 7c68d29).

**v2 changes over v1:** Incorporates sota-contrarian pre-mortem findings:
- **BLOCK #1 fixed:** `RenderA2uiSurfaceTool.execute` matches `TradingTool` ABC signature `(tool_input, ctx)` — Task 6.
- **BLOCK #2 fixed:** `hasRichRenderer` + `TOOL_RENDERERS` both extended for `render_a2ui_surface` — Task 4.
- **MITIGATION #3:** Task 13 split — Phase-1 localStorage-only (Task 13a), Postgres-sync deferred to Phase-2 until go-appservice route exists.
- **MITIGATION #4:** `GlobalCopilotContext` env-guarded (same flag as `AgentProviders`) — Task 3.
- **MITIGATION #5:** A2UI-tree validation (Zod schema + type-whitelist) before dispatch to renderer — Task 4.
- **MINOR #6:** System-prompt A2UI-instructions conditional on keyword heuristic — Task 7.
- **New Task 0:** Pre-implementation LiteLLM tool-call smoke to validate OpenAIAdapter + LiteLLM + OpenRouter handshake before Task 12.

---

## File Structure

### New files to create

| Path | Responsibility |
|---|---|
| `frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx` | Env-gated: registers global actions + readables only when CopilotKit active |
| `frontend_merger/src/features/agent/hooks/useCurrentRoute.ts` | Pathname parsing `{pathname, segment, subtab}` |
| `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts` | Phase-1: localStorage only. Phase-2: + BFF sync |
| `frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx` | Plugs A2UI-renderer for `render_a2ui_surface` tool-results |
| `frontend_merger/src/features/agent/lib/a2uiTreeSchema.ts` | Zod schema + allowed component-type whitelist (validation) |
| `frontend_merger/src/app/api/copilotkit/route.ts` | CopilotKit runtime via OpenAIAdapter → LiteLLM |
| `python-backend/agent/tools/a2ui_surface.py` | `RenderA2uiSurfaceTool` (matches ABC signature) |
| `frontend_merger/tests/a2ui-integration.spec.ts` | Playwright E2E #9-#12 |
| `frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx` | Vitest unit |
| `frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts` | Vitest unit |
| `frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts` | Vitest unit (localStorage-only path) |
| `frontend_merger/src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts` | Validation tests (valid tree, wrong case, bad type, missing fields) |
| `python-backend/tests/agent/tools/test_a2ui_surface.py` | Pytest with mock `AgentExecutionContext` |

### Files to modify

| Path | Change |
|---|---|
| `frontend_merger/src/app/layout.tsx` | (no change — AgentProviders already wraps) |
| `frontend_merger/src/features/agent/providers/AgentProviders.tsx` | Nest GlobalCopilotContext inside (env-aware) |
| `frontend_merger/src/features/agent/components/AgentChatToolBlock.tsx` | `hasRichRenderer` extended |
| `frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx` | New `render_a2ui_surface` case + validation |
| `frontend_merger/src/components/GlobalTopBar.tsx` | Files + Memory in NAV_LINKS |
| `frontend_merger/src/features/files/components/FileCard.tsx` | "Add to Chat" context-menu |
| `frontend_merger/src/features/files/FilesPage.tsx` | `saveAttachmentToStorage` + `recentFiles` |
| `frontend_merger/src/features/control/ControlPage.tsx` | `openControlTab` + `activeControlTab` |
| `python-backend/agent/tools/registry.py` | Register `RenderA2uiSurfaceTool` |
| `python-backend/agent/app.py` | Conditional A2UI-instructions in `_build_system_prompt` |
| `frontend_merger/.env.example`, `.env.local` | CopilotKit runtime-URL + LiteLLM adapter flags |

---

## Task 0: LiteLLM + Tool-Call Handshake Smoke

Validate that the CopilotKit runtime → OpenAIAdapter → LiteLLM → OpenRouter chain correctly streams tool-calls. Blocking for Task 12.

**Files:** none (runbook only)

- [ ] **Step 1: Ensure LiteLLM running**

```bash
nc -z 127.0.0.1 4000 && echo "LiteLLM up" || echo "Start: ./scripts/dev-stack.sh --litellm"
```

- [ ] **Step 2: Curl-smoke with tool-call**

```bash
curl -sS -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-haiku-4-5",
    "messages": [{"role": "user", "content": "Call the test_tool function with name=foo"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "test_tool",
        "description": "A test tool",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
      }
    }],
    "stream": false
  }' | python3 -m json.tool
```

Expected: response contains `choices[0].message.tool_calls[0].function.arguments` as a JSON-string `"{\"name\":\"foo\"}"` (OpenAI standard). Note whether `arguments` is a string or an object.

- [ ] **Step 3: Document finding**

If `arguments` is a JSON-string: CopilotKit-runtime expects this — OK. If it's already-parsed object: check `@copilotkit/runtime` source for how it parses — may need wrapper adapter. Record in `docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md` §14 Risks as confirmed/refuted.

- [ ] **Step 4: Streaming smoke**

```bash
curl -sN -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-haiku-4-5",
    "messages": [{"role": "user", "content": "Call test_tool with name=bar"}],
    "tools": [...same as above...],
    "stream": true
  }' | head -20
```

Expected: SSE with `data:` lines; `delta.tool_calls` in at least one chunk.

- [ ] **Step 5: No commit — proceed to Task 1 only if streaming works**

If blocked: stop, surface the handshake problem, do NOT continue to Task 12. Tasks 1-11 and 13a-14 can still proceed (they don't depend on /api/copilotkit).

---

## Task 1: Env flags for CopilotKit runtime-gate

**Files:**
- Modify: `frontend_merger/.env.example`
- Modify: `frontend_merger/.env.local`

- [ ] **Step 1: Append flags to `.env.example`**

```bash
cat >> frontend_merger/.env.example <<'EOF'

# ─── CopilotKit runtime (default off — prevents 404 retries in dev)
NEXT_PUBLIC_COPILOTKIT_ENABLED=false
NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL=/api/copilotkit

# ─── /api/copilotkit → LiteLLM adapter
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=sk-not-used-with-litellm
COPILOTKIT_DEFAULT_MODEL=anthropic/claude-haiku-4-5
EOF
```

- [ ] **Step 2: Copy to `.env.local` (dev)**

```bash
cat >> frontend_merger/.env.local <<'EOF'
NEXT_PUBLIC_COPILOTKIT_ENABLED=false
NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL=/api/copilotkit
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=sk-not-used-with-litellm
COPILOTKIT_DEFAULT_MODEL=anthropic/claude-haiku-4-5
EOF
```

- [ ] **Step 3: Typecheck sanity**

```bash
cd frontend_merger && bunx tsc --noEmit
```
Expected: exit 0

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/.env.example frontend_merger/.env.local
git commit -m "feat(frontend_merger): env flags for CopilotKit runtime-gate + LiteLLM adapter"
```

---

## Task 2: `useCurrentRoute` hook + test

**Files:**
- Create: `frontend_merger/src/features/agent/hooks/useCurrentRoute.ts`
- Create: `frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts`

- [ ] **Step 1: Write failing test**

Create `frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts`:

```ts
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useCurrentRoute } from "../useCurrentRoute";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

describe("useCurrentRoute", () => {
  it("parses root", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/");
    expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
      pathname: "/", segment: "home", subtab: null,
    });
  });
  it("parses /control/agents", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/control/agents");
    expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
      pathname: "/control/agents", segment: "control", subtab: "agents",
    });
  });
  it("parses /memory/timeline", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/memory/timeline");
    expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
      pathname: "/memory/timeline", segment: "memory", subtab: "timeline",
    });
  });
  it("parses /files with no subtab", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/files");
    expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
      pathname: "/files", segment: "files", subtab: null,
    });
  });
});
```

- [ ] **Step 2: Run test → fail**

```bash
cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/useCurrentRoute.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement hook**

Create `frontend_merger/src/features/agent/hooks/useCurrentRoute.ts`:

```ts
"use client";

import { usePathname } from "next/navigation";
import { useMemo } from "react";

export interface CurrentRoute {
  pathname: string;
  segment: "home" | "matrix" | "files" | "memory" | "control" | "unknown";
  subtab: string | null;
}

const KNOWN_SEGMENTS = ["matrix", "files", "memory", "control"] as const;

export function useCurrentRoute(): CurrentRoute {
  const pathname = usePathname();
  return useMemo(() => {
    if (!pathname || pathname === "/") {
      return { pathname: pathname ?? "/", segment: "home", subtab: null };
    }
    const parts = pathname.split("/").filter(Boolean);
    const first = parts[0] ?? "";
    const segment = (KNOWN_SEGMENTS as readonly string[]).includes(first)
      ? (first as CurrentRoute["segment"])
      : "unknown";
    return { pathname, segment, subtab: parts[1] ?? null };
  }, [pathname]);
}
```

- [ ] **Step 4: Run test → pass**

```bash
cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/useCurrentRoute.test.ts
```
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/src/features/agent/hooks/useCurrentRoute.ts \
        frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts
git commit -m "feat(frontend_merger): useCurrentRoute hook"
```

---

## Task 3: `GlobalCopilotContext` (env-gated)

**Files:**
- Create: `frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx`
- Create: `frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx`
- Modify: `frontend_merger/src/features/agent/providers/AgentProviders.tsx`

- [ ] **Step 1: Write test covering env-gate**

Create `frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GlobalCopilotContext } from "../GlobalCopilotContext";

const useCopilotActionMock = vi.fn();
const useCopilotReadableMock = vi.fn();

vi.mock("@copilotkit/react-core", () => ({
  useCopilotAction: (...args: unknown[]) => useCopilotActionMock(...args),
  useCopilotReadable: (...args: unknown[]) => useCopilotReadableMock(...args),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@agent/stores/globalChatStore", () => ({
  useGlobalChat: () => ({ toggleChat: vi.fn() }),
}));

describe("GlobalCopilotContext", () => {
  beforeEach(() => {
    useCopilotActionMock.mockClear();
    useCopilotReadableMock.mockClear();
  });
  afterEach(() => {
    delete (process.env as Record<string, string | undefined>).NEXT_PUBLIC_COPILOTKIT_ENABLED;
  });

  it("does NOT register hooks when env disabled", () => {
    (process.env as Record<string, string>).NEXT_PUBLIC_COPILOTKIT_ENABLED = "false";
    render(<GlobalCopilotContext>child</GlobalCopilotContext>);
    expect(useCopilotActionMock).not.toHaveBeenCalled();
    expect(useCopilotReadableMock).not.toHaveBeenCalled();
  });

  it("registers navigateTo + toggleAgentSidebar + currentRoute when env enabled", () => {
    (process.env as Record<string, string>).NEXT_PUBLIC_COPILOTKIT_ENABLED = "true";
    render(<GlobalCopilotContext>child</GlobalCopilotContext>);
    expect(useCopilotActionMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: "navigateTo" }),
    );
    expect(useCopilotActionMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: "toggleAgentSidebar" }),
    );
    expect(useCopilotReadableMock).toHaveBeenCalledWith(
      expect.objectContaining({ description: expect.stringContaining("current route") }),
    );
  });
});
```

- [ ] **Step 2: Run test → fail**

```bash
cd frontend_merger && bunx vitest run src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement — split into inner + outer for env-gate**

Create `frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx`:

```tsx
"use client";

import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useGlobalChat } from "@agent/stores/globalChatStore";
import { useCurrentRoute } from "@agent/hooks/useCurrentRoute";

interface Props {
  children: ReactNode;
}

/**
 * Inner component: hooks fire here. Only mounted when CopilotKit provider active.
 */
function GlobalCopilotInner({ children }: Props) {
  const router = useRouter();
  const { toggleChat } = useGlobalChat();
  const route = useCurrentRoute();

  useCopilotAction({
    name: "navigateTo",
    description: "Navigate the user to a specific route in the app",
    parameters: [
      {
        name: "route",
        type: "string",
        description: "Target route (e.g. /control/agents, /files, /memory/kg)",
        required: true,
      },
    ],
    handler: async ({ route: target }: { route: string }) => {
      router.push(target);
      return { navigated: true, to: target };
    },
  });

  useCopilotAction({
    name: "toggleAgentSidebar",
    description: "Open or close the agent chat overlay",
    parameters: [],
    handler: async () => {
      toggleChat();
      return { toggled: true };
    },
  });

  useCopilotReadable({
    description: "The current route the user is viewing",
    value: route,
  });

  return <>{children}</>;
}

/**
 * Outer component: env-gate. When CopilotKit is disabled, renders children plain
 * (no hooks fire — avoids React-context errors without the CopilotKit provider).
 */
export function GlobalCopilotContext({ children }: Props) {
  const enabled = process.env.NEXT_PUBLIC_COPILOTKIT_ENABLED === "true";
  if (!enabled) return <>{children}</>;
  return <GlobalCopilotInner>{children}</GlobalCopilotInner>;
}
```

- [ ] **Step 4: Nest into `AgentProviders`**

Modify `frontend_merger/src/features/agent/providers/AgentProviders.tsx` — read current file, confirm it wraps `<CopilotKit>` → `<A2uiRootProvider>` → children. Insert `<GlobalCopilotContext>` as innermost wrapper inside `<A2uiRootProvider>`:

```tsx
import { GlobalCopilotContext } from "./GlobalCopilotContext";

// Replace the existing return-tree so it ends with:
<A2uiRootProvider>
  <GlobalCopilotContext>{children}</GlobalCopilotContext>
</A2uiRootProvider>
```

- [ ] **Step 5: Run tests + typecheck**

```bash
cd frontend_merger && bunx vitest run src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx && bunx tsc --noEmit
```
Expected: 2 tests PASS, tsc exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx \
        frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx \
        frontend_merger/src/features/agent/providers/AgentProviders.tsx
git commit -m "feat(frontend_merger): env-gated GlobalCopilotContext with navigateTo + toggleAgentSidebar"
```

---

## Task 4: A2UI tree validation + ToolOutputRenderer dispatch + hasRichRenderer

**Files:**
- Create: `frontend_merger/src/features/agent/lib/a2uiTreeSchema.ts`
- Create: `frontend_merger/src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts`
- Create: `frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx`
- Modify: `frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx`
- Modify: `frontend_merger/src/features/agent/components/AgentChatToolBlock.tsx`

- [ ] **Step 1: Write validation test**

Create `frontend_merger/src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseA2uiEnvelope } from "../a2uiTreeSchema";

describe("parseA2uiEnvelope", () => {
  it("accepts valid envelope with whitelisted root type", () => {
    const result = parseA2uiEnvelope({
      type: "a2ui",
      surface_id: "main",
      tree: { type: "Card", children: [{ type: "Text", text: "hello" }] },
    });
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.surfaceId).toBe("main");
  });

  it("rejects wrong type field (Ansatz Y marker missing)", () => {
    const result = parseA2uiEnvelope({
      type: "other",
      surface_id: "main",
      tree: { type: "Card" },
    });
    expect(result.ok).toBe(false);
  });

  it("rejects unknown root component type (not in whitelist)", () => {
    const result = parseA2uiEnvelope({
      type: "a2ui",
      surface_id: "main",
      tree: { type: "NotAComponent" },
    });
    expect(result.ok).toBe(false);
  });

  it("rejects empty tree", () => {
    const result = parseA2uiEnvelope({
      type: "a2ui",
      surface_id: "main",
      tree: {},
    });
    expect(result.ok).toBe(false);
  });

  it("rejects JSON-string-not-object tree", () => {
    const result = parseA2uiEnvelope({
      type: "a2ui",
      surface_id: "main",
      tree: '{"type":"Card"}' as unknown as Record<string, unknown>,
    });
    expect(result.ok).toBe(false);
  });

  it("accepts nested valid children", () => {
    const result = parseA2uiEnvelope({
      type: "a2ui",
      surface_id: "chat-1",
      tree: {
        type: "Column",
        children: [
          { type: "Card", children: [{ type: "Text", text: "NVDA" }] },
          { type: "Row", children: [{ type: "Button", label: "Buy" }] },
        ],
      },
    });
    expect(result.ok).toBe(true);
  });
});
```

- [ ] **Step 2: Run test → fail**

```bash
cd frontend_merger && bunx vitest run src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement schema + whitelist**

Create `frontend_merger/src/features/agent/lib/a2uiTreeSchema.ts`:

```ts
/**
 * A2UI tree envelope validation — guards against:
 *   - Malformed LLM output (wrong case, string-not-object, missing fields)
 *   - Unknown component types (prevents "Unknown widget" ambiguity)
 *   - Prompt-injection vectors via unsanitized component types
 *
 * Whitelist matches @copilotkit/a2ui-renderer basicCatalog (v0.9).
 */

import { z } from "zod";

const ALLOWED_TYPES = [
  "Card", "Column", "Row", "List", "Text", "Image", "Icon",
  "Video", "AudioPlayer", "Button", "TextField", "CheckBox",
  "ChoicePicker", "Slider", "DateTimeInput", "Divider", "Modal",
  "Tabs", "Chart", // Chart is not in basicCatalog but widely used in our registry
] as const;

const allowedTypesSet = new Set<string>(ALLOWED_TYPES);

const nodeSchema: z.ZodType<{ type: string; [key: string]: unknown }> = z.lazy(() =>
  z.object({ type: z.string() }).passthrough(),
);

const envelopeSchema = z.object({
  type: z.literal("a2ui"),
  surface_id: z.string().min(1),
  tree: nodeSchema,
});

export type A2uiEnvelope = z.infer<typeof envelopeSchema>;

type ParseResult =
  | { ok: true; surfaceId: string; tree: Record<string, unknown> }
  | { ok: false; error: string };

/**
 * Validate an A2UI envelope from a tool-result. Checks:
 *   - Shape (zod)
 *   - Tree root type is in the whitelist
 *   - Tree children recursively have whitelisted types (depth-first)
 *   - Tree is a non-empty object
 */
export function parseA2uiEnvelope(input: unknown): ParseResult {
  const parsed = envelopeSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, error: parsed.error.message };
  }
  const { surface_id, tree } = parsed.data;
  if (!tree || typeof tree !== "object" || Array.isArray(tree)) {
    return { ok: false, error: "tree must be a non-empty object" };
  }
  const treeObj = tree as Record<string, unknown>;
  if (Object.keys(treeObj).length === 0) {
    return { ok: false, error: "tree is empty" };
  }

  const checkNode = (node: unknown): string | null => {
    if (!node || typeof node !== "object" || Array.isArray(node)) {
      return "non-object node";
    }
    const obj = node as Record<string, unknown>;
    const t = obj.type;
    if (typeof t !== "string") return "node missing type string";
    if (!allowedTypesSet.has(t)) return `unknown component type: ${t}`;
    const children = obj.children;
    if (Array.isArray(children)) {
      for (const child of children) {
        const err = checkNode(child);
        if (err) return err;
      }
    }
    return null;
  };

  const err = checkNode(treeObj);
  if (err) return { ok: false, error: err };

  return { ok: true, surfaceId: surface_id, tree: treeObj };
}
```

- [ ] **Step 4: Run test → pass**

```bash
cd frontend_merger && bunx vitest run src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts
```
Expected: 6 PASS.

- [ ] **Step 5: Implement A2uiMessageRenderer**

Create `frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx`:

```tsx
"use client";

import { A2UIRenderer } from "@copilotkit/a2ui-renderer";
import { AlertTriangle } from "lucide-react";

interface Props {
  surfaceId: string;
  inlineTree?: Record<string, unknown>;
}

/**
 * Wrapper around A2UIRenderer with sensible fallback for chat-inline use.
 * `inlineTree` passed via initialTree prop when A2UIRenderer supports it
 * (v1.56.2 — check runtime support; falls back to surfaceId-only otherwise).
 */
export function A2uiMessageRenderer({ surfaceId, inlineTree }: Props) {
  return (
    <A2UIRenderer
      surfaceId={surfaceId}
      fallback={
        <div className="flex items-center gap-2 text-xs text-muted-foreground p-2">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Widget wird geladen…</span>
        </div>
      }
      {...(inlineTree ? { initialTree: inlineTree } : {})}
    />
  );
}
```

- [ ] **Step 6: Extend ToolOutputRenderer with validated A2UI dispatch**

Read `frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx`. Replace the `ToolOutputRenderer` function body with:

```tsx
import { parseA2uiEnvelope } from "@agent/lib/a2uiTreeSchema";
import { A2uiMessageRenderer } from "./A2uiMessageRenderer";
import { AlertTriangle } from "lucide-react";

// ... keep existing TOOL_RENDERERS + hasRichRenderer export (updated below)

export function ToolOutputRenderer({ toolName, output }: ToolOutputRendererProps) {
  if (
    typeof output === "object" &&
    output !== null &&
    (output as Record<string, unknown>).action === "browser_execute"
  ) {
    return (
      <div className="flex items-center gap-1.5 text-amber-400 text-[10px] mt-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Executing in browser via WebMCP...</span>
      </div>
    );
  }

  // Ansatz Y: A2UI widget tree via virtual tool-result
  if (toolName === "render_a2ui_surface") {
    const parsed = parseA2uiEnvelope(output);
    if (!parsed.ok) {
      return (
        <div className="flex items-center gap-1.5 text-red-400 text-[10px] mt-1 p-2 bg-red-500/5 border border-red-500/20 rounded">
          <AlertTriangle className="h-3 w-3" />
          <span>Invalid A2UI payload: {parsed.error}</span>
        </div>
      );
    }
    return <A2uiMessageRenderer surfaceId={parsed.surfaceId} inlineTree={parsed.tree} />;
  }

  const Component = TOOL_RENDERERS[toolName];
  if (!Component) return null;
  return <Component {...(output as Record<string, unknown>)} />;
}
```

- [ ] **Step 7: Extend `hasRichRenderer`**

In the same file, replace:

```ts
export function hasRichRenderer(toolName: string): boolean {
  return toolName in TOOL_RENDERERS;
}
```

with:

```ts
const RICH_RENDERER_NAMES = new Set<string>(["render_a2ui_surface"]);
export function hasRichRenderer(toolName: string): boolean {
  return toolName in TOOL_RENDERERS || RICH_RENDERER_NAMES.has(toolName);
}
```

- [ ] **Step 8: Verify `AgentChatToolBlock` consumes the updated `hasRichRenderer`**

```bash
grep -n "hasRichRenderer" frontend_merger/src/features/agent/components/AgentChatToolBlock.tsx
```

Expected: one import + one call-site. No change needed — just verify.

- [ ] **Step 9: Typecheck + biome + vitest**

```bash
cd frontend_merger && \
  bunx tsc --noEmit && \
  bunx biome check src/features/agent/lib src/features/agent/components/ToolOutputRenderer.tsx src/features/agent/components/A2uiMessageRenderer.tsx && \
  bunx vitest run src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts
```
Expected: all exit 0.

- [ ] **Step 10: Commit**

```bash
git add frontend_merger/src/features/agent/lib/a2uiTreeSchema.ts \
        frontend_merger/src/features/agent/lib/__tests__/a2uiTreeSchema.test.ts \
        frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx \
        frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx
git commit -m "feat(frontend_merger): A2UI tree validation + ToolOutputRenderer dispatch (Ansatz Y) + hasRichRenderer"
```

---

## Task 5: TopBar Files + Memory buttons

**Files:**
- Modify: `frontend_merger/src/components/GlobalTopBar.tsx`

- [ ] **Step 1: Extend NAV_LINKS**

Modify `frontend_merger/src/components/GlobalTopBar.tsx` — replace the import line and `NAV_LINKS`:

```tsx
import { Bot, Brain, Clock, Files, MessageSquare, SlidersHorizontal, Sparkles } from "lucide-react";

// Replace NAV_LINKS:
const NAV_LINKS: NavLink[] = [
  { href: "/matrix", label: "Matrix", icon: <MessageSquare className="h-3.5 w-3.5" />, match: (p) => p.startsWith("/matrix") },
  { href: "/files", label: "Files", icon: <Files className="h-3.5 w-3.5" />, match: (p) => p.startsWith("/files") },
  { href: "/memory", label: "Memory", icon: <Brain className="h-3.5 w-3.5" />, match: (p) => p.startsWith("/memory") },
  { href: "/control", label: "Control", icon: <SlidersHorizontal className="h-3.5 w-3.5" />, match: (p) => p.startsWith("/control") },
];
```

- [ ] **Step 2: Typecheck + biome**

```bash
cd frontend_merger && bunx tsc --noEmit && bunx biome check src/components/GlobalTopBar.tsx
```
Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add frontend_merger/src/components/GlobalTopBar.tsx
git commit -m "feat(frontend_merger): Files + Memory buttons in GlobalTopBar"
```

---

## Task 6: `RenderA2uiSurfaceTool` matching TradingTool ABC signature

**Files:**
- Create: `python-backend/agent/tools/a2ui_surface.py`
- Create: `python-backend/tests/agent/tools/test_a2ui_surface.py`
- Modify: `python-backend/agent/tools/registry.py`

- [ ] **Step 1: Read TradingTool ABC to confirm signature**

```bash
grep -nE "class TradingTool|def execute|AgentExecutionContext" python-backend/agent/tools/base.py | head
```

Note the exact signature: `async def execute(self, tool_input: dict[str, Any], ctx: AgentExecutionContext) -> dict[str, Any]` (or similar). Match this in the tool + test.

- [ ] **Step 2: Write failing test with mock AgentExecutionContext**

Create `python-backend/tests/agent/tools/test_a2ui_surface.py`:

```python
"""Tests for RenderA2uiSurfaceTool — matches TradingTool ABC signature."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.tools.a2ui_surface import RenderA2uiSurfaceTool


def _mock_ctx() -> MagicMock:
    # AgentExecutionContext has fields like user_id, session_id, role, tool_registry
    # We only need a stub — the tool should not dereference it.
    ctx = MagicMock()
    ctx.user_id = "test-user"
    ctx.session_id = "test-session"
    return ctx


@pytest.mark.asyncio
async def test_execute_returns_a2ui_envelope():
    tool = RenderA2uiSurfaceTool()
    tree = {"type": "Card", "children": [{"type": "Text", "text": "hello"}]}
    result = await tool.execute({"surface_id": "main", "tree": tree}, _mock_ctx())
    assert result == {"type": "a2ui", "surface_id": "main", "tree": tree}


@pytest.mark.asyncio
async def test_execute_rejects_missing_tree():
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="tree"):
        await tool.execute({"surface_id": "main", "tree": None}, _mock_ctx())


@pytest.mark.asyncio
async def test_execute_rejects_empty_tree():
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="tree"):
        await tool.execute({"surface_id": "main", "tree": {}}, _mock_ctx())


@pytest.mark.asyncio
async def test_execute_rejects_missing_surface_id():
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="surface_id"):
        await tool.execute({"tree": {"type": "Card"}}, _mock_ctx())


def test_tool_name():
    assert RenderA2uiSurfaceTool().name == "render_a2ui_surface"
```

Note: `.name` as property (not method) — check `TradingTool` base: if `name` is a `@property`, test uses `tool.name`. If it's a method, use `tool.name()`. Adjust test after reading base.py.

- [ ] **Step 3: Run test → fail**

```bash
cd python-backend && APP_ENV=development uv run pytest tests/agent/tools/test_a2ui_surface.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 4: Implement tool matching ABC**

Create `python-backend/agent/tools/a2ui_surface.py`:

```python
"""RenderA2uiSurfaceTool — virtual tool wrapping an A2UI widget-tree as tool-result.

Ansatz Y from the spec: reuses existing tool-result SSE streaming. Agent emits
this via a normal tool-call; the frontend `ToolOutputRenderer` recognizes the
`type="a2ui"` envelope and mounts an `<A2UIRenderer>` inline.

Signature matches TradingTool ABC exactly: `execute(tool_input, ctx)`.
"""

from __future__ import annotations

from typing import Any

from agent.tools.base import TradingTool


class RenderA2uiSurfaceTool(TradingTool):
    """Emit an A2UI widget-tree bound to a surface id."""

    @property
    def name(self) -> str:
        return "render_a2ui_surface"

    @property
    def description(self) -> str:
        return (
            "Render a rich UI widget tree on the frontend. "
            "Use surface_id 'main' for the standalone dashboard canvas on '/' "
            "or surface_id 'chat-<messageId>' for inline chat-message widgets. "
            "tree is an A2UI v0.9 component-tree JSON with allowed types: "
            "Card, Column, Row, List, Text, Image, Icon, Video, AudioPlayer, "
            "Button, TextField, CheckBox, ChoicePicker, Slider, DateTimeInput, "
            "Divider, Modal, Tabs, Chart."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "surface_id": {
                    "type": "string",
                    "description": "Surface identifier (e.g. 'main', 'chat-<id>')",
                },
                "tree": {
                    "type": "object",
                    "description": "A2UI v0.9 component-tree JSON",
                },
            },
            "required": ["surface_id", "tree"],
        }

    async def execute(
        self,
        tool_input: dict[str, Any],
        ctx: Any,  # AgentExecutionContext — imported lazily to avoid cycle
    ) -> dict[str, Any]:
        surface_id = tool_input.get("surface_id")
        tree = tool_input.get("tree")
        if not surface_id:
            raise ValueError("surface_id required")
        if not tree or not isinstance(tree, dict):
            raise ValueError("tree must be a non-empty dict")
        return {"type": "a2ui", "surface_id": surface_id, "tree": tree}
```

**Note:** Verify `name`, `description`, `parameters_schema` match the property/method style of `TradingTool` base after reading base.py in Step 1. Adjust accordingly.

- [ ] **Step 5: Register in ToolRegistry**

Read `python-backend/agent/tools/registry.py`. Identify where default tools are loaded. Add import + registration. Common pattern:

```python
from agent.tools.a2ui_surface import RenderA2uiSurfaceTool

# In the default-tools factory or __init__:
registry.register(RenderA2uiSurfaceTool())
```

If auto-discovery by module scan: verify that placing the file in `agent/tools/` is enough. Otherwise add explicit registration.

- [ ] **Step 6: Run tests → pass**

```bash
cd python-backend && APP_ENV=development uv run pytest tests/agent/tools/test_a2ui_surface.py -v
```
Expected: 5 PASS.

- [ ] **Step 7: Lint check**

```bash
cd python-backend && uv run ruff check agent/tools/a2ui_surface.py agent/tools/registry.py
```
Expected: exit 0.

- [ ] **Step 8: Commit**

```bash
git add python-backend/agent/tools/a2ui_surface.py \
        python-backend/agent/tools/registry.py \
        python-backend/tests/agent/tools/test_a2ui_surface.py
git commit -m "feat(python-backend): RenderA2uiSurfaceTool (matches TradingTool ABC signature)"
```

---

## Task 7: Conditional A2UI system-prompt injection

**Files:**
- Modify: `python-backend/agent/app.py` (in `_build_system_prompt`)

- [ ] **Step 1: Locate function**

```bash
grep -n "_build_system_prompt" python-backend/agent/app.py
```

- [ ] **Step 2: Extend with keyword-gated injection**

Inside the function, append after the existing system-prompt body, before `return`:

```python
# Ansatz Y: A2UI widget emission (conditional to save tokens for small models).
# Heuristic — only inject if the user message hints at visual output.
A2UI_KEYWORDS = ("chart", "card", "dashboard", "visual", "zeig", "show", "render", "graph", "widget")

def _wants_a2ui(user_context: str | None) -> bool:
    if not user_context:
        return False
    lower = user_context.lower()
    return any(kw in lower for kw in A2UI_KEYWORDS)

A2UI_INSTRUCTIONS = """

You can render rich UI widgets using the `render_a2ui_surface` tool. Use it when
the user asks for visual data (charts, portfolio cards, tables, forms, etc.).

Call signature:
  render_a2ui_surface(surface_id="main" | "chat-<id>", tree=<A2UI-JSON>)

Allowed root component types (A2UI v0.9 basicCatalog + Chart):
  Card, Column, Row, List, Text, Image, Icon, Video, AudioPlayer, Button,
  TextField, CheckBox, ChoicePicker, Slider, DateTimeInput, Divider, Modal,
  Tabs, Chart.

Example:
  render_a2ui_surface(
    surface_id="main",
    tree={
      "type": "Card",
      "children": [
        {"type": "Text", "text": "NVDA"},
        {"type": "Text", "text": "$142.50"}
      ]
    }
  )

Use exact type names (case-sensitive). Use "main" surface_id for the landing
page dashboard, or "chat-<uuid>" for inline chat widgets.
"""

# At the existing system-prompt return site:
if _wants_a2ui(req.context):
    prompt = prompt + A2UI_INSTRUCTIONS

return prompt
```

Adjust variable names (`prompt`, `req.context`, etc.) to match the actual function structure — read the function body before editing.

- [ ] **Step 3: Smoke-test no regression**

```bash
cd python-backend && APP_ENV=development uv run pytest tests/agent/ -x --timeout=30 -q
```
Expected: existing tests unaffected.

- [ ] **Step 4: Commit**

```bash
git add python-backend/agent/app.py
git commit -m "feat(python-backend): conditional A2UI instructions in system-prompt (keyword-gated)"
```

---

## Task 8: Files-page CopilotKit actions + readables

**Files:**
- Modify: `frontend_merger/src/features/files/FilesPage.tsx`

- [ ] **Step 1: Locate file-query hook**

```bash
grep -n "useQuery\|useFiles\|filesQuery" frontend_merger/src/features/files/FilesPage.tsx | head
```

Adapt the variable names below to what's actually in FilesPage.

- [ ] **Step 2: Add hooks**

Inside `FilesPage()` body (before return):

```tsx
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

// Inside FilesPage():
const filesQuery = useFiles(); // adjust to actual hook
const recentFiles = (filesQuery.data ?? []).slice(0, 10).map((f) => ({
  id: f.id,
  name: f.name,
  mime: f.mime ?? f.contentType ?? "unknown",
  size: f.size ?? 0,
}));

useCopilotReadable({
  description: "Up to 10 most recent files in the user's storage",
  value: recentFiles,
});

useCopilotAction({
  name: "saveAttachmentToStorage",
  description:
    "Persist a chat-attached file from chat-state to blob storage so it shows up in /files",
  parameters: [
    { name: "attachmentId", type: "string", description: "The attachment id from currentChatAttachments", required: true },
  ],
  handler: async ({ attachmentId }: { attachmentId: string }) => {
    const res = await fetch("/api/files/save-attachment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ attachmentId }),
    });
    if (!res.ok) {
      const text = await res.text();
      return { saved: false, error: text };
    }
    const file = (await res.json()) as { id: string; name: string };
    filesQuery.refetch?.();
    return { saved: true, fileId: file.id, name: file.name };
  },
});
```

**Safe when CopilotKit disabled:** `useCopilotAction`/`useCopilotReadable` from `@copilotkit/react-core` check internally for provider presence. If `NEXT_PUBLIC_COPILOTKIT_ENABLED=false`, `AgentProviders` does NOT mount `<CopilotKit>` — so these hooks must tolerate that. Test:

```bash
grep -n "useCopilotAction\|useCopilotReadable" frontend_merger/node_modules/@copilotkit/react-core/dist/*.d.ts | head -5
```

If the hooks error without a provider in the tree, wrap the whole block in a conditional matching the env-gate (same pattern as Task 3's `GlobalCopilotContext`).

- [ ] **Step 3: Ensure backend route `/api/files/save-attachment` exists or stub**

```bash
ls frontend_merger/src/app/api/files/
```

If `save-attachment/route.ts` doesn't exist, create a minimal stub that returns 501 so the action doesn't crash the UI:

```ts
// frontend_merger/src/app/api/files/save-attachment/route.ts
export async function POST() {
  return Response.json(
    { error: "save-attachment not yet implemented — go-appservice route pending" },
    { status: 501 },
  );
}
```

- [ ] **Step 4: Typecheck + biome**

```bash
cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/files/FilesPage.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/src/features/files/FilesPage.tsx \
        frontend_merger/src/app/api/files/save-attachment/route.ts
git commit -m "feat(frontend_merger): FilesPage — saveAttachmentToStorage action + recentFiles readable"
```

---

## Task 9: "Add to Chat" context-menu on FileCard

**Files:**
- Modify: `frontend_merger/src/features/files/components/FileCard.tsx` (or equivalent file-card component)
- Maybe-create: `frontend_merger/src/components/ui/context-menu.tsx` (shadcn add)

- [ ] **Step 1: Locate file-card component**

```bash
grep -rnlE "FileCard|FileRow|FileItem" frontend_merger/src/features/files/components/ | head
```

Adapt component path to what exists.

- [ ] **Step 2: Ensure context-menu UI primitive exists**

```bash
ls frontend_merger/src/components/ui/context-menu.tsx
```

If missing:

```bash
cd frontend_merger && bunx shadcn@latest add context-menu
```

- [ ] **Step 3: Wrap FileCard root in ContextMenu**

Edit the FileCard component. Add `data-testid="file-card"` (for Playwright #12), wrap existing JSX:

```tsx
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useGlobalChat } from "@agent/stores/globalChatStore";

// Inside the component:
const { openChat } = useGlobalChat();

return (
  <ContextMenu>
    <ContextMenuTrigger asChild>
      <div data-testid="file-card">
        {/* existing FileCard JSX */}
      </div>
    </ContextMenuTrigger>
    <ContextMenuContent>
      <ContextMenuItem
        onClick={() => openChat(`file-context:${file.id}:${file.name}`)}
      >
        Add to Chat
      </ContextMenuItem>
    </ContextMenuContent>
  </ContextMenu>
);
```

- [ ] **Step 4: Typecheck + biome**

```bash
cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/files/components/
```

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/src/features/files/components/ \
        frontend_merger/src/components/ui/context-menu.tsx
git commit -m "feat(frontend_merger): FileCard 'Add to Chat' context-menu"
```

---

## Task 10: Control-page CopilotKit action + readable

**Files:**
- Modify: `frontend_merger/src/features/control/ControlPage.tsx`

- [ ] **Step 1: Add hooks to ControlPage**

At the top of `ControlPage()` body (before renderSubtab or return):

```tsx
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { useRouter, usePathname } from "next/navigation";

// Inside ControlPage():
const router = useRouter();
const pathname = usePathname();
const activeControlTab = pathname.startsWith("/control/")
  ? (pathname.split("/")[2] ?? "overview")
  : "overview";

useCopilotReadable({
  description:
    "Currently active Control-UI tab (overview, agents, skills, sessions, tools, security, system, sandbox, audit, mcp, a2a, api)",
  value: { activeControlTab },
});

useCopilotAction({
  name: "openControlTab",
  description: "Switch to a specific tab inside the Control UI",
  parameters: [
    {
      name: "tab",
      type: "string",
      description:
        "One of: overview, agents, skills, sessions, tools, security, system, sandbox, audit, mcp, a2a, api",
      required: true,
    },
  ],
  handler: async ({ tab }: { tab: string }) => {
    router.push(`/control/${tab === "overview" ? "" : tab}`);
    return { switched: true, tab };
  },
});
```

- [ ] **Step 2: Typecheck + biome**

```bash
cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/control/ControlPage.tsx
```

- [ ] **Step 3: Commit**

```bash
git add frontend_merger/src/features/control/ControlPage.tsx
git commit -m "feat(frontend_merger): ControlPage — openControlTab action + activeControlTab readable"
```

---

## Task 11: Layout styles import (CopilotKit CSS)

**Files:**
- Modify: `frontend_merger/src/app/layout.tsx`

Minor but required: CopilotKit UI components use `@copilotkit/react-ui/styles.css`. Even though we don't mount `CopilotSidebar`/`CopilotPopup`, importing the CSS once is harmless and future-proofs later UI-component adoption.

- [ ] **Step 1: Verify import exists**

```bash
grep -n "copilotkit" frontend_merger/src/app/layout.tsx
```

If already present (from prior session): skip to Step 3.

- [ ] **Step 2: Add import**

In `frontend_merger/src/app/layout.tsx`, add before `./globals.css`:

```tsx
import "@copilotkit/react-ui/styles.css";
import "./globals.css";
```

- [ ] **Step 3: Verify build**

```bash
cd frontend_merger && bun run build 2>&1 | tail -20
```
Expected: exit 0 with successful build.

- [ ] **Step 4: Commit (skip if no change)**

```bash
git add frontend_merger/src/app/layout.tsx
git commit -m "chore(frontend_merger): import @copilotkit/react-ui/styles.css"
```

---

## Task 12: `/api/copilotkit` runtime endpoint

**Pre-condition:** Task 0 LiteLLM tool-call smoke PASSED.

**Files:**
- Create: `frontend_merger/src/app/api/copilotkit/route.ts`

- [ ] **Step 1: Create the route**

Create `frontend_merger/src/app/api/copilotkit/route.ts`:

```ts
/**
 * CopilotKit Runtime Endpoint.
 *
 * Thin BFF proxy: OpenAIAdapter with baseURL → LiteLLM → provider-agnostic.
 * All LLM calls go through localhost:4000 (LiteLLM gateway) which routes to
 * OpenRouter / Anthropic / OpenAI / Ollama per user config.
 *
 * Spec: docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md §17.1.10
 */

import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import OpenAI from "openai";
import type { NextRequest } from "next/server";

const LITELLM_BASE_URL =
  process.env.LITELLM_BASE_URL ??
  process.env.NEXT_PUBLIC_LITELLM_BASE_URL ??
  "http://localhost:4000";

const DEFAULT_MODEL =
  process.env.COPILOTKIT_DEFAULT_MODEL ?? "anthropic/claude-haiku-4-5";

const openai = new OpenAI({
  baseURL: LITELLM_BASE_URL,
  apiKey: process.env.LITELLM_API_KEY ?? "sk-not-used-with-litellm",
});

const serviceAdapter = new OpenAIAdapter({ openai, model: DEFAULT_MODEL });
const runtime = new CopilotRuntime();

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};

export const OPTIONS = async () =>
  new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "content-type, authorization",
    },
  });
```

- [ ] **Step 2: Typecheck**

```bash
cd frontend_merger && bunx tsc --noEmit
```

- [ ] **Step 3: Smoke-test route with LiteLLM up**

```bash
curl -sSf -X POST http://localhost:3003/api/copilotkit \
  -H "Content-Type: application/json" \
  -d '{"operationName":"generateCopilotResponse","variables":{}}' | head -c 500
```

Expected: a GraphQL error about missing variables (route exists + runtime responds) — NOT 404.

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/src/app/api/copilotkit/route.ts
git commit -m "feat(frontend_merger): /api/copilotkit runtime via OpenAIAdapter → LiteLLM"
```

---

## Task 13a: `usePersistentSurface` — localStorage only (Phase-1)

**Explicitly deferred:** Postgres-sync via BFF + Alembic migration + go-appservice `/api/v1/surfaces/*` route. Phase-2 task.

**Files:**
- Create: `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts`
- Create: `frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts`

- [ ] **Step 1: Write test (localStorage-only)**

Create `frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts`:

```ts
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePersistentSurface } from "../usePersistentSurface";

const SCHEMA_VERSION = 1;

beforeEach(() => {
  window.localStorage.clear();
});

describe("usePersistentSurface (localStorage-only)", () => {
  it("loads nothing on first mount when storage empty", () => {
    const { result } = renderHook(() => usePersistentSurface("main"));
    expect(result.current.surfaceJson).toBeNull();
  });

  it("persists save to localStorage with schema_version", () => {
    const { result } = renderHook(() => usePersistentSurface("main"));
    act(() => {
      result.current.save({ type: "Card", children: [] });
    });
    const stored = window.localStorage.getItem("a2ui.surface.main");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.schema_version).toBe(SCHEMA_VERSION);
    expect(parsed.surface_json).toEqual({ type: "Card", children: [] });
  });

  it("loads existing valid surface on mount", () => {
    window.localStorage.setItem(
      "a2ui.surface.main",
      JSON.stringify({
        schema_version: SCHEMA_VERSION,
        surface_json: { type: "Card" },
      }),
    );
    const { result } = renderHook(() => usePersistentSurface("main"));
    expect(result.current.surfaceJson).toEqual({ type: "Card" });
  });

  it("drops stale schema_version on mount", () => {
    window.localStorage.setItem(
      "a2ui.surface.main",
      JSON.stringify({
        schema_version: 99,
        surface_json: { type: "Card" },
      }),
    );
    const { result } = renderHook(() => usePersistentSurface("main"));
    expect(result.current.surfaceJson).toBeNull();
    // Stale entry should be removed:
    expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
  });

  it("clear() removes storage + state", () => {
    window.localStorage.setItem(
      "a2ui.surface.main",
      JSON.stringify({ schema_version: SCHEMA_VERSION, surface_json: { type: "Card" } }),
    );
    const { result } = renderHook(() => usePersistentSurface("main"));
    act(() => {
      result.current.clear();
    });
    expect(result.current.surfaceJson).toBeNull();
    expect(window.localStorage.getItem("a2ui.surface.main")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test → fail**

```bash
cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/usePersistentSurface.test.ts
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement hook (localStorage-only, Phase-1)**

Create `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts`:

```ts
"use client";

import { useCallback, useEffect, useState } from "react";

const SCHEMA_VERSION = 1;

interface StoredSurface {
  schema_version: number;
  surface_json: Record<string, unknown>;
  updated_at?: string;
}

export interface PersistentSurfaceApi {
  surfaceJson: Record<string, unknown> | null;
  save: (json: Record<string, unknown>) => void;
  clear: () => void;
}

function storageKey(surfaceId: string): string {
  return `a2ui.surface.${surfaceId}`;
}

/**
 * Phase-1: localStorage-only.
 *
 * Phase-2 will add BFF sync via /api/surfaces/[id] once go-appservice exposes
 * /api/v1/surfaces/*. Until then, surfaces are per-browser, per-origin — no
 * cross-device carry-over. Document this in the Control-UI when surfaces are
 * visible in user settings.
 */
export function usePersistentSurface(surfaceId: string): PersistentSurfaceApi {
  const [surfaceJson, setSurfaceJson] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(storageKey(surfaceId));
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as StoredSurface;
      if (parsed.schema_version === SCHEMA_VERSION) {
        setSurfaceJson(parsed.surface_json);
      } else {
        window.localStorage.removeItem(storageKey(surfaceId));
      }
    } catch {
      window.localStorage.removeItem(storageKey(surfaceId));
    }
  }, [surfaceId]);

  const save = useCallback(
    (json: Record<string, unknown>) => {
      const entry: StoredSurface = {
        schema_version: SCHEMA_VERSION,
        surface_json: json,
        updated_at: new Date().toISOString(),
      };
      window.localStorage.setItem(storageKey(surfaceId), JSON.stringify(entry));
      setSurfaceJson(json);
    },
    [surfaceId],
  );

  const clear = useCallback(() => {
    window.localStorage.removeItem(storageKey(surfaceId));
    setSurfaceJson(null);
  }, [surfaceId]);

  return { surfaceJson, save, clear };
}
```

- [ ] **Step 4: Run test → pass**

```bash
cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/usePersistentSurface.test.ts
```
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/src/features/agent/hooks/usePersistentSurface.ts \
        frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts
git commit -m "feat(frontend_merger): usePersistentSurface (localStorage-only, Phase-1)"
```

---

## Task 14: Playwright E2E tests #9-#12

**Files:**
- Create: `frontend_merger/tests/a2ui-integration.spec.ts`

- [ ] **Step 1: Check playwright config + existing test patterns**

```bash
cat frontend_merger/playwright.config.ts
ls frontend_merger/tests/
```

- [ ] **Step 2: Create test file**

Create `frontend_merger/tests/a2ui-integration.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test.describe("A2UI + CopilotKit integration (Ansatz Y)", () => {
  test("#9 Files and Memory buttons visible + navigate", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /files/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /memory/i })).toBeVisible();

    await page.getByRole("link", { name: /files/i }).click();
    await expect(page).toHaveURL(/\/files/);

    await page.getByRole("link", { name: /memory/i }).click();
    await expect(page).toHaveURL(/\/memory/);
  });

  test("#10 Landing A2UI canvas renders idle placeholder", async ({ page }) => {
    await page.goto("/");
    const canvas = page.locator('[aria-label="A2UI surface main"]');
    await expect(canvas).toBeVisible();
    await expect(canvas).toContainText(/canvas bereit|widget wird geladen/i);
  });

  test("#11 Chat message with A2UI tool-result renders inline widget", async ({ page }) => {
    // Mock /api/agent/chat SSE to emit render_a2ui_surface tool-result
    await page.route("**/api/agent/chat", async (route) => {
      const chunks = [
        `data: ${JSON.stringify({ type: "thread-id", thread_id: "t1" })}\n\n`,
        `data: ${JSON.stringify({ type: "text-start", id: "t1" })}\n\n`,
        `data: ${JSON.stringify({ type: "text-end", id: "t1" })}\n\n`,
        `data: ${JSON.stringify({
          type: "tool-result",
          tool_call_id: "tc1",
          tool_name: "render_a2ui_surface",
          result: {
            type: "a2ui",
            surface_id: "chat-inline-1",
            tree: { type: "Card", children: [{ type: "Text", text: "hello-widget" }] },
          },
        })}\n\n`,
        `data: ${JSON.stringify({ type: "finish" })}\n\n`,
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "x-vercel-ai-ui-message-stream": "v1" },
        body: chunks,
      });
    });

    await page.goto("/");
    await page.getByRole("button", { name: /agent/i }).click();
    const composer = page.getByRole("textbox").first();
    await composer.fill("show test widget");
    await composer.press("Enter");
    await expect(page.getByText("hello-widget")).toBeVisible({ timeout: 10_000 });
  });

  test("#12 FileCard 'Add to Chat' opens chat with context", async ({ page }) => {
    await page.goto("/files");
    const card = page.locator('[data-testid="file-card"]').first();
    const cardVisible = await card.isVisible().catch(() => false);
    test.skip(!cardVisible, "No files in storage — seed fixture not set up");
    await card.click({ button: "right" });
    await page.getByRole("menuitem", { name: /add to chat/i }).click();
    const sheet = page.locator('[role="dialog"]').first();
    await expect(sheet).toBeVisible();
  });
});
```

- [ ] **Step 3: Run (dev server up)**

```bash
cd frontend_merger && bunx playwright test a2ui-integration.spec.ts --reporter=list
```
Expected: #9 + #10 PASS; #11 may fail if SSE-mock format doesn't match what `useChatSession` parses — adjust chunks accordingly; #12 SKIP if no files seeded.

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/tests/a2ui-integration.spec.ts
git commit -m "test(frontend_merger): A2UI + CopilotKit integration Playwright #9-#12"
```

---

## Task 15: Full-stack smoke (verification runbook)

**Files:** none (runbook)

- [ ] **Step 1: Start stack**

```bash
./scripts/setup-garage.sh
./scripts/dev-stack.sh --matrix-chat --litellm
```

Wait for all services to report `✓`.

- [ ] **Step 2: Browser smoke**

Open `http://localhost:3003` in Chrome:
- TopBar shows: Matrix · Files · Memory · Control (+ Agent toggle)
- Landing A2UI canvas visible with idle placeholder
- Console: 0 errors (a few warnings OK)

- [ ] **Step 3: Route navigation**

Click each TopBar button → page loads within 3s, no console errors.

- [ ] **Step 4: Agent prompt → widget**

Enable CopilotKit in `.env.local`: `NEXT_PUBLIC_COPILOTKIT_ENABLED=true`. Restart frontend. Open agent sidebar. Prompt: `"Zeig mir eine Card mit NVDA und Preis $142"`. Expected: LLM calls `render_a2ui_surface` with a Card tree → inline widget renders in chat.

If LLM refuses to call the tool, inspect DevConsole + python-agent logs (`logs/devstack/python-agent.log`). Adjust `A2UI_INSTRUCTIONS` wording.

- [ ] **Step 5: Navigate action via agent**

Prompt: `"Open the agents tab in control"`. Expected: URL changes to `/control/agents`.

If no-op: verify CopilotKit is active (DevConsole visible in corner). Verify LiteLLM is streaming tool_calls correctly.

- [ ] **Step 6: Persistence**

Prompt: `"Render on the main surface a Card saying 'Hello Dashboard'"`. Expected: widget appears on `/` landing. Reload page → widget still there.

- [ ] **Step 7: Run full test suite**

```bash
cd frontend_merger && bunx vitest run && bunx playwright test
cd python-backend && APP_ENV=development uv run pytest tests/agent/tools/ -v
```
Expected: all green.

- [ ] **Step 8: No commit — verification only**

---

## Deferred / Phase-2 (NOT in this plan)

Per spec §13 + §17.1.14 + contrarian MITIGATION #3:

- Postgres persistence for surfaces (`usePersistentSurface` BFF-sync + `/api/surfaces/[surfaceId]` route + Alembic migration 027) — **blocked on go-appservice adding `/api/v1/surfaces/*`**
- Native A2UI SSE packet-types (`a2ui-surface-start` etc.) — Ansatz X migration
- Live-data binding patterns (agent `updateDataModel` stream / client `useQuery` data-sources)
- `a2ui-agent-sdk` Python install + integration
- Custom A2UI widget-catalog beyond `basicCatalog` (wrap ChartWidget/PortfolioCard as A2UI catalog entries via `createReactComponent`)
- Matrix-chat CopilotKit integration (exec-10 territory)
- Route consolidation into `/control/*`

---

## Rollback Strategy

Per-task rollback (each task commits independently):

```bash
git reset --hard HEAD~1        # drop last commit + working tree
git revert <commit-sha>        # preserve history
```

Full-feature rollback:

```bash
# Find the commit BEFORE Task 1 of this plan:
git log --oneline --grep="env flags for CopilotKit runtime-gate" | head -1
# Then:
git reset --hard <that-sha>^
```

Since Task 13a is localStorage-only, no migration to revert.

---

## Self-Review

**1. Spec coverage.**
- §19 step 1 (provider hierarchy) → Task 1, 3, 11
- §19 step 2 (GlobalCopilotContext) → Task 3
- §19 step 3 (A2uiMessageRenderer integration) → Task 4
- §19 step 4 (ToolOutputRenderer extension) → Task 4
- §19 step 5 (TopBar buttons) → Task 5
- §19 step 6 (Python tool registration) → Task 6, 7
- §19 step 7 (FileCard Add-to-Chat) → Task 9
- §19 step 8 (Files-page actions + readables) → Task 8
- §19 step 9 (Control-page actions + readables) → Task 10
- §19 step 10 (/api/copilotkit) → Task 12 (prereq Task 0)
- §19 step 11 (persistent surface) → Task 13a (Phase-1: localStorage only)
- §19 step 12 (main-canvas) → already done pre-plan; integrates with Task 13a
- §19 step 13 (tests) → Task 14
- §19 step 14 (deferred phase-2) → Deferred section
- Contrarian fixes → Task 0 + Task 3 env-gate + Task 4 validation + Task 6 ABC-signature + Task 13a scope-reduction + Task 7 keyword-gated prompt

**2. Placeholder scan.** No TBD, TODO, "similar to Task N" shorthand. Every step has real code or a concrete runbook action.

**3. Type consistency.**
- `render_a2ui_surface` (snake_case) consistent everywhere (Task 4 dispatch, Task 6 tool-name, Task 7 prompt, Task 14 test).
- Envelope shape `{type: "a2ui", surface_id, tree}` — Task 4 validates, Task 6 emits, Task 14 mocks. All match.
- `schema_version = 1` in usePersistentSurface (Task 13a).
- CopilotKit env-flag `NEXT_PUBLIC_COPILOTKIT_ENABLED` — same name in Task 1 (define), Task 3 (read), Task 15 (runbook toggle).
