# Agentic-Stack Frontend Merger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire CopilotKit hooks (provider-agnostic, no UI mounted) + A2UI v0.9 widget-rendering (chat-inline + standalone main-canvas) into `frontend_merger/`, with persistent surfaces, new TopBar buttons (Files + Memory), and a virtual `render_a2ui_surface` tool on the python-agent side (Ansatz Y-first).

**Architecture:** Hierarchical provider-tree: `<CopilotKit>` → `<A2UIProvider catalog={basicCatalog}>` → `<GlobalCopilotContext>` → children. Agent-brain stays in python-agent (LangGraph + LiteLLM), Next.js hosts BFF routes (`/api/copilotkit` runtime-endpoint, `/api/surfaces/[id]` persistence). Existing AgentChatPanel (ai-sdk v6) stays as chat-UI; A2UI plugs in via `ToolOutputRenderer` extension (Ansatz Y: virtual tool-result).

**Tech Stack:** `@copilotkit/react-core` 1.56.2, `@copilotkit/react-ui` 1.56.2 (installed as alt), `@copilotkit/runtime` 1.56.2, `@copilotkit/a2ui-renderer` 1.56.2, `@a2ui/react` 0.9.1 (alt), `@a2ui/web_core` 0.9.2. Python: extends existing `TradingTool` base + `ToolRegistry`. Alembic migration 027 for surface-persistence.

**Spec:** `docs/superpowers/specs/2026-04-21-ag-stack-mapping-design.md` (commits 593290a + 5446a38 + 7c68d29). §19 has the 14-step sequence this plan expands.

---

## File Structure

### New files to create

| Path | Responsibility |
|---|---|
| `frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx` | Registers global `useCopilotAction`/`useCopilotReadable` (navigateTo, toggleAgentSidebar, currentRoute, currentChatAttachments) |
| `frontend_merger/src/features/agent/hooks/useCurrentRoute.ts` | Pathname parsing `{pathname, segment, subtab}` |
| `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts` | A2UI surface persistence (localStorage sync + Postgres async) |
| `frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx` | Plugs A2UI-renderer into AgentChatPanel as a per-message renderer for `render_a2ui_surface` tool-results |
| `frontend_merger/src/app/api/copilotkit/route.ts` | CopilotKit runtime-endpoint via OpenAIAdapter → LiteLLM (`http://localhost:4000`) |
| `frontend_merger/src/app/api/surfaces/[surfaceId]/route.ts` | Surface persistence GET/PUT |
| `python-backend/agent/tools/a2ui_surface.py` | `RenderA2uiSurfaceTool(TradingTool)` — virtual tool emitting A2UI-tree in `output.type="a2ui"` |
| `python-backend/alembic/versions/027_user_surfaces.py` | `agent.user_surfaces` table migration |
| `frontend_merger/tests/a2ui-integration.spec.ts` | Playwright E2E tests #9-#12 |
| `frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx` | Vitest unit |
| `frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts` | Vitest unit |
| `frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts` | Vitest unit |
| `python-backend/tests/agent/tools/test_a2ui_surface.py` | Pytest for tool |

### Files to modify

| Path | Change |
|---|---|
| `frontend_merger/src/app/layout.tsx` | Wrap children with `<CopilotKit>` env-gated |
| `frontend_merger/src/features/agent/providers/AgentProviders.tsx` | Already wraps A2UIProvider (keep); nested correctly under CopilotKit |
| `frontend_merger/src/features/agent/AgentChatPanel.tsx` | Mount A2uiMessageRenderer in message-render-path |
| `frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx` | New case for `tool_name === "render_a2ui_surface"` |
| `frontend_merger/src/components/GlobalTopBar.tsx` | Add Files + Memory to NAV_LINKS |
| `frontend_merger/src/features/files/components/FileCard.tsx` | Add "Add to Chat" context-menu entry |
| `frontend_merger/src/features/files/FilesPage.tsx` | `useCopilotAction(saveAttachmentToStorage)` + `useCopilotReadable(recentFiles)` |
| `frontend_merger/src/features/control/ControlPage.tsx` | `useCopilotAction(openControlTab)` + `useCopilotReadable(activeControlTab)` |
| `frontend_merger/src/app/page.tsx` | Uses A2uiCanvas (already done — verify surface-id "main") |
| `python-backend/agent/tools/registry.py` | Register `RenderA2uiSurfaceTool` |
| `python-backend/agent/app.py` | Extend system-prompt with A2UI-catalog awareness |

---

## Task 1: Wrap layout with CopilotKit (env-gated)

**Files:**
- Modify: `frontend_merger/src/app/layout.tsx`
- Modify: `frontend_merger/.env.example`
- Modify: `frontend_merger/.env.local`

- [ ] **Step 1: Extend .env.example with CopilotKit flags**

Append to `frontend_merger/.env.example`:

```bash
# CopilotKit runtime-endpoint gate (default off → no 404 retries in dev)
NEXT_PUBLIC_COPILOTKIT_ENABLED=false
NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL=/api/copilotkit
```

- [ ] **Step 2: Copy flags into .env.local**

```bash
cat >> frontend_merger/.env.local <<'EOF'
NEXT_PUBLIC_COPILOTKIT_ENABLED=false
NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL=/api/copilotkit
EOF
```

- [ ] **Step 3: Verify AgentProviders nests correctly**

