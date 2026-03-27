"use client";

// AC75/AC77: Global Chat Context — provides open state + context injection
// AC88: badgeCount — proactive badge on Bot icon
// AC89: mode — sheet (overlay) vs split (pushes content)
// AC93: mode "rail" — persistent 240px sidebar, always visible regardless of open state

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type ChatMode = "sheet" | "split" | "rail";

interface GlobalChatContextValue {
	open: boolean;
	mode: ChatMode;
	/** Proactive badge count (AC88) — pulses on Bot icon when > 0 */
	badgeCount: number;
	/** Injected context string shown as chip in chat header (AC87/AC94) */
	chatContext: string | null;
	openChat: (ctx?: string) => void;
	closeChat: () => void;
	toggleChat: () => void;
	toggleMode: () => void;
	/** Inject context without changing open state */
	setChatContext: (ctx: string | null) => void;
	clearChatContext: () => void;
	/** Increment proactive badge (AC88) */
	incrementBadge: () => void;
	clearBadge: () => void;
}

const GlobalChatContext = createContext<GlobalChatContextValue | null>(null);

export function GlobalChatProvider({ children }: { children: React.ReactNode }) {
	const [open, setOpen] = useState(false);
	const [mode, setMode] = useState<ChatMode>("sheet");
	const [badgeCount, setBadgeCount] = useState(0);
	const [chatContext, setChatContext] = useState<string | null>(null);

	const openChat = useCallback((ctx?: string) => {
		if (ctx) setChatContext(ctx);
		setOpen(true);
		setBadgeCount(0);
	}, []);

	const closeChat = useCallback(() => setOpen(false), []);

	const toggleChat = useCallback(() => {
		setOpen((v) => {
			if (!v) setBadgeCount(0); // clear badge on open
			return !v;
		});
	}, []);

	// AC93: cycles sheet → split → rail → sheet
	const toggleMode = useCallback(() => {
		setMode((m) => {
			if (m === "sheet") return "split";
			if (m === "split") return "rail";
			return "sheet";
		});
	}, []);

	const clearChatContext = useCallback(() => setChatContext(null), []);

	const incrementBadge = useCallback(() => {
		setOpen((currentOpen) => {
			if (!currentOpen) setBadgeCount((n) => n + 1);
			return currentOpen;
		});
	}, []);

	const clearBadge = useCallback(() => setBadgeCount(0), []);

	const value = useMemo(
		() => ({
			open,
			mode,
			badgeCount,
			chatContext,
			openChat,
			closeChat,
			toggleChat,
			toggleMode,
			setChatContext,
			clearChatContext,
			incrementBadge,
			clearBadge,
		}),
		[
			open,
			mode,
			badgeCount,
			chatContext,
			openChat,
			closeChat,
			toggleChat,
			toggleMode,
			clearChatContext,
			incrementBadge,
			clearBadge,
		],
	);

	return <GlobalChatContext.Provider value={value}>{children}</GlobalChatContext.Provider>;
}

export function useGlobalChat() {
	const ctx = useContext(GlobalChatContext);
	if (!ctx) throw new Error("useGlobalChat must be used within GlobalChatProvider");
	return ctx;
}
