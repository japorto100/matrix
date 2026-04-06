import type { LayoutMode } from "@/features/trading/types";
import {
	createDbReadyJsonStorageAdapter,
	createLocalJsonStorageAdapter,
} from "@/lib/storage/adapter";

export interface FusionPreferences {
	favorites: string[];
	layout: LayoutMode;
	updatedAt: number;
}

const PREFERENCES_KEY = "fusion-preferences";

const storage = createDbReadyJsonStorageAdapter(createLocalJsonStorageAdapter("tradeview:"));

export const DEFAULT_FUSION_PREFERENCES: FusionPreferences = {
	favorites: [],
	layout: "single",
	updatedAt: 0,
};

export function readFusionPreferences(): FusionPreferences {
	const value = storage.getJSON(PREFERENCES_KEY, DEFAULT_FUSION_PREFERENCES);

	return {
		favorites: Array.isArray(value.favorites) ? value.favorites : [],
		layout: value.layout ?? "single",
		updatedAt: typeof value.updatedAt === "number" ? value.updatedAt : 0,
	};
}

export function writeFusionPreferences(
	updates: Partial<Pick<FusionPreferences, "favorites" | "layout">>,
): FusionPreferences {
	const current = readFusionPreferences();
	const next: FusionPreferences = {
		...current,
		...updates,
		updatedAt: Date.now(),
	};
	storage.setJSON(PREFERENCES_KEY, next);
	return next;
}