Read `frontend_merger/src/features/agent/providers/AgentProviders.tsx` — confirm it already:
1. Wraps children in `<A2UIProvider>` from `@copilotkit/a2ui-renderer`
2. Env-gates `<CopilotKit runtimeUrl>` via `NEXT_PUBLIC_COPILOTKIT_ENABLED` + `_RUNTIME_URL`
3. Renders children plain if flag off

No change needed if already in place from prior session — this step only verifies.

- [ ] **Step 4: Run typecheck**

Run: `cd frontend_merger && bunx tsc --noEmit`
Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/.env.example frontend_merger/.env.local
git commit -m "feat(frontend_merger): env flags for CopilotKit runtime-gate (default off)"
```

---

## Task 2: `useCurrentRoute` hook + unit test

**Files:**
- Create: `frontend_merger/src/features/agent/hooks/useCurrentRoute.ts`
- Create: `frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts`

- [ ] **Step 1: Write the failing test**

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
  it("parses root pathname", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/");
    const { result } = renderHook(() => useCurrentRoute());
    expect(result.current).toEqual({ pathname: "/", segment: "home", subtab: null });
  });

  it("parses /control/agents", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/control/agents");
    const { result } = renderHook(() => useCurrentRoute());
    expect(result.current).toEqual({
      pathname: "/control/agents",
      segment: "control",
      subtab: "agents",
    });
  });

  it("parses /memory/timeline", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/memory/timeline");
    const { result } = renderHook(() => useCurrentRoute());
    expect(result.current).toEqual({
      pathname: "/memory/timeline",
      segment: "memory",
      subtab: "timeline",
    });
  });

  it("parses /files with no subtab", () => {
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/files");
    const { result } = renderHook(() => useCurrentRoute());
    expect(result.current).toEqual({
      pathname: "/files",
      segment: "files",
      subtab: null,
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/useCurrentRoute.test.ts`
Expected: FAIL with "useCurrentRoute is not a function" or similar module-not-found.

- [ ] **Step 3: Implement the hook**

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
    const subtab = parts[1] ?? null;
    return { pathname, segment, subtab };
  }, [pathname]);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/useCurrentRoute.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/src/features/agent/hooks/useCurrentRoute.ts frontend_merger/src/features/agent/hooks/__tests__/useCurrentRoute.test.ts
