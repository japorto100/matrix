// Dynamic model list from backend (exec-16)
// Fetches user's available models, grouped by cloud/local.
// Falls back to static list if backend unreachable.

import { useCallback, useEffect, useRef, useState } from "react";

export interface AvailableModel {
	id: string;
	group: "cloud" | "local";
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
}

const FALLBACK_MODELS: AvailableModel[] = [
	{ id: "claude-sonnet-4-6", group: "cloud" },
	{ id: "claude-opus-4-6", group: "cloud" },
	{ id: "claude-haiku-4-5", group: "cloud" },
];

export function useAvailableModels() {
	const [models, setModels] = useState<AvailableModel[]>(FALLBACK_MODELS);
	const [defaultModel, setDefaultModel] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const fetched = useRef(false);

	const refresh = useCallback(async () => {
		try {
			const res = await fetch("/api/agent/models", { cache: "no-store" });
			if (!res.ok) return;

			const data = (await res.json()) as LlmSettingsResponse;
			setDefaultModel(data.default_model);

			const result: AvailableModel[] = [];
			for (const provider of data.providers) {
				if (!provider.is_active || provider.available_models.length === 0) continue;
				const group = provider.type === "local" ? "local" : "cloud";
				for (const modelId of provider.available_models) {
					result.push({ id: modelId, group });
				}
			}

			if (result.length > 0) {
				setModels(result);
			}
		} catch {
			// keep fallback
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		if (fetched.current) return;
		fetched.current = true;
		void refresh();
	}, [refresh]);

	const cloudModels = models.filter((m) => m.group === "cloud");
	const localModels = models.filter((m) => m.group === "local");

	return { models, cloudModels, localModels, defaultModel, loading, refresh };
}
