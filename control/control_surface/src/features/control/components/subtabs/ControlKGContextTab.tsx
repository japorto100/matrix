"use client";

// AC8 — KG / Context Tab: knowledge graph stats + recent nodes.

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, Network } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface KGStats {
	nodeCount: number;
	edgeCount: number;
	health: "healthy" | "degraded" | "offline" | "unknown";
	lastSyncAt: string | null;
}

interface KGNode {
	id: string;
	label: string;
	type: string;
	connectedEdges: number;
}

interface KGContextData {
	stats: KGStats;
	recentNodes: KGNode[];
	degraded?: boolean;
	degraded_reasons?: string[];
}

const HEALTH_STYLES: Record<KGStats["health"], string> = {
	healthy: "bg-emerald-500/20 text-emerald-400",
	degraded: "bg-amber-500/20 text-amber-400",
	offline: "bg-red-500/20 text-red-400",
	unknown: "bg-muted text-muted-foreground",
};

export function ControlKGContextTab() {
	const { data, isLoading, error } = useQuery<KGContextData>({
		queryKey: ["control", "kg-context"],
		queryFn: async () => {
			const res = await fetch("/api/control/kg-context", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<KGContextData>;
		},
		staleTime: 20_000,
		refetchInterval: 30_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading graph…
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-destructive text-sm">
				<AlertCircle className="h-4 w-4" />
				{getErrorMessage(error)}
			</div>
		);
	}

	const stats = data?.stats ?? { nodeCount: 0, edgeCount: 0, health: "unknown", lastSyncAt: null };
	const nodes = data?.recentNodes ?? [];

	return (
		<div className="p-4 space-y-4">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Knowledge Graph</h2>
				<div className="flex items-center gap-2">
					{data?.degraded && (
						<span className="text-[10px] font-mono text-amber-500">
							{data.degraded_reasons?.join(", ")}
						</span>
					)}
					<span
						className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${HEALTH_STYLES[stats.health]}`}
					>
						{stats.health}
					</span>
				</div>
			</div>

			{/* Stats row */}
			<div className="grid grid-cols-2 gap-3">
				{[
					{ label: "Nodes", value: stats.nodeCount },
					{ label: "Edges", value: stats.edgeCount },
				].map(({ label, value }) => (
					<div key={label} className="rounded-lg border border-border bg-card p-3">
						<p className="text-[10px] text-muted-foreground/60 uppercase tracking-widest mb-1">
							{label}
						</p>
						<p className="text-2xl font-mono font-bold text-foreground">{value.toLocaleString()}</p>
					</div>
				))}
			</div>

			{stats.lastSyncAt && (
				<p className="text-[10px] text-muted-foreground/60">
					Last sync: {new Date(stats.lastSyncAt).toLocaleString()}
				</p>
			)}

			{/* Recent nodes */}
			{nodes.length > 0 && (
				<div className="space-y-2">
					<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
						Recent Nodes
					</p>
					{nodes.map((n) => (
						<div
							key={n.id}
							className="flex items-center gap-2 rounded border border-border bg-card px-3 py-2"
						>
							<Network className="h-3 w-3 text-muted-foreground shrink-0" />
							<span className="text-xs text-foreground flex-1 truncate">{n.label}</span>
							<span className="text-[10px] font-mono text-muted-foreground/60">{n.type}</span>
							<span className="text-[10px] text-muted-foreground/40">{n.connectedEdges}e</span>
						</div>
					))}
				</div>
			)}

			{nodes.length === 0 && !data?.degraded && (
				<div className="flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
					<Network className="h-8 w-8 opacity-20" />
					<span className="text-sm">No nodes indexed</span>
				</div>
			)}
		</div>
	);
}