git commit -m "feat(frontend_merger): useCurrentRoute hook for pathname parsing"
```

---

## Task 3: `GlobalCopilotContext` — global actions + readables

**Files:**
- Create: `frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx`
- Create: `frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx`
- Modify: `frontend_merger/src/features/agent/providers/AgentProviders.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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
  it("registers navigateTo action", () => {
    render(<GlobalCopilotContext>child</GlobalCopilotContext>);
    expect(useCopilotActionMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: "navigateTo" }),
    );
  });

  it("registers toggleAgentSidebar action", () => {
    render(<GlobalCopilotContext>child</GlobalCopilotContext>);
    expect(useCopilotActionMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: "toggleAgentSidebar" }),
    );
  });

  it("registers currentRoute readable", () => {
    render(<GlobalCopilotContext>child</GlobalCopilotContext>);
    expect(useCopilotReadableMock).toHaveBeenCalledWith(
      expect.objectContaining({ description: expect.stringContaining("current route") }),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend_merger && bunx vitest run src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement GlobalCopilotContext**

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
 * Global actions + readables available on every route.
 * Route-level contexts add their own via hooks in the route component.
 */
export function GlobalCopilotContext({ children }: Props) {
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
        description:
          "Target route, e.g. /control/agents, /files, /memory/kg, /matrix, /",
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
```

- [ ] **Step 4: Nest GlobalCopilotContext inside AgentProviders**

Modify `frontend_merger/src/features/agent/providers/AgentProviders.tsx` — wrap existing children with `<GlobalCopilotContext>` inside the innermost provider (after A2UIProvider, before children).

Exact change: inside the `AgentProviders` component body, wherever `return (...children wrappers...)` nests them, add `<GlobalCopilotContext>{children}</GlobalCopilotContext>` as the innermost wrapper. If AgentProviders already returns `<A2UIProvider>{children}</A2UIProvider>`, change to:

```tsx
import { GlobalCopilotContext } from "./GlobalCopilotContext";

// ...inside return:
<A2UIProvider catalog={basicCatalog}>
  <GlobalCopilotContext>{children}</GlobalCopilotContext>
</A2UIProvider>
```

- [ ] **Step 5: Run tests**

Run: `cd frontend_merger && bunx vitest run src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx && bunx tsc --noEmit`
Expected: 3 tests PASS, typecheck exit 0

- [ ] **Step 6: Commit**

```bash
git add frontend_merger/src/features/agent/providers/GlobalCopilotContext.tsx \
        frontend_merger/src/features/agent/providers/__tests__/GlobalCopilotContext.test.tsx \
        frontend_merger/src/features/agent/providers/AgentProviders.tsx
git commit -m "feat(frontend_merger): GlobalCopilotContext with navigateTo + toggleAgentSidebar + currentRoute"
```

---

## Task 4: Extend ToolOutputRenderer for `render_a2ui_surface`

**Files:**
- Modify: `frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx`
- Create: `frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx`

- [ ] **Step 1: Create A2uiMessageRenderer**

Create `frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx`:

```tsx
"use client";

import { A2UIRenderer } from "@copilotkit/a2ui-renderer";
import { AlertTriangle } from "lucide-react";

interface Props {
  surfaceId: string;
  /** If provided, renderer will dispatch this tree to the surface on mount. */
  inlineTree?: Record<string, unknown>;
}

/**
 * Wrapper around A2UIRenderer with a sensible fallback for chat-inline use.
 * When the backend emits `render_a2ui_surface` tool-result with an A2UI tree,
 * ToolOutputRenderer mounts this component with surfaceId + inlineTree.
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

- [ ] **Step 2: Extend ToolOutputRenderer**

Modify `frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx` — add branch handling the A2UI tool-name. Full replacement of `ToolOutputRenderer` function body:

```tsx
export function ToolOutputRenderer({ toolName, output }: ToolOutputRendererProps) {
  // exec-09: Browser-Tool Marker erkennen
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

  // A2UI virtual tool (Ansatz Y): agent emits widget-tree via tool-result
  if (
    toolName === "render_a2ui_surface" &&
    typeof output === "object" &&
    output !== null &&
    (output as Record<string, unknown>).type === "a2ui"
  ) {
    const payload = output as { type: "a2ui"; surface_id: string; tree: Record<string, unknown> };
    return <A2uiMessageRenderer surfaceId={payload.surface_id} inlineTree={payload.tree} />;
  }

  const Component = TOOL_RENDERERS[toolName];
  if (!Component) return null;
  return <Component {...(output as Record<string, unknown>)} />;
}
```

Add import at top: `import { A2uiMessageRenderer } from "./A2uiMessageRenderer";`

- [ ] **Step 3: Typecheck + biome**

Run: `cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/agent/components/ToolOutputRenderer.tsx src/features/agent/components/A2uiMessageRenderer.tsx`
Expected: both exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/src/features/agent/components/A2uiMessageRenderer.tsx \
        frontend_merger/src/features/agent/components/ToolOutputRenderer.tsx
git commit -m "feat(frontend_merger): ToolOutputRenderer handles render_a2ui_surface (Ansatz Y)"
```

---

## Task 5: Add Files + Memory buttons to GlobalTopBar

**Files:**
- Modify: `frontend_merger/src/components/GlobalTopBar.tsx`

- [ ] **Step 1: Extend NAV_LINKS**

Modify `frontend_merger/src/components/GlobalTopBar.tsx` — replace the `NAV_LINKS` array:

```tsx
import { Bot, Brain, Clock, Files, MessageSquare, SlidersHorizontal, Sparkles } from "lucide-react";

const NAV_LINKS: NavLink[] = [
  {
    href: "/matrix",
    label: "Matrix",
    icon: <MessageSquare className="h-3.5 w-3.5" />,
    match: (p) => p.startsWith("/matrix"),
  },
  {
    href: "/files",
    label: "Files",
    icon: <Files className="h-3.5 w-3.5" />,
    match: (p) => p.startsWith("/files"),
  },
  {
    href: "/memory",
    label: "Memory",
    icon: <Brain className="h-3.5 w-3.5" />,
    match: (p) => p.startsWith("/memory"),
  },
  {
    href: "/control",
    label: "Control",
    icon: <SlidersHorizontal className="h-3.5 w-3.5" />,
    match: (p) => p.startsWith("/control"),
  },
];
```

- [ ] **Step 2: Typecheck + biome**

Run: `cd frontend_merger && bunx tsc --noEmit && bunx biome check src/components/GlobalTopBar.tsx`
Expected: exit 0

- [ ] **Step 3: Commit**

```bash
git add frontend_merger/src/components/GlobalTopBar.tsx
git commit -m "feat(frontend_merger): Files + Memory buttons in GlobalTopBar"
```

---

## Task 6: Python — `RenderA2uiSurfaceTool` + registration

**Files:**
- Create: `python-backend/agent/tools/a2ui_surface.py`
- Create: `python-backend/tests/agent/tools/test_a2ui_surface.py`
- Modify: `python-backend/agent/tools/registry.py`

- [ ] **Step 1: Write the failing test**

Create `python-backend/tests/agent/tools/test_a2ui_surface.py`:

```python
import pytest
from agent.tools.a2ui_surface import RenderA2uiSurfaceTool


@pytest.mark.asyncio
async def test_render_a2ui_surface_returns_a2ui_envelope():
    tool = RenderA2uiSurfaceTool()
    tree = {"type": "Card", "children": [{"type": "Text", "text": "hello"}]}
    result = await tool.execute(surface_id="main", tree=tree)
    assert result == {"type": "a2ui", "surface_id": "main", "tree": tree}


@pytest.mark.asyncio
async def test_render_a2ui_surface_validates_tree_required():
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="tree"):
        await tool.execute(surface_id="main", tree=None)  # type: ignore[arg-type]


def test_render_a2ui_surface_name():
    assert RenderA2uiSurfaceTool().name() == "render_a2ui_surface"
```

- [ ] **Step 2: Run test to verify fails**

Run: `cd python-backend && APP_ENV=development uv run pytest tests/agent/tools/test_a2ui_surface.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the tool**

Create `python-backend/agent/tools/a2ui_surface.py`:

```python
"""RenderA2uiSurfaceTool — virtual tool that wraps an A2UI widget-tree as tool-result.

Agent emits this as a normal tool-call; the output payload carries an envelope the
frontend's ToolOutputRenderer recognizes (type="a2ui") and mounts into an
A2UIRenderer surface. Ansatz Y from the spec — reuses the existing tool-result
streaming channel, no new SSE packet-types needed for MVP.
"""

from __future__ import annotations

from typing import Any

from agent.tools.base import TradingTool


class RenderA2uiSurfaceTool(TradingTool):
    """Emit an A2UI widget-tree bound to a surface id."""

    def name(self) -> str:
        return "render_a2ui_surface"

    def description(self) -> str:
        return (
            "Render a rich UI widget tree on the frontend. "
            "Use surface_id 'main' for the standalone dashboard canvas on '/' "
            "or surface_id 'chat-<messageId>' for inline chat-message widgets. "
            "The tree parameter is an A2UI v0.9 component-tree JSON."
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "surface_id": {
                    "type": "string",
                    "description": "Surface identifier (e.g. 'main', 'chat-<id>')",
                },
                "tree": {
                    "type": "object",
                    "description": "A2UI v0.9 component-tree (Card, Column, Text, Chart, …)",
                },
            },
            "required": ["surface_id", "tree"],
        }

    async def execute(self, *, surface_id: str, tree: dict[str, Any]) -> dict[str, Any]:
        if not tree:
            raise ValueError("tree must be a non-empty A2UI component-tree")
        return {"type": "a2ui", "surface_id": surface_id, "tree": tree}
```

- [ ] **Step 4: Register in ToolRegistry**

Read `python-backend/agent/tools/registry.py`. Find the default-tools list/factory. Add `RenderA2uiSurfaceTool()` to it:

```python
# In registry.py — wherever the default ToolRegistry is built, e.g. a register_default_tools()
# or the __init__ that gathers tools. Add import + register call.

from agent.tools.a2ui_surface import RenderA2uiSurfaceTool

# ...inside the registry-build function, after existing registrations:
registry.register(RenderA2uiSurfaceTool())
```

If `registry.py` uses an auto-discovery pattern (scan module), this step may be a no-op — verify that the new tool is loaded by the registry on import.

- [ ] **Step 5: Run tests to verify pass**

Run: `cd python-backend && APP_ENV=development uv run pytest tests/agent/tools/test_a2ui_surface.py -v`
Expected: 3 tests PASS

- [ ] **Step 6: Verify lint + type**

Run: `cd python-backend && uv run ruff check agent/tools/a2ui_surface.py`
Expected: exit 0

- [ ] **Step 7: Commit**

```bash
git add python-backend/agent/tools/a2ui_surface.py \
        python-backend/agent/tools/registry.py \
        python-backend/tests/agent/tools/test_a2ui_surface.py
git commit -m "feat(python-backend): RenderA2uiSurfaceTool for A2UI widget emission (Ansatz Y)"
```

---

## Task 7: System-prompt A2UI awareness

**Files:**
- Modify: `python-backend/agent/app.py` (in `_build_system_prompt`)

- [ ] **Step 1: Locate `_build_system_prompt`**

Grep for it:
```bash
grep -n "_build_system_prompt" python-backend/agent/app.py
```

- [ ] **Step 2: Extend the prompt**

Find the function body. Append the following paragraph inside the system-prompt string (before any final `return`):

```python
A2UI_INSTRUCTIONS = """
You can render rich UI widgets using the `render_a2ui_surface` tool. Use it when
the user asks to see data visually (charts, portfolio cards, tables, forms, etc.).

Arguments:
- surface_id: "main" for the dashboard canvas on the landing page,
  or "chat-<random>" for an inline widget in the current chat message.
- tree: A2UI v0.9 JSON component-tree. Available components in the basicCatalog:
  Card, Column, Row, List, Text, Image, Icon, Video, AudioPlayer, Button,
  TextField, CheckBox, ChoicePicker, Slider, DateTimeInput, Divider, Modal, Tabs.

Example call:
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

Prefer render_a2ui_surface over plain text when the user asks for visual
information (charts, tables, comparisons).
"""
```

Concatenate into the system-prompt return value (append after existing prompt body).

- [ ] **Step 3: Verify no regression**

Run: `cd python-backend && APP_ENV=development uv run pytest tests/agent/ -x --timeout=30 -q`
Expected: existing tests unaffected.

- [ ] **Step 4: Commit**

```bash
git add python-backend/agent/app.py
git commit -m "feat(python-backend): system-prompt A2UI catalog awareness"
```

---

## Task 8: Wire A2uiMessageRenderer into AgentChatPanel

**Files:**
- Modify: `frontend_merger/src/features/agent/AgentChatPanel.tsx`

- [ ] **Step 1: Verify `ToolOutputRenderer` usage in AgentChatPanel**

Grep:
```bash
grep -n "ToolOutputRenderer\|renderToolOutput" frontend_merger/src/features/agent/AgentChatPanel.tsx \
  frontend_merger/src/features/agent/components/ frontend_merger/src/features/agent/hooks/
```

- [ ] **Step 2: Confirm no code-change needed (Ansatz Y is transparent)**

Because ToolOutputRenderer already dispatches based on `toolName`, and Task 4 added the `render_a2ui_surface` branch, AgentChatPanel needs no direct edit — as long as it already renders tool-outputs via ToolOutputRenderer.

If the grep shows `<ToolOutputRenderer toolName={...} output={...} />` already mounted in the message-rendering flow: nothing to do here.

If the flow skips ToolOutputRenderer for some tool outputs, adjust the branch to always route through ToolOutputRenderer.

- [ ] **Step 3: Typecheck**

Run: `cd frontend_merger && bunx tsc --noEmit`
Expected: exit 0

- [ ] **Step 4: No commit if no change; otherwise:**

```bash
git add frontend_merger/src/features/agent/AgentChatPanel.tsx
git commit -m "chore(frontend_merger): route all tool-outputs through ToolOutputRenderer"
```

---

## Task 9: Files-page CopilotKit actions + readables

**Files:**
- Modify: `frontend_merger/src/features/files/FilesPage.tsx`

- [ ] **Step 1: Locate file-list-query usage**

Grep for how files are fetched in FilesPage (likely via tanstack-query hook):
```bash
grep -n "useQuery\|useFiles\|files" frontend_merger/src/features/files/FilesPage.tsx
```

- [ ] **Step 2: Add hooks at top of FilesPage component body**

Insert inside `FilesPage()` before the return statement (adapt variable names to what Step 1 revealed):

```tsx
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

// ...inside FilesPage():
const filesQuery = useFiles(); // existing hook — adjust name to actual
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
    "Persist a chat-attached file (still in chat-state) to blob storage so it shows up in /files",
  parameters: [
    {
      name: "attachmentId",
      type: "string",
      description: "The attachment id from currentChatAttachments",
      required: true,
    },
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

- [ ] **Step 3: Typecheck + biome**

Run: `cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/files/FilesPage.tsx`
Expected: exit 0

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/src/features/files/FilesPage.tsx
git commit -m "feat(frontend_merger): FilesPage — saveAttachmentToStorage action + recentFiles readable"
```

---

## Task 10: "Add to Chat" context-menu on file-card

**Files:**
- Modify: `frontend_merger/src/features/files/components/FileCard.tsx` (or the file-item component — locate via grep)

- [ ] **Step 1: Locate file-card component**

```bash
grep -rnE "FileCard|FileItem|FileRow" frontend_merger/src/features/files/components/ | head
```

Assume the file is `FileCard.tsx`. If another name, adapt below accordingly.

- [ ] **Step 2: Add context-menu with "Add to Chat"**

In FileCard, wrap the card root in a `<DropdownMenu>` (or `<ContextMenu>` if right-click preferred) from `@/components/ui/context-menu`:

```tsx
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useGlobalChat } from "@agent/stores/globalChatStore";

// Inside FileCard({ file, ... }) component body:
const { openChat } = useGlobalChat();

// Wrap the existing JSX:
return (
  <ContextMenu>
    <ContextMenuTrigger asChild>
      {/* existing FileCard JSX here */}
    </ContextMenuTrigger>
    <ContextMenuContent>
      <ContextMenuItem
        onClick={() =>
          openChat(`file-context:${file.id}:${file.name}`)
        }
      >
        Add to Chat
      </ContextMenuItem>
    </ContextMenuContent>
  </ContextMenu>
);
```

Note: `useGlobalChat` is the existing store — `openChat(ctx)` is already in its API (confirmed from code earlier).

If `ContextMenu` component does not yet exist in `@/components/ui/`, add it via shadcn CLI first: `cd frontend_merger && bunx shadcn@latest add context-menu`

- [ ] **Step 3: Typecheck + biome**

Run: `cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/files/components/FileCard.tsx`
Expected: exit 0

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/src/features/files/components/FileCard.tsx \
        frontend_merger/src/components/ui/context-menu.tsx
git commit -m "feat(frontend_merger): FileCard 'Add to Chat' context-menu"
```

---

## Task 11: Control-page CopilotKit action + readable

**Files:**
- Modify: `frontend_merger/src/features/control/ControlPage.tsx`

- [ ] **Step 1: Add hooks to ControlPage**

At the top of `ControlPage()` body, before the return / switch-rendering:

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
  description: "Currently active Control-UI tab (overview, agents, skills, sessions, tools, security, system, sandbox, audit, mcp, a2a, api)",
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

Run: `cd frontend_merger && bunx tsc --noEmit && bunx biome check src/features/control/ControlPage.tsx`
Expected: exit 0

- [ ] **Step 3: Commit**

```bash
git add frontend_merger/src/features/control/ControlPage.tsx
git commit -m "feat(frontend_merger): ControlPage — openControlTab action + activeControlTab readable"
```

---

## Task 12: `/api/copilotkit` BFF route (runtime via LiteLLM adapter)

**Files:**
- Create: `frontend_merger/src/app/api/copilotkit/route.ts`

- [ ] **Step 1: Write the route**

Create `frontend_merger/src/app/api/copilotkit/route.ts`:

```ts
/**
 * CopilotKit Runtime Endpoint.
 *
 * Thin BFF proxy using OpenAIAdapter with LiteLLM baseURL — provider-agnostic,
 * all LLM calls go through `http://localhost:4000` (LiteLLM gateway) which
 * routes to OpenRouter / Anthropic / OpenAI / Ollama based on user config.
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

const serviceAdapter = new OpenAIAdapter({
  openai,
  model: DEFAULT_MODEL,
});

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

- [ ] **Step 2: Add env vars to .env.example**

Append to `frontend_merger/.env.example`:

```bash
# CopilotKit runtime (forwards to LiteLLM)
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=sk-not-used-with-litellm
COPILOTKIT_DEFAULT_MODEL=anthropic/claude-haiku-4-5
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend_merger && bunx tsc --noEmit`
Expected: exit 0

- [ ] **Step 4: Smoke-test — route responds**

Run (stack must be up with LiteLLM on :4000):
```bash
curl -sSf -X POST http://localhost:3003/api/copilotkit \
  -H "Content-Type: application/json" \
  -d '{"operationName":"generateCopilotResponse","variables":{}}' | head -c 500
```
Expected: GraphQL error for malformed input, NOT "404 Not Found". Route exists.

Optional: if you don't have the stack up, skip this step — syntax-check alone proves the route is wired.

- [ ] **Step 5: Commit**

```bash
git add frontend_merger/src/app/api/copilotkit/route.ts frontend_merger/.env.example
git commit -m "feat(frontend_merger): /api/copilotkit runtime endpoint via LiteLLM adapter"
```

---

## Task 13: `usePersistentSurface` hook — localStorage + BFF sync

**Files:**
- Create: `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts`
- Create: `frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts`
- Create: `frontend_merger/src/app/api/surfaces/[surfaceId]/route.ts`
- Create: `python-backend/alembic/versions/027_user_surfaces.py`

- [ ] **Step 1: Write alembic migration**

Create `python-backend/alembic/versions/027_user_surfaces.py`:

```python
"""027_user_surfaces — persistent A2UI surfaces per user.

Revision ID: 027_user_surfaces
Revises: 026_smart_routing_config
Create Date: 2026-04-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "027_user_surfaces"
down_revision = "026_smart_routing_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.create_table(
        "user_surfaces",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("surface_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("surface_json", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("user_id", "surface_id"),
        schema="agent",
    )
    op.create_index(
        "ix_user_surfaces_updated",
        "user_surfaces",
        ["updated_at"],
        schema="agent",
    )


def downgrade() -> None:
    op.drop_index("ix_user_surfaces_updated", table_name="user_surfaces", schema="agent")
    op.drop_table("user_surfaces", schema="agent")
```

- [ ] **Step 2: Write BFF route**

Create `frontend_merger/src/app/api/surfaces/[surfaceId]/route.ts`:

```ts
/**
 * Surface persistence (Ansatz Y — static snapshots only; live-data patterns phase-2).
 * GET  /api/surfaces/[surfaceId]  → returns { surface_json, schema_version } or 404
 * PUT  /api/surfaces/[surfaceId]  → upserts surface JSON
 *
 * Proxies to go-appservice which owns postgres access. If go-appservice doesn't
 * expose this yet, fallback to direct postgres via the shared pool (tracked as
 * a follow-up — for now go-appservice must add /api/v1/surfaces/* routes).
 */

import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";

const SCHEMA_VERSION = 1;

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ surfaceId: string }> },
) {
  const { surfaceId } = await context.params;
  const base = getGatewayBaseURL();
  const res = await fetch(
    `${base}/api/v1/surfaces/${encodeURIComponent(surfaceId)}`,
    {
      method: "GET",
      headers: forwardAuth(req),
      cache: "no-store",
    },
  );
  if (res.status === 404) {
    return Response.json({ surface: null }, { status: 404 });
  }
  const body = await res.json().catch(() => null);
  return Response.json(body ?? { surface: null }, { status: res.status });
}

export async function PUT(
  req: NextRequest,
  context: { params: Promise<{ surfaceId: string }> },
) {
  const { surfaceId } = await context.params;
  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object" || !body.surface_json) {
    return Response.json({ error: "surface_json required" }, { status: 400 });
  }
  const base = getGatewayBaseURL();
  const res = await fetch(
    `${base}/api/v1/surfaces/${encodeURIComponent(surfaceId)}`,
    {
      method: "PUT",
      headers: {
        ...forwardAuth(req),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        schema_version: SCHEMA_VERSION,
        surface_json: body.surface_json,
      }),
    },
  );
  return Response.json(
    (await res.json().catch(() => ({ ok: res.ok }))),
    { status: res.status },
  );
}

function forwardAuth(req: NextRequest): Record<string, string> {
  const auth = req.headers.get("authorization");
  const user = req.headers.get("x-auth-user");
  const role = req.headers.get("x-user-role");
  const h: Record<string, string> = {};
  if (auth) h.authorization = auth;
  if (user) h["x-auth-user"] = user;
  if (role) h["x-user-role"] = role;
  return h;
}
```

- [ ] **Step 3: Write the hook test**

Create `frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts`:

```ts
import { renderHook, act, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePersistentSurface } from "../usePersistentSurface";

beforeEach(() => {
  window.localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const SCHEMA_VERSION = 1;

describe("usePersistentSurface", () => {
  it("loads nothing on first mount when localStorage empty", () => {
    const { result } = renderHook(() => usePersistentSurface("main"));
    expect(result.current.surfaceJson).toBeNull();
  });

  it("persists update to localStorage + posts to BFF", async () => {
    const { result } = renderHook(() => usePersistentSurface("main"));
    await act(async () => {
      result.current.save({ type: "Card", children: [] });
    });
    const stored = window.localStorage.getItem("a2ui.surface.main");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.schema_version).toBe(SCHEMA_VERSION);
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/surfaces/main",
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });

  it("drops stale schema on mount", () => {
    window.localStorage.setItem(
      "a2ui.surface.main",
      JSON.stringify({ schema_version: 99, surface_json: { type: "Card" } }),
    );
    const { result } = renderHook(() => usePersistentSurface("main"));
    expect(result.current.surfaceJson).toBeNull();
  });
});
```

- [ ] **Step 4: Implement the hook**

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

export function usePersistentSurface(surfaceId: string): PersistentSurfaceApi {
  const [surfaceJson, setSurfaceJson] = useState<Record<string, unknown> | null>(null);

  // Load on mount: localStorage first (instant), then BFF async (cross-device)
  useEffect(() => {
    const raw = window.localStorage.getItem(storageKey(surfaceId));
    if (raw) {
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
    }

    // Background fetch
    let cancelled = false;
    fetch(`/api/surfaces/${encodeURIComponent(surfaceId)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => {
        if (cancelled || !body?.surface_json) return;
        if (body.schema_version !== SCHEMA_VERSION) return;
        setSurfaceJson(body.surface_json);
        window.localStorage.setItem(
          storageKey(surfaceId),
          JSON.stringify({
            schema_version: SCHEMA_VERSION,
            surface_json: body.surface_json,
          }),
        );
      })
      .catch(() => {
        /* silent — localStorage already loaded */
      });

    return () => {
      cancelled = true;
    };
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

      // Fire-and-forget to BFF
      fetch(`/api/surfaces/${encodeURIComponent(surfaceId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ surface_json: json }),
      }).catch(() => {
        /* queue retry could be added in phase-2 */
      });
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

- [ ] **Step 5: Run migration**

```bash
cd python-backend && APP_ENV=development uv run alembic upgrade head
```
Expected: migration 027 applied; `agent.user_surfaces` table exists.

Verify:
```bash
psql postgres://postgres:postgres@localhost:5433/hindsight_dev -c "\d agent.user_surfaces"
```
Expected: table with user_id, surface_id, schema_version, surface_json, updated_at columns.

- [ ] **Step 6: Run hook test**

Run: `cd frontend_merger && bunx vitest run src/features/agent/hooks/__tests__/usePersistentSurface.test.ts`
Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add python-backend/alembic/versions/027_user_surfaces.py \
        frontend_merger/src/app/api/surfaces/ \
        frontend_merger/src/features/agent/hooks/usePersistentSurface.ts \
        frontend_merger/src/features/agent/hooks/__tests__/usePersistentSurface.test.ts
git commit -m "feat(persistence): user_surfaces table + usePersistentSurface hook + BFF route"
```

**NOTE (follow-up):** go-appservice does not yet expose `/api/v1/surfaces/*`. The BFF route forwards there but will 502 until the Go side is added — that is tracked as a follow-up task outside this plan. For E2E in phase-1, the BFF route can be adjusted to write directly via a python-backend helper if needed (keep scope small: localStorage works standalone until Go side lands).

---

## Task 14: Playwright E2E tests #9–#12

**Files:**
- Create: `frontend_merger/tests/a2ui-integration.spec.ts`

- [ ] **Step 1: Locate existing Playwright config and pattern**

```bash
cat frontend_merger/playwright.config.ts
ls frontend_merger/tests/
```

Review one of the existing 8 tests for structural conventions (baseURL, port, snapshot vs assertion style).

- [ ] **Step 2: Create new test file**

Create `frontend_merger/tests/a2ui-integration.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test.describe("A2UI + CopilotKit integration", () => {
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
    // Either the A2UIRenderer fallback or our own fallback copy:
    await expect(canvas).toContainText(/canvas bereit|widget wird geladen/i);
  });

  test("#11 Chat message with A2UI tool-result renders inline widget", async ({ page }) => {
    // Mock the /api/agent/chat SSE response to emit a render_a2ui_surface tool-result
    await page.route("**/api/agent/chat", async (route) => {
      const payload =
        [
          "data: " +
            JSON.stringify({ type: "thread-id", thread_id: "t1" }) +
            "\n\n",
          "data: " +
            JSON.stringify({
              type: "tool-result",
              tool_call_id: "tc1",
              result: {
                type: "a2ui",
                surface_id: "chat-inline-1",
                tree: { type: "Card", children: [{ type: "Text", text: "hello-widget" }] },
              },
            }) +
            "\n\n",
          "data: " + JSON.stringify({ type: "finish" }) + "\n\n",
        ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "x-vercel-ai-ui-message-stream": "v1" },
        body: payload,
      });
    });

    await page.goto("/");
    // Open agent sidebar (button in topbar labeled "Agent")
    await page.getByRole("button", { name: /agent/i }).click();

    // Type + send
    const composer = page.getByRole("textbox").first();
    await composer.fill("show test widget");
    await composer.press("Enter");

    // Widget text must appear in a chat message
    await expect(page.getByText("hello-widget")).toBeVisible({ timeout: 10_000 });
  });

  test("#12 FileCard 'Add to Chat' opens chat with context", async ({ page }) => {
    await page.goto("/files");
    // Files page must have at least one card — if none, seed-via-mock is out of scope
    const card = page.locator('[data-testid="file-card"]').first();
    await card.click({ button: "right" });
    await page.getByRole("menuitem", { name: /add to chat/i }).click();
    // Agent sheet should now be open
    const sheet = page.locator('[role="dialog"]').first();
    await expect(sheet).toBeVisible();
  });
});
```

- [ ] **Step 3: Run tests (skip #11/#12 if stack not up)**

Run: `cd frontend_merger && bunx playwright test a2ui-integration.spec.ts --reporter=list`
Expected: #9 + #10 PASS with dev-server running. #11 + #12 may be SKIPPED or marked as `.fixme` if no stack.

If #12 fails because FileCard has no `data-testid="file-card"`, add the attribute to the FileCard root in Task 10 (retroactive: `git commit --amend` or a new small commit).

- [ ] **Step 4: Commit**

```bash
git add frontend_merger/tests/a2ui-integration.spec.ts
git commit -m "test(frontend_merger): A2UI + CopilotKit integration Playwright tests #9-#12"
```

---

## Task 15: Final verification — full-stack smoke

**Files:** none (runbook)

- [ ] **Step 1: Start stack**

```bash
./scripts/setup-garage.sh   # idempotent if already run
./scripts/dev-stack.sh --matrix-chat
```

Wait for all services to report `✓`.

- [ ] **Step 2: Open browser**

Open `http://localhost:3003` in Chrome. Verify:
- TopBar shows: Matrix · Files · Memory · Control (+ Agent toggle)
- Landing A2UI canvas visible with idle placeholder
- Console: **0 errors** (expect a few warnings OK)

