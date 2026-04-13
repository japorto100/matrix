"use client";

import {
	BrainCircuit,
	Check,
	Eye,
	Filter,
	Globe,
	Plus,
	Sparkles,
	SquareCode,
	Wrench,
	Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import type { ModelInfo } from "@/lib/queries/control";
import { useModelList } from "@/lib/queries/hooks";

function formatPrice(perMtok: number | null | undefined): string {
	if (perMtok == null) return "\u2014";
	if (perMtok === 0) return "Free";
	if (perMtok < 0.1) return `$${perMtok.toFixed(3)}/Mtok`;
	if (perMtok < 10) return `$${perMtok.toFixed(2)}/Mtok`;
	return `$${perMtok.toFixed(0)}/Mtok`;
}

function formatContext(ctx: number | undefined): string {
	if (!ctx) return "\u2014";
	if (ctx >= 1_000_000) return `${(ctx / 1_000_000).toFixed(1)}M`;
	if (ctx >= 1_000) return `${(ctx / 1_000).toFixed(0)}k`;
	return String(ctx);
}

function ModelCard({
	model,
	isSelected,
	onToggle,
}: {
	model: ModelInfo;
	isSelected: boolean;
	onToggle: () => void;
}) {
	return (
		<Card className="hover:border-primary/50 transition-colors">
			<CardHeader className="pb-2">
				<div className="flex items-start justify-between gap-2">
					<div className="min-w-0 flex-1">
						<CardTitle className="truncate text-sm font-medium">{model.name}</CardTitle>
						<p className="text-muted-foreground mt-0.5 truncate text-xs">{model.id}</p>
					</div>
					<div className="flex items-center gap-1 shrink-0">
						{model.is_free && (
							<Badge variant="secondary" className="bg-green-500/10 text-green-600 text-xs">
								Free
							</Badge>
						)}
						<Button
							variant={isSelected ? "default" : "outline"}
							size="sm"
							className="h-6 w-6 p-0"
							onClick={onToggle}
						>
							{isSelected ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
						</Button>
					</div>
				</div>
			</CardHeader>
			<CardContent className="pt-0">
				<div className="mb-2 flex flex-wrap gap-1.5">
					{model.supports_tools && (
						<Badge variant="outline" className="gap-1 text-xs">
							<Wrench className="h-3 w-3" /> Tools
						</Badge>
					)}
					{model.supports_vision && (
						<Badge variant="outline" className="gap-1 text-xs">
							<Eye className="h-3 w-3" /> Vision
						</Badge>
					)}
					{model.supports_reasoning && (
						<Badge variant="outline" className="gap-1 text-xs">
							<BrainCircuit className="h-3 w-3" /> Reasoning
						</Badge>
					)}
					{model.supports_structured_output && (
						<Badge variant="outline" className="gap-1 text-xs">
							<SquareCode className="h-3 w-3" /> JSON
						</Badge>
					)}
				</div>
				<div className="text-muted-foreground flex items-center justify-between text-xs">
					<span>{formatContext(model.context_length)} ctx</span>
					<span>{formatPrice(model.prompt_price_per_mtok)}</span>
				</div>
			</CardContent>
		</Card>
	);
}

const CONTEXT_OPTIONS = [
	{ label: "Any", value: "0" },
	{ label: "32k+", value: "32000" },
	{ label: "128k+", value: "128000" },
	{ label: "200k+", value: "200000" },
	{ label: "1M+", value: "1000000" },
];

const PRICE_OPTIONS = [
	{ label: "Any", value: "0" },
	{ label: "Free", value: "free" },
	{ label: "< $1/Mtok", value: "1" },
	{ label: "< $10/Mtok", value: "10" },
	{ label: "< $50/Mtok", value: "50" },
];

const OUTPUT_OPTIONS = [
	{ label: "Any", value: "0" },
	{ label: "4k+", value: "4000" },
	{ label: "16k+", value: "16000" },
	{ label: "64k+", value: "64000" },
	{ label: "128k+", value: "128000" },
];

const MODALITY_OPTIONS = [
	{ label: "Any", value: "" },
	{ label: "Text only", value: "text" },
	{ label: "Multimodal", value: "image" },
];

export function ModelExplorer() {
	const [search, setSearch] = useState("");
	const [freeOnly, setFreeOnly] = useState(false);
	const [toolsOnly, setToolsOnly] = useState(false);
	const [visionOnly, setVisionOnly] = useState(false);
	const [reasoningOnly, setReasoningOnly] = useState(false);
	const [structuredOnly, setStructuredOnly] = useState(false);
	const [providerFilter, setProviderFilter] = useState("");
	const [minContext, setMinContext] = useState("0");
	const [maxPrice, setMaxPrice] = useState("0");
	const [modalityFilter, setModalityFilter] = useState("");
	const [minOutput, setMinOutput] = useState("0");
	const [sortBy, setSortBy] = useState("name");
	const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());

	// Load existing selection on mount
	useEffect(() => {
		fetch("/api/control/user/llm/selected-models")
			.then((r) => r.json())
			.then((data: { selected_models?: string[] }) => {
				if (data.selected_models?.length) {
					setSelectedModels(new Set(data.selected_models));
				}
			})
			.catch(() => {});
	}, []);

	const filters = useMemo(() => {
		const f: Record<string, string> = { sort_by: sortBy, limit: "200" };
		if (search.trim()) f.search = search.trim();
		if (freeOnly || maxPrice === "free") f.free_only = "true";
		if (toolsOnly) f.supports_tools = "true";
		if (visionOnly) f.supports_vision = "true";
		if (reasoningOnly) f.supports_reasoning = "true";
		if (structuredOnly) f.supports_structured_output = "true";
		if (modalityFilter) f.modality = modalityFilter;
		if (providerFilter) f.provider = providerFilter;
		if (minContext !== "0") f.min_context = minContext;
		if (maxPrice !== "0" && maxPrice !== "free") f.max_price = maxPrice;
		if (minOutput !== "0") f.min_output = minOutput;
		return f;
	}, [
		search,
		freeOnly,
		toolsOnly,
		visionOnly,
		reasoningOnly,
		providerFilter,
		minContext,
		maxPrice,
		sortBy,
		structuredOnly,
		modalityFilter,
		minOutput,
	]);

	const { data, isLoading, error } = useModelList(filters);
	const models = data?.models ?? [];
	const facets = data?.facets;
	const total = data?.total ?? 0;

	function toggleModel(id: string) {
		setSelectedModels((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	}

	async function saveSelection() {
		try {
			const resp = await fetch("/api/control/user/llm/selected-models", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ models: Array.from(selectedModels) }),
			});
			if (!resp.ok) throw new Error(`${resp.status}`);
			toast.success(`${selectedModels.size} models saved for Agent Chat`);
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
				{selectedModels.size > 0 && (
					<Button size="sm" onClick={saveSelection}>
						Save {selectedModels.size} selected
					</Button>
				)}
			</div>
			<div className="flex flex-col gap-4 md:flex-row">
				<div className="w-full shrink-0 space-y-3 md:w-60">
					<Input
						placeholder="Search models..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="h-8 text-sm"
					/>
					<Separator />
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs font-medium uppercase">Capabilities</p>
						<label className="flex cursor-pointer items-center gap-2 text-sm">
							<Checkbox checked={freeOnly} onCheckedChange={(v) => setFreeOnly(!!v)} />
							<Zap className="h-3.5 w-3.5 text-green-500" /> Free only
							{facets && (
								<span className="text-muted-foreground ml-auto text-xs">{facets.free_count}</span>
							)}
						</label>
						<label className="flex cursor-pointer items-center gap-2 text-sm">
							<Checkbox checked={toolsOnly} onCheckedChange={(v) => setToolsOnly(!!v)} />
							<Wrench className="h-3.5 w-3.5" /> Tool calling
							{facets && (
								<span className="text-muted-foreground ml-auto text-xs">{facets.tools_count}</span>
							)}
						</label>
						<label className="flex cursor-pointer items-center gap-2 text-sm">
							<Checkbox checked={visionOnly} onCheckedChange={(v) => setVisionOnly(!!v)} />
							<Eye className="h-3.5 w-3.5" /> Vision
							{facets && (
								<span className="text-muted-foreground ml-auto text-xs">{facets.vision_count}</span>
							)}
						</label>
						<label className="flex cursor-pointer items-center gap-2 text-sm">
							<Checkbox checked={reasoningOnly} onCheckedChange={(v) => setReasoningOnly(!!v)} />
							<BrainCircuit className="h-3.5 w-3.5" /> Reasoning
							{facets && (
								<span className="text-muted-foreground ml-auto text-xs">
									{facets.reasoning_count}
								</span>
							)}
						</label>
						<label className="flex cursor-pointer items-center gap-2 text-sm">
							<Checkbox checked={structuredOnly} onCheckedChange={(v) => setStructuredOnly(!!v)} />
							<SquareCode className="h-3.5 w-3.5" /> Structured Output
						</label>
					</div>
					<Separator />
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs font-medium uppercase">Modality</p>
						<Select value={modalityFilter} onValueChange={setModalityFilter}>
							<SelectTrigger className="h-7 text-xs">
								<SelectValue placeholder="Any" />
							</SelectTrigger>
							<SelectContent>
								{MODALITY_OPTIONS.map((o) => (
									<SelectItem key={o.value || "any"} value={o.value}>
										{o.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs font-medium uppercase">Context Length</p>
						<Select value={minContext} onValueChange={setMinContext}>
							<SelectTrigger className="h-7 text-xs">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								{CONTEXT_OPTIONS.map((o) => (
									<SelectItem key={o.value} value={o.value}>
										{o.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs font-medium uppercase">Max Price</p>
						<Select value={maxPrice} onValueChange={setMaxPrice}>
							<SelectTrigger className="h-7 text-xs">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								{PRICE_OPTIONS.map((o) => (
									<SelectItem key={o.value} value={o.value}>
										{o.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs font-medium uppercase">Max Output</p>
						<Select value={minOutput} onValueChange={setMinOutput}>
							<SelectTrigger className="h-7 text-xs">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								{OUTPUT_OPTIONS.map((o) => (
									<SelectItem key={o.value} value={o.value}>
										{o.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
					<Separator />
					<div className="space-y-2">
						<p className="text-muted-foreground text-xs font-medium uppercase">Sort by</p>
						<div className="flex flex-wrap gap-1">
							{(["name", "price_asc", "price_desc", "context_desc"] as const).map((s) => (
								<Button
									key={s}
									variant={sortBy === s ? "default" : "outline"}
									size="sm"
									className="h-6 px-2 text-xs"
									onClick={() => setSortBy(s)}
								>
									{s === "name"
										? "Name"
										: s === "price_asc"
											? "$ Low"
											: s === "price_desc"
												? "$ High"
												: "Context"}
								</Button>
							))}
						</div>
					</div>
					{facets?.providers && facets.providers.length > 0 && (
						<>
							<Separator />
							<div className="space-y-1">
								<p className="text-muted-foreground text-xs font-medium uppercase">Provider</p>
								<button
									type="button"
									className={`text-muted-foreground flex w-full items-center justify-between text-xs hover:text-foreground ${!providerFilter ? "text-foreground font-medium" : ""}`}
									onClick={() => setProviderFilter("")}
								>
									<span>All</span>
									<span>{facets.total_all}</span>
								</button>
								{facets.providers.slice(0, 10).map((p) => (
									<button
										key={p.id}
										type="button"
										className={`text-muted-foreground flex w-full items-center justify-between text-xs hover:text-foreground ${providerFilter === p.id ? "text-foreground font-medium" : ""}`}
										onClick={() => setProviderFilter(providerFilter === p.id ? "" : p.id)}
									>
										<span className="flex items-center gap-1">
											<Globe className="h-3 w-3" />
											{p.id}
										</span>
										<span>{p.count}</span>
									</button>
								))}
							</div>
						</>
					)}
				</div>
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
								isSelected={selectedModels.has(m.id)}
								onToggle={() => toggleModel(m.id)}
							/>
						))}
					</div>
				</ScrollArea>
			</div>
		</div>
	);
}
