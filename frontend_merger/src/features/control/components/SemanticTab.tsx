"use client";

import { AlertTriangle, BookOpenText, DatabaseZap, GitBranch, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSemanticCatalog, useSemanticMetricPlan } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockSemanticCatalog } from "../mock-data";
import type { SemanticCatalogResponse, SemanticMetric, SemanticTerm } from "../types";

const STATUS_COLOR: Record<string, string> = {
	active: "border-emerald-500/40 text-emerald-400",
	draft: "border-amber-500/40 text-amber-400",
	deprecated: "border-rose-500/40 text-rose-400",
};

const SCOPE_COLOR: Record<string, string> = {
	public: "border-emerald-500/40 text-emerald-400",
	tenant: "border-sky-500/40 text-sky-400",
	user: "border-amber-500/40 text-amber-400",
	admin: "border-rose-500/40 text-rose-400",
};

function containsTerm(term: SemanticTerm, query: string): boolean {
	return [
		term.term_id,
		term.name,
		term.description,
		term.owner,
		...term.aliases,
		...term.source_refs,
		...term.kg_claim_types,
		...term.rag_source_classes,
	]
		.join(" ")
		.toLowerCase()
		.includes(query);
}

function containsMetric(metric: SemanticMetric, query: string): boolean {
	return [
		metric.metric_id,
		metric.name,
		metric.measure,
		metric.owner,
		metric.source_table,
		...metric.aliases,
		...metric.dimensions,
		...metric.filters,
		...metric.source_refs,
	]
		.join(" ")
		.toLowerCase()
		.includes(query);
}

