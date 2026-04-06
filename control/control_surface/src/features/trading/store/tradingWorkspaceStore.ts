import { create } from "zustand";
import { ALL_FUSION_SYMBOLS, type FusionSymbol, WATCHLIST_CATEGORIES } from "@/lib/fusion-symbols";
import { readFusionPreferences, writeFusionPreferences } from "@/lib/storage/preferences";
import type { LayoutMode } from "../types";

interface TradingWorkspaceState {
	currentSymbol: FusionSymbol;
	favorites: string[];
	layout: LayoutMode;
	// Actions
	setCurrentSymbol: (symbol: FusionSymbol) => void;
	toggleFavorite: (symbolId: string) => void;
	setLayout: (layout: LayoutMode) => void;
	setFavorites: (favorites: string[]) => void;
}

const prefs = readFusionPreferences();
const DEFAULT_TRADING_SYMBOL = WATCHLIST_CATEGORIES.crypto[0] ?? ALL_FUSION_SYMBOLS[0];

if (!DEFAULT_TRADING_SYMBOL) {
	throw new Error("Trading workspace requires at least one fusion symbol");
}

export const useTradingWorkspaceStore = create<TradingWorkspaceState>((set) => ({
	currentSymbol: DEFAULT_TRADING_SYMBOL,
	favorites: prefs.favorites ?? [],
	layout: prefs.layout ?? "single",

	setCurrentSymbol: (symbol) => set({ currentSymbol: symbol }),

	toggleFavorite: (symbolId) =>
		set((state) => {
			const next = state.favorites.includes(symbolId)
				? state.favorites.filter((s) => s !== symbolId)
				: [...state.favorites, symbolId];
			writeFusionPreferences({ favorites: next });
			return { favorites: next };
		}),

	setLayout: (layout) => {
		writeFusionPreferences({ layout });
		set({ layout });
	},

	setFavorites: (favorites) => {
		writeFusionPreferences({ favorites });
		set({ favorites });
	},
}));