- [ ] **Step 3: Exercise each route**

Click each TopBar button → page loads within 3s, no console errors.

- [ ] **Step 4: Open agent sidebar, send a simple prompt**

Sidebar opens. Send `"zeig mir eine einfache Card mit Hallo"`. Agent responds:
- Either as plain text ("Hallo!") if LLM did not call the tool
- Or as an inline A2UI-Card (emerald-bordered) if the agent invoked `render_a2ui_surface`

If the LLM never calls the tool, the system-prompt may need tuning — adjust A2UI_INSTRUCTIONS wording in `python-backend/agent/app.py` (Task 7) and restart python-agent.

- [ ] **Step 5: Trigger `openControlTab` via prompt**

In agent sidebar: `"go to the agents tab in control"`.
Expected: the page navigates to `/control/agents` (if CopilotKit is enabled + runtime-URL set).

If `NEXT_PUBLIC_COPILOTKIT_ENABLED=false`, this skips silently — that's expected for a default-off dev setup. Toggle to `true` in `.env.local` + restart to fully exercise.

- [ ] **Step 6: Persistence round-trip**

Dispatch a widget to `surfaceId="main"` (agent prompt: `"render a test dashboard with a Card and Text on surface main"`). Verify widget appears on `/` landing. Reload the page — widget still there (localStorage).