export function SemanticTab() {
	const [filter, setFilter] = useState("");
	const [selectedMetricId, setSelectedMetricId] = useState("agent_tool_success_rate");
	const catalogQuery = useSemanticCatalog();
	const data = (catalogQuery.data as SemanticCatalogResponse | undefined) ?? mockSemanticCatalog;
	const planQuery = useSemanticMetricPlan(selectedMetricId, "local");
	const selectedMetric = data.catalog.metrics.find(
		(metric) => metric.metric_id === selectedMetricId,
	);
	const metricPlan = planQuery.data;

	const normalizedFilter = filter.trim().toLowerCase();
	const terms = useMemo(() => {
		if (!normalizedFilter) return data.catalog.terms;
		return data.catalog.terms.filter((term) => containsTerm(term, normalizedFilter));
	}, [data.catalog.terms, normalizedFilter]);

	const metrics = useMemo(() => {
		if (!normalizedFilter) return data.catalog.metrics;
		return data.catalog.metrics.filter((metric) => containsMetric(metric, normalizedFilter));
	}, [data.catalog.metrics, normalizedFilter]);

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-base font-semibold">Semantic Catalog</h2>
					<p className="text-xs text-muted-foreground">
						v{data.catalog.version} · {data.catalog.terms.length} terms ·{" "}
						{data.catalog.metrics.length} metrics
					</p>
				</div>
				<Input
					placeholder="Filter terms, metrics, aliases..."
					value={filter}
					onChange={(event) => setFilter(event.target.value)}
					className="h-8 w-full text-xs sm:w-72"
				/>
			</header>

			<div className="grid grid-cols-1 gap-3 md:grid-cols-4">
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Validation</span>
						<ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{data.validation.passed ? "Passed" : "Blocked"}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Alias Collisions</span>
						<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{Object.keys(data.validation.alias_collisions).length}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">KG Terms</span>
						<GitBranch className="h-3.5 w-3.5 text-sky-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{data.catalog.terms.filter((term) => term.kg_claim_types.length > 0).length}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Tenant Metrics</span>
						<DatabaseZap className="h-3.5 w-3.5 text-purple-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{data.catalog.metrics.filter((metric) => metric.permission_scope === "tenant").length}
					</div>
				</div>
			</div>

			<div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
				<div className="space-y-4">
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="flex items-center gap-1.5 text-sm">
								<BookOpenText className="h-3.5 w-3.5" />
								Terms
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							{terms.map((term) => (
								<div key={term.term_id} className="rounded border border-border/50 p-3">
									<div className="flex flex-wrap items-center justify-between gap-2">
										<div>
											<p className="text-sm font-medium">{term.name}</p>
											<p className="font-mono text-[10px] text-muted-foreground">{term.term_id}</p>
										</div>
										<Badge
											variant="outline"
											className={cn("h-5 px-1.5 text-[10px]", STATUS_COLOR[term.status])}
										>
											{term.status}
										</Badge>
									</div>
									<p className="mt-2 text-xs leading-relaxed text-muted-foreground">
										{term.description}
									</p>
									<div className="mt-2 flex flex-wrap gap-1">
										{[...term.aliases, ...term.source_refs].map((value) => (
											<Badge
												key={`${term.term_id}-${value}`}
												variant="secondary"
												className="h-4 px-1.5 text-[9px]"
											>
												{value}
											</Badge>
										))}
									</div>
								</div>
							))}
							{terms.length === 0 && (
								<p className="text-center text-xs text-muted-foreground">No terms match filters</p>
							)}
						</CardContent>
					</Card>

					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="flex items-center gap-1.5 text-sm">
								<DatabaseZap className="h-3.5 w-3.5" />
								Metrics
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							{metrics.map((metric) => (
								<button
									key={metric.metric_id}
									type="button"
									onClick={() => setSelectedMetricId(metric.metric_id)}
									className={cn(
										"w-full rounded border border-border/50 p-3 text-left transition-colors hover:bg-card/40",
										selectedMetricId === metric.metric_id && "border-primary/50 bg-primary/5",
									)}
								>
									<div className="flex flex-wrap items-center justify-between gap-2">
										<div>
											<p className="text-sm font-medium">{metric.name}</p>
											<p className="font-mono text-[10px] text-muted-foreground">
												{metric.metric_id}
											</p>
										</div>
										<div className="flex flex-wrap gap-1">
											<Badge
												variant="outline"
												className={cn("h-5 px-1.5 text-[10px]", STATUS_COLOR[metric.status])}
											>
												{metric.status}
											</Badge>
											<Badge
												variant="outline"
												className={cn(
													"h-5 px-1.5 text-[10px]",
													SCOPE_COLOR[metric.permission_scope],
												)}
											>
												{metric.permission_scope}
											</Badge>
										</div>
									</div>
									<p className="mt-2 font-mono text-[11px] text-muted-foreground">
										{metric.measure}
									</p>
									<div className="mt-2 flex flex-wrap gap-1">
										{[metric.source_table, ...metric.source_refs].map((value) => (
											<Badge
												key={`${metric.metric_id}-${value}`}
												variant="secondary"
												className="h-4 px-1.5 text-[9px]"
											>
												{value}
											</Badge>
										))}
									</div>
								</button>
							))}
							{metrics.length === 0 && (
								<p className="text-center text-xs text-muted-foreground">
									No metrics match filters
								</p>
							)}
						</CardContent>
					</Card>
				</div>

				<Card className="h-fit">
					<CardHeader className="pb-3">
						<CardTitle className="text-sm">Metric Plan</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3">
						{selectedMetric ? (
							<>
								<div>
									<p className="text-sm font-medium">{selectedMetric.name}</p>
									<p className="font-mono text-[10px] text-muted-foreground">
										{selectedMetric.metric_id}
									</p>
								</div>
								<div className="grid grid-cols-2 gap-2 text-xs">
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Grain</p>
										<p className="font-mono">{selectedMetric.grain}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Freshness</p>
										<p className="font-mono">{selectedMetric.freshness_sla || "—"}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Time Field</p>
										<p className="font-mono">{selectedMetric.time_field || "—"}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Raw SQL</p>
										<p className="font-mono">
											{metricPlan?.raw_sql_allowed === true ? "allowed" : "disabled"}
										</p>
									</div>
								</div>
								<div>
									<p className="mb-1 text-[10px] uppercase text-muted-foreground/70">Dimensions</p>
									<div className="flex flex-wrap gap-1">
										{selectedMetric.dimensions.map((dimension) => (
											<Badge key={dimension} variant="secondary" className="h-4 px-1.5 text-[9px]">
												{dimension}
											</Badge>
										))}
									</div>
								</div>
								<div>
									<p className="mb-1 text-[10px] uppercase text-muted-foreground/70">Filters</p>
									<div className="flex flex-wrap gap-1">
										{selectedMetric.filters.map((filterValue) => (
											<Badge
												key={filterValue}
												variant="secondary"
												className="h-4 px-1.5 text-[9px]"
											>
												{filterValue}
											</Badge>
										))}
									</div>
								</div>
								{metricPlan && !metricPlan.allowed && (
									<div className="rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-300">
										Plan denied: {metricPlan.reason ?? "unknown"}
									</div>
								)}
							</>
						) : (
							<p className="text-xs text-muted-foreground">Select a metric to inspect its plan.</p>
						)}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
