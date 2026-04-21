"use client";

// Dynamic model metadata from control-ui backend (exec-19 Stufe 5b/5c).
// Provides pricing, context length, reasoning capabilities per model.
// Replaces hardcoded COST_PER_TOKEN + MODEL_MAX_CONTEXT in useChatSession.

import { useCallback, useEffect, useRef, useState } from "react";

export interface ModelMeta {
	id: string;
	context_length: number;
	max_output_tokens: number;
	prompt_price_per_mtok: number | null;
	completion_price_per_mtok: number | null;
	supports_reasoning: boolean;
	reasoning_type: string | null; // "effort" | "thinking" | null
	reasoning_levels: string[] | null; // null = unknown, LiteLLM validates
}

// Cache: model id → ModelMeta
const modelMetaCache = new Map<string, ModelMeta>();

const FALLBACK_META: ModelMeta = {
	id: "",
	context_length: 200_000,
	max_output_tokens: 8192,
	prompt_price_per_mtok: null,
	completion_price_per_mtok: null,
	supports_reasoning: false,
	reasoning_type: null,
	reasoning_levels: null,
};

async function fetchModelMeta(modelId: string): Promise<ModelMeta> {
	const cached = modelMetaCache.get(modelId);
	if (cached) return cached;

	try {
		const res = await fetch(
			`/api/control/user/llm/models?search=${encodeURIComponent(modelId)}&limit=1`,
			{ cache: "no-store" },
		);
		if (!res.ok) return { ...FALLBACK_META, id: modelId };
		const data = await res.json();
		const model = data.models?.[0];
		if (!model) return { ...FALLBACK_META, id: modelId };

		const meta: ModelMeta = {
			id: model.id,
			context_length: model.context_length ?? 200_000,
			max_output_tokens: model.max_output_tokens ?? 8192,
			prompt_price_per_mtok: model.prompt_price_per_mtok ?? null,
			completion_price_per_mtok: model.completion_price_per_mtok ?? null,
			supports_reasoning: model.supports_reasoning ?? false,
			reasoning_type: model.reasoning_type ?? null,
			reasoning_levels: model.reasoning_levels ?? null,
		};
		modelMetaCache.set(modelId, meta);
		return meta;
	} catch {
		return { ...FALLBACK_META, id: modelId };
	}
}

/**
 * Returns dynamic model metadata for the currently selected model.
 * Fetches from backend on model change, caches results.
 */
export function useModelInfo(modelId: string) {
	const [meta, setMeta] = useState<ModelMeta>(
		() => modelMetaCache.get(modelId) ?? { ...FALLBACK_META, id: modelId },
	);
	const prevModelRef = useRef(modelId);

	const refresh = useCallback(async (id: string) => {
		const result = await fetchModelMeta(id);
		setMeta(result);
	}, []);

	useEffect(() => {
		if (modelId !== prevModelRef.current || !modelMetaCache.has(modelId)) {
			prevModelRef.current = modelId;
			void refresh(modelId);
		}
	}, [modelId, refresh]);

	return meta;
}

/**
 * Compute cost in USD from token counts + model pricing.
 * Returns undefined if pricing not available.
 */
export function computeCost(
	meta: ModelMeta,
	promptTokens: number,
	completionTokens: number,
): number | undefined {
	if (meta.prompt_price_per_mtok == null || meta.completion_price_per_mtok == null) {
		return undefined;
	}
	if (!promptTokens && !completionTokens) return undefined;
	return (
		(promptTokens * meta.prompt_price_per_mtok) / 1_000_000 +
		(completionTokens * meta.completion_price_per_mtok) / 1_000_000
	);
}