- [ ] **Step 7: No commit — this is verification only**

---

## Deferred / Phase-2 (NOT in this plan)

Explicitly out of scope per spec §13 + §17.1.14:

- Native A2UI SSE packet-types (`a2ui-surface-start`, `a2ui-update-components`, `a2ui-update-data-model`, `a2ui-surface-end`) and the SSE-parser extension in `useChatSession`
- Live-data binding patterns (agent-driven `updateDataModel` stream / client-side `useQuery` data-sources)
- `a2ui-agent-sdk` Python install and integration
- Custom A2UI widget-catalog beyond `basicCatalog` (e.g. wrapping existing ChartWidget/PortfolioCard as A2UI catalog entries via `createReactComponent`)
- go-appservice `/api/v1/surfaces/*` routes — Next.js BFF will 502 until added (Task 13 note)
- Matrix-chat CopilotKit integration (exec-10 territory)
- Route consolidation into `/control/*`

---

## Rollback-Strategy

Each task commits independently and produces either additive new files or small edits. Individual task rollback:

```bash
# Drop the last commit (soft — keeps working tree)
git reset HEAD~1

# Or drop + discard changes:
git reset --hard HEAD~1

# Revert a specific commit (leaves history intact):
git revert <commit-sha>
```

Full-feature rollback (drop everything this plan introduced):

```bash
# Assuming plan-start SHA is <START>:
git diff <START>..HEAD --name-only | xargs -r rm -f 2>/dev/null
git reset --hard <START>
```

For the alembic migration (Task 13):
```bash
cd python-backend && APP_ENV=development uv run alembic downgrade 026_smart_routing_config
```

## Self-Review Notes

**Spec coverage:** Every §19 step has at least one task. Task 6 + 7 cover §19.6 (python tool + system-prompt). Task 14 covers §11 testing.

**Type consistency:**
- `render_a2ui_surface` tool-name appears identical in: Task 4 (frontend dispatch), Task 6 (python tool), Task 7 (system-prompt), Task 14 (test mock). ✓
- `surface_id` vs `surfaceId` — python uses snake_case (tool args), TypeScript uses camelCase at the hook boundary. Envelope payload passed through uses `surface_id` (python format) and is consumed as-is in `ToolOutputRenderer` (`payload.surface_id`). ✓ consistent with A2UI v0.9 spec (which uses `surfaceId` — minor divergence; acceptable because the frontend only reads it, not type-serializes).
- `schema_version` = 1 consistent in Task 13 hook + BFF + migration. ✓

**Placeholder scan:** No TBD, TODO, "implement later", or unconcreted placeholders.
