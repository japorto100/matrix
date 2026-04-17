/**
 * Jotai Atoms — feingranularer State für Agent Chat.
 *
 * Zustand: globaler App-State (open, mode, badge)
 * Jotai: per-message / per-tool atomarer State (collapsed tools, usage map)
 *
 * Vorteil: Components subscriben nur auf die Atome die sie brauchen.
 * Ein Tool-Collapse re-rendert nicht die ganze Message-Liste.
 */

import { atom } from "jotai";
import type { MessageUsage } from "../hooks/useChatSession";

// ── Tool Collapse State ─────────────────────────────────────────────────────
// Set von toolCallIds die collapsed sind.
// Wird von AgentChatToolBlock gelesen und von toggleToolCollapse geschrieben.

export const collapsedToolsAtom = atom<Set<string>>(new Set<string>());

export const toggleToolCollapseAtom = atom(null, (get, set, toolCallId: string) => {
	const prev = get(collapsedToolsAtom);
	const next = new Set(prev);
	if (next.has(toolCallId)) next.delete(toolCallId);
	else next.add(toolCallId);
	set(collapsedToolsAtom, next);
});

// ── Per-Message Usage Tracking ──────────────────────────────────────────────
// Map von messageId → Usage (tokens, cost, finishReason).
// Wird von useChatSession geschrieben und von AgentChatMessage gelesen.

export const usageMapAtom = atom<Map<string, MessageUsage>>(new Map());
