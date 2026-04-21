// Dynamic model list from backend (exec-16 + exec-19 Stufe 5b)
// Source of truth: User's selected_models from control-ui DB.
// Fallback: provider discovery. Last resort: openrouter/free router.
// NO hardcoded model IDs anywhere.

import { useCallback, useEffect, useRef, useState } from "react";

export interface AvailableModel {
	id: string;
	group: "cloud" | "local" | "router";
}

export interface RouterOption {
	id: string;
	label: string;
	cost: string;
}

interface ProviderData {
	id: string;
	type: "cloud" | "local";
	is_active: boolean;
	available_models: string[];
}

interface LlmSettingsResponse {
	default_model: string | null;
	providers: ProviderData[];
	routers?: RouterOption[];
}

// System fallback router — used when no models are configured
const FALLBACK_ROUTER: AvailableModel = { id: "openrouter/free", group: "router" };

export function useAvailableModels() {
	const [models, setModels] = useState<AvailableModel[]>([]);
	const [routers, setRouters] = useState<RouterOption[]>([]);
	const [defaultModel, setDefaultModel] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const fetched = useRef(false);

	const refresh = useCallback(async () => {
		let hasSelectedModels = false;

		try {
			// 1. User's selected models from control-ui (primary source)
			const selectedRes = await fetch("/api/control/user/llm/selected-models", {
				cache: "no-store",
			});
			if (selectedRes.ok) {
				const data = (await selectedRes.json()) as { selected_models?: string[] };
				if (data.selected_models && data.selected_models.length > 0) {
					setModels(data.selected_models.map((id) => ({ id, group: "cloud" as const })));
					hasSelectedModels = true;
				}
			}
		} catch {
			// continue to fallback
		}

		try {
			// 2. Default model + routers + provider discovery
			const res = await fetch("/api/agent/models", { cache: "no-store" });
			if (res.ok) {
				const data = (await res.json()) as LlmSettingsResponse;
				if (data.default_model) setDefaultModel(data.default_model);
				if (data.routers) setRouters(data.routers);

				// If no selected models, use all active provider models
				if (!hasSelectedModels) {
					const discovered: AvailableModel[] = [];
					for (const provider of data.providers) {
						if (!provider.is_active || provider.available_models.length === 0) continue;
						const group = provider.type === "local" ? "local" : "cloud";
						for (const modelId of provider.available_models) {
							discovered.push({ id: modelId, group });
						}
					}
					if (discovered.length > 0) {
						setModels(discovered);
						hasSelectedModels = true;
					}
				}
			}
		} catch {
			// continue to fallback
		}

		// 3. Last resort: openrouter/free as only option
		if (!hasSelectedModels) {
			setModels([FALLBACK_ROUTER]);
		}

		setLoading(false);
	}, []);

	useEffect(() => {
		if (fetched.current) return;
		fetched.current = true;
		void refresh();
	}, [refresh]);

	const cloudModels = models.filter((m) => m.group === "cloud");
	const localModels = models.filter((m) => m.group === "local");

	return { models, cloudModels, localModels, routers, defaultModel, loading, refresh };
}
