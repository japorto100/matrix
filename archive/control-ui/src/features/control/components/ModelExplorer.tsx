"use client";

import { Filter, Sparkles } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAccountInfo, useModelList, useSelectedModels } from "@/lib/queries/hooks";
import { ModelCard } from "./ModelCard";
import { type FilterKey, ModelFilterSidebar, type ModelFilters } from "./ModelFilterSidebar";

const INITIAL_FILTERS: ModelFilters = {
	search: "",
	freeOnly: false,
	toolsOnly: false,
	visionOnly: false,
	reasoningOnly: false,
	structuredOnly: false,
	affordableOnly: false,
	providerFilter: "",
	minContext: "0",
	maxPrice: "0",
	modalityFilter: "",
	minOutput: "0",
	sortBy: "name",
};

export function ModelExplorer() {
	const [filters, setFilters] = useState<ModelFilters>(INITIAL_FILTERS);
	const { selected, save, isSaving } = useSelectedModels();
	const [localSelected, setLocalSelected] = useState<Set<string> | null>(null);
	const accountQuery = useAccountInfo();

	const creditsRemaining =
		accountQuery.data?.providers?.find((p) => p.limit_remaining != null)?.limit_remaining ?? null;

	const effectiveSelected = localSelected ?? selected;

	const queryFilters = useMemo(() => {
		const f: Record<string, string> = { sort_by: filters.sortBy, limit: "200" };
		if (filters.search.trim()) f.search = filters.search.trim();
		if (filters.freeOnly || filters.maxPrice === "free") f.free_only = "true";
		if (filters.toolsOnly) f.supports_tools = "true";
		if (filters.visionOnly) f.supports_vision = "true";
		if (filters.reasoningOnly) f.supports_reasoning = "true";
		if (filters.structuredOnly) f.supports_structured_output = "true";
		if (filters.modalityFilter) f.modality = filters.modalityFilter;
		if (filters.providerFilter) f.provider = filters.providerFilter;
		if (filters.minContext !== "0") f.min_context = filters.minContext;
		if (filters.affordableOnly && creditsRemaining != null && creditsRemaining > 0) {
			// Convert credits remaining ($) to max acceptable $/Mtok
			// Logic: if I have $5 remaining, show models where 1M tokens costs <= $5
			f.max_price = String(creditsRemaining);
		} else if (filters.maxPrice !== "0" && filters.maxPrice !== "free") {
			f.max_price = filters.maxPrice;
		}
		if (filters.minOutput !== "0") f.min_output = filters.minOutput;
		return f;
	}, [filters, creditsRemaining]);

	const { data, isLoading, error } = useModelList(queryFilters);
	const models = data?.models ?? [];
	const facets = data?.facets;
	const total = data?.total ?? 0;

	const handleFilterChange = useCallback(<K extends FilterKey>(key: K, value: ModelFilters[K]) => {
		setFilters((prev) => ({ ...prev, [key]: value }));
	}, []);

	function toggleModel(id: string) {
		setLocalSelected((prev) => {
			const base = prev ?? new Set(selected);
			const next = new Set(base);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	}

	async function saveSelection() {
		try {
			await save(effectiveSelected);
			toast.success(`${effectiveSelected.size} models saved for Agent Chat`);
			setLocalSelected(null);
		} catch {
			toast.error("Failed to save model selection");
		}
	}

	return (
		<div className="space-y-4">
			<div className="flex items-center gap-2">
				<Sparkles className="text-primary h-5 w-5" />
				<h3 className="text-lg font-semibold">Model Explorer</h3>
				{facets && (
					<Badge variant="secondary" className="ml-auto">
						{total} / {facets.total_all} models
					</Badge>
				)}
				{effectiveSelected.size > 0 && (
					<Button size="sm" onClick={saveSelection} disabled={isSaving}>
						{isSaving ? "Saving..." : `Save ${effectiveSelected.size} selected`}
					</Button>
				)}
			</div>
			<div className="flex flex-col gap-4 md:flex-row">
				<ModelFilterSidebar
					filters={filters}
					onChange={handleFilterChange}
					facets={facets}
					creditsRemaining={creditsRemaining}
				/>
				<ScrollArea className="flex-1">
					{isLoading && (
						<div className="text-muted-foreground flex items-center justify-center py-12 text-sm">
							Loading models...
						</div>
					)}
					{error && (
						<div className="flex items-center justify-center py-12 text-sm text-red-500">
							{error instanceof Error ? error.message : "Failed to load models"}
						</div>
					)}
					{!isLoading && !error && models.length === 0 && (
						<div className="text-muted-foreground flex flex-col items-center justify-center gap-2 py-12 text-sm">
							<Filter className="h-8 w-8 opacity-50" />
							<p>No models match your filters</p>
						</div>
					)}
					<div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
						{models.map((m) => (
							<ModelCard
								key={m.id}
								model={m}
								isSelected={effectiveSelected.has(m.id)}
								onToggle={() => toggleModel(m.id)}
							/>
						))}
					</div>
				</ScrollArea>
			</div>
		</div>
	);
}
