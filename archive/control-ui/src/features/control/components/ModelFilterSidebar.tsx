import { BrainCircuit, DollarSign, Eye, Globe, SquareCode, Wrench, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import type { ModelFacets } from "@/lib/queries/control";

export interface ModelFilters {
	search: string;
	freeOnly: boolean;
	toolsOnly: boolean;
	visionOnly: boolean;
	reasoningOnly: boolean;
	structuredOnly: boolean;
	affordableOnly: boolean;
	providerFilter: string;
	minContext: string;
	maxPrice: string;
	modalityFilter: string;
	minOutput: string;
	sortBy: string;
}

export type FilterKey = keyof ModelFilters;

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

export function ModelFilterSidebar({
	filters,
	onChange,
	facets,
	creditsRemaining,
}: {
	filters: ModelFilters;
	onChange: <K extends FilterKey>(key: K, value: ModelFilters[K]) => void;
	facets?: ModelFacets;
	creditsRemaining?: number | null;
}) {
	return (
		<div className="w-full shrink-0 space-y-3 md:w-60">
			<Input
				placeholder="Search models..."
				value={filters.search}
				onChange={(e) => onChange("search", e.target.value)}
				className="h-8 text-sm"
			/>
			<Separator />
			<div className="space-y-2">
				<p className="text-muted-foreground text-xs font-medium uppercase">Capabilities</p>
				<label className="flex cursor-pointer items-center gap-2 text-sm">
					<Checkbox checked={filters.freeOnly} onCheckedChange={(v) => onChange("freeOnly", !!v)} />
					<Zap className="h-3.5 w-3.5 text-green-500" /> Free only
					{facets && (
						<span className="text-muted-foreground ml-auto text-xs">{facets.free_count}</span>
					)}
				</label>
				<label className="flex cursor-pointer items-center gap-2 text-sm">
					<Checkbox
						checked={filters.toolsOnly}
						onCheckedChange={(v) => onChange("toolsOnly", !!v)}
					/>
					<Wrench className="h-3.5 w-3.5" /> Tool calling
					{facets && (
						<span className="text-muted-foreground ml-auto text-xs">{facets.tools_count}</span>
					)}
				</label>
				<label className="flex cursor-pointer items-center gap-2 text-sm">
					<Checkbox
						checked={filters.visionOnly}
						onCheckedChange={(v) => onChange("visionOnly", !!v)}
					/>
					<Eye className="h-3.5 w-3.5" /> Vision
					{facets && (
						<span className="text-muted-foreground ml-auto text-xs">{facets.vision_count}</span>
					)}
				</label>
				<label className="flex cursor-pointer items-center gap-2 text-sm">
					<Checkbox
						checked={filters.reasoningOnly}
						onCheckedChange={(v) => onChange("reasoningOnly", !!v)}
					/>
					<BrainCircuit className="h-3.5 w-3.5" /> Reasoning
					{facets && (
						<span className="text-muted-foreground ml-auto text-xs">{facets.reasoning_count}</span>
					)}
				</label>
				<label className="flex cursor-pointer items-center gap-2 text-sm">
					<Checkbox
						checked={filters.structuredOnly}
						onCheckedChange={(v) => onChange("structuredOnly", !!v)}
					/>
					<SquareCode className="h-3.5 w-3.5" /> Structured Output
				</label>
				{creditsRemaining != null && creditsRemaining > 0 && (
					<label className="flex cursor-pointer items-center gap-2 text-sm">
						<Checkbox
							checked={filters.affordableOnly}
							onCheckedChange={(v) => onChange("affordableOnly", !!v)}
						/>
						<DollarSign className="h-3.5 w-3.5 text-emerald-500" /> Affordable only
						<span className="text-muted-foreground ml-auto text-xs">
							${creditsRemaining.toFixed(2)}
						</span>
					</label>
				)}
			</div>
			<Separator />
			<div className="space-y-2">
				<p className="text-muted-foreground text-xs font-medium uppercase">Modality</p>
				<Select value={filters.modalityFilter} onValueChange={(v) => onChange("modalityFilter", v)}>
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
				<Select value={filters.minContext} onValueChange={(v) => onChange("minContext", v)}>
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
				<Select value={filters.maxPrice} onValueChange={(v) => onChange("maxPrice", v)}>
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
				<Select value={filters.minOutput} onValueChange={(v) => onChange("minOutput", v)}>
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
							variant={filters.sortBy === s ? "default" : "outline"}
							size="sm"
							className="h-6 px-2 text-xs"
							onClick={() => onChange("sortBy", s)}
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
							className={`text-muted-foreground flex w-full items-center justify-between text-xs hover:text-foreground ${!filters.providerFilter ? "text-foreground font-medium" : ""}`}
							onClick={() => onChange("providerFilter", "")}
						>
							<span>All</span>
							<span>{facets.total_all}</span>
						</button>
						{facets.providers.slice(0, 10).map((p) => (
							<button
								key={p.id}
								type="button"
								className={`text-muted-foreground flex w-full items-center justify-between text-xs hover:text-foreground ${filters.providerFilter === p.id ? "text-foreground font-medium" : ""}`}
								onClick={() =>
									onChange("providerFilter", filters.providerFilter === p.id ? "" : p.id)
								}
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
	);
}
