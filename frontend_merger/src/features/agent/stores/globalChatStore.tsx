"use client";

// AC75/AC77: Global Chat State — Zustand Store (SOTA 2026, ersetzt React Context)
// AC88: badgeCount — proactive badge on Bot icon
// AC89: mode — sheet (overlay) vs split (pushes content)
// AC93: mode "rail" — persistent 240px sidebar

import { create } from "zustand";

export type ChatMode = "sheet" | "split" | "rail";

interface GlobalChatState {
	open: boolean;
	mode: ChatMode;
	badgeCount: number;
	chatContext: string | null;
	openChat: (ctx?: string) => void;
	closeChat: () => void;
	toggleChat: () => void;
	toggleMode: () => void;
	setChatContext: (ctx: string | null) => void;
	clearChatContext: () => void;
	incrementBadge: () => void;
	clearBadge: () => void;
}

export const useGlobalChat = create<GlobalChatState>((set) => ({
	open: false,
	mode: "sheet",
	badgeCount: 0,
	chatContext: null,

	openChat: (ctx) =>
		set((s) => ({
			open: true,
			badgeCount: 0,
			chatContext: ctx ?? s.chatContext,
		})),

	closeChat: () => set({ open: false }),

	toggleChat: () =>
		set((s) => ({
			open: !s.open,
			badgeCount: s.open ? s.badgeCount : 0,
		})),

	// AC93: cycles sheet → split → rail → sheet
	toggleMode: () =>
		set((s) => ({
			mode: s.mode === "sheet" ? "split" : s.mode === "split" ? "rail" : "sheet",
		})),

	setChatContext: (ctx) => set({ chatContext: ctx }),
	clearChatContext: () => set({ chatContext: null }),

	incrementBadge: () =>
		set((s) => ({
			badgeCount: s.open ? s.badgeCount : s.badgeCount + 1,
		})),

	clearBadge: () => set({ badgeCount: 0 }),
}));

// Backwards-compat: Components die GlobalChatProvider importieren brauchen keinen Provider mehr
// Zustand ist provider-free. Dieser Export ist ein No-Op Wrapper.
export function GlobalChatProvider({ children }: { children: React.ReactNode }) {
	return <>{children}</>;
}
