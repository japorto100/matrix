"use client";

// MemoryHealthCards — 3 cards showing health of episodic / kg / vector layers
// Pattern adapted from D:/matrix/control/control_surface/src/features/control/components/subtabs/ControlMemoryTab.tsx
// Visual style inspired by _ref/supermemory/apps/web/components/settings/account.tsx (SectionTitle + Card)

import { Brain, Database, Layers, Loader2, Network } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMemoryHealth } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockMemoryOverview } from "../mock-data";
import type { MemoryLayer } from "../types";

const HEALTH_VARIANT: Record<MemoryLayer["health"], { label: string; className: string }> = {
	ok: {
		label: "Healthy",
		className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
	},
	degraded: {
		label: "Degraded",
		className: "bg-amber-500/15 text-amber-400 border-amber-500/30",
	},
	error: {
		label: "Error",
		className: "bg-red-500/15 text-red-400 border-red-500/30",
	},
};

const LAYER_META: Record<
	MemoryLayer["type"],
	{ icon: typeof Brain; title: string; description: string }
> = {
	episodic: {
		icon: Brain,
		title: "Episodic",
		description: "Per-session memory of agent interactions",
	},
	kg: {
		icon: Network,
		title: "Knowledge Graph",
		description: "Stratagems, regimes, channels, asset relationships",
	},
	vector: {
		icon: Database,
		title: "Vector Store",
		description: "Semantic embeddings for similarity search",
	},
};

function formatRelativeTime(iso: string | null): string {
	if (!iso) return "never";
	const ms = Date.now() - Date.parse(iso);
	if (ms < 60_000) return "just now";
	if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
	if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
	return `${Math.floor(ms / 86_400_000)}d ago`;
}

export function MemoryHealthCards() {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useMemoryHealth();
	// If backend returns layers[] keep using that; otherwise fall back to mock overview shape
	const data = (query.data as typeof mockMemoryOverview | undefined) ?? mockMemoryOverview;
	const isLoading = query.isLoading && !query.data;

	if (isLoading) {
		return (
			<div className="flex items-center gap-2 text-muted-foreground text-sm py-8 px-6">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading memory layers…
			</div>
		);
	}

	return (
		<section className="px-6 py-5">
			<div className="mb-4 flex items-center gap-2">
				<Layers className="h-4 w-4 text-muted-foreground" />
				<h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
					Memory Layers
				</h2>
			</div>
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				{data.layers.map((layer) => {
					const meta = LAYER_META[layer.type];
					const Icon = meta.icon;
					const variant = HEALTH_VARIANT[layer.health];
					return (
						<Card
							key={layer.type}
							className="bg-card border-border/50 hover:border-border transition-colors"
						>
							<CardHeader className="pb-3">
								<div className="flex items-start justify-between gap-2">
									<div className="flex items-center gap-2">
										<div className="rounded-md bg-accent/40 p-1.5">
											<Icon className="h-4 w-4 text-foreground" />
										</div>
										<div>
											<CardTitle className="text-sm font-semibold leading-tight">
												{meta.title}
											</CardTitle>
											<p className="text-[10px] font-mono text-muted-foreground/80 mt-0.5">
												{layer.provider}
											</p>
										</div>
									</div>
									<Badge
										variant="outline"
										className={cn("h-5 text-[10px] font-medium", variant.className)}
									>
										{variant.label}
									</Badge>
								</div>
							</CardHeader>
							<CardContent className="pt-0 space-y-3">
								<p className="text-[11px] text-muted-foreground leading-relaxed">
									{meta.description}
								</p>
								<div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/30">
									<div>
										<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
											Items
										</p>
										<p className="text-lg font-bold tabular-nums">
											{layer.item_count.toLocaleString()}
										</p>
									</div>
									<div>
										<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
											Last sync
										</p>
										<p className="text-xs font-medium text-foreground/90 mt-1">
											{formatRelativeTime(layer.last_sync_at)}
										</p>
									</div>
								</div>
								{layer.consolidation_pending > 0 && (
									<div className="flex items-center gap-1.5 text-[10px] text-amber-400 font-medium">
										<span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
										{layer.consolidation_pending} consolidation
										{layer.consolidation_pending === 1 ? "" : "s"} pending
									</div>
								)}
							</CardContent>
						</Card>
					);
				})}
			</div>
		</section>
	);
}
