/**
 * A2UI Canvas — mounts an A2UIRenderer surface.
 *
 * TWO DISTINCT USAGES (unterschiedliche semantics, nicht nur IDs):
 *
 *   1. **Main-Canvas (LandingPage /):** Standalone Dashboard-surface.
 *      Langlebig, session-übergreifend, vom User steuerbar (resize/hide).
 *      Agent streamed hier "globale" widget-trees (Portfolio, Charts-grid, etc).
 *      Typischer surfaceId: `"main"`.
 *
 *   2. **Chat-Inline-Canvas (im AgentChatPanel):** In-Message widget-rendering.
 *      Gebunden an eine chat-message, lebenszyklus = chat-turn.
 *      Agent streamed hier message-specific UI (form zum ausfüllen, konfirm-card,
 *      quick-chart als antwort). Jede message kann eigene surfaceId haben,
 *      typischer prefix: `"chat-<messageId>"`.
 *
 * Multiple surfaces coexist — A2UIProvider managed sie parallel.
 * A2UIRenderer rendert eigenes fallback wenn surface noch nicht dispatched.
 *
 * Data source (plan-v2 Phase-2 #34): the canvas is purely reactive. It
 * reads from the shared A2UI store populated by `useA2uiSseSubscriber`
 * (wired in ``useChatSession.onData``). Any ``data-a2ui-*`` packet the
 * agent emits during an active chat turn flows into the store and the
 * renderer picks it up — same store feeds this canvas AND any chat-
 * inline canvases. Push-from-agent while chat is closed requires a
 * dedicated persistent channel (SSE or WS) which is out of scope for
 * #34 — track as follow-up if needed.
 */

"use client";

import { A2UIRenderer } from "@copilotkit/a2ui-renderer";
import { Bot } from "lucide-react";
import type { ReactNode } from "react";

interface A2uiCanvasProps {
	/** Unique surface-id that the agent dispatches widgets to. */
	surfaceId: string;
	/** Container styling (tailwind classes). */
	className?: string;
	/** Custom fallback UI shown when no surface is mounted yet. */
	fallback?: ReactNode;
}

const defaultFallback = (
	<div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-2 text-center p-6">
		<Bot className="h-8 w-8 text-muted-foreground/60" />
		<p className="text-sm text-muted-foreground">
			Canvas bereit. Sobald der python-agent A2UI-Widgets streamed (via SSE /api/agent/chat),
			erscheinen hier dynamische Widgets.
		</p>
	</div>
);

export function A2uiCanvas({ surfaceId, className, fallback = defaultFallback }: A2uiCanvasProps) {
	return (
		<section
			aria-label={`A2UI surface ${surfaceId}`}
			className={
				className ??
				"min-h-[280px] rounded-lg border border-dashed border-border bg-card/30 overflow-hidden"
			}
		>
			<A2UIRenderer surfaceId={surfaceId} fallback={fallback} />
		</section>
	);
}
