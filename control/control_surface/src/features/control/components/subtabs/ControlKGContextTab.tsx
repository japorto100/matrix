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

interface InspectorBlock {
	id: string;
	title: string;
	preview: string;
	sourceLayer: string;
	sourceType: string;
	artifactType: string;
	groundingStatus: string;
	provenanceRef: string;
	status: string;
}

interface KGInspector {
	worldClaims?: InspectorBlock[];
	contextBlocks?: InspectorBlock[];
	degradationFlags?: string[];
	sourceLayerCounts?: Record<string, number>;
	activeSession?: {
		model?: string | null;
		provider?: string | null;
		promptTokens?: number;
		completionTokens?: number;
		cachedTokens?: number;
	};
}

interface KGContextData {
	stats: KGStats;
	recentNodes: KGNode[];
	inspector?: KGInspector;
	degraded?: boolean;
	degradedReasons?: string[];
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
	const inspector = data?.inspector;
	const worldClaims = inspector?.worldClaims ?? [];
	const degradationFlags = inspector?.degradationFlags ?? [];
	const sourceLayerCounts = Object.entries(inspector?.sourceLayerCounts ?? {}).filter(
		([, count]) => count > 0,
	);

	return (
		<div className="p-4 space-y-4">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Knowledge Graph</h2>
				<div className="flex items-center gap-2">
					{data?.degraded && (
						<span className="text-[10px] font-mono text-amber-500">
							{data.degradedReasons?.join(", ")}
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

			{inspector?.activeSession && (
				<div className="rounded-lg border border-border bg-card p-3 space-y-2">
					<p className="text-xs font-semibold text-foreground">Latest Runtime Context</p>
					<p className="text-[10px] text-muted-foreground/60">
						{inspector.activeSession.model || "model unknown"} via{" "}
						{inspector.activeSession.provider || "unknown"}
					</p>
					<div className="grid grid-cols-3 gap-2">
						{[
							{ label: "Prompt", value: inspector.activeSession.promptTokens ?? 0 },
							{ label: "Completion", value: inspector.activeSession.completionTokens ?? 0 },
							{ label: "Cached", value: inspector.activeSession.cachedTokens ?? 0 },
						].map(({ label, value }) => (
							<div key={label} className="rounded border border-border/60 bg-muted/20 p-2">
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/60">
									{label}
								</p>
								<p className="font-mono text-sm text-foreground">{value.toLocaleString()}</p>
							</div>
						))}
					</div>
				</div>
			)}

			{degradationFlags.length > 0 && (
				<div className="flex flex-wrap gap-2">
					{degradationFlags.map((flag) => (
						<span
							key={flag}
							className="rounded bg-amber-500/15 px-2 py-1 text-[10px] font-mono text-amber-400"
						>
							{flag}
						</span>
					))}
				</div>
			)}

			{sourceLayerCounts.length > 0 && (
				<div className="grid grid-cols-2 gap-2">
					{sourceLayerCounts.map(([layer, count]) => (
						<div key={layer} className="rounded border border-border bg-card px-3 py-2">
							<p className="text-[9px] uppercase tracking-wider text-muted-foreground/60">
								{layer.replaceAll("_", " ")}
							</p>
							<p className="font-mono text-lg text-foreground">{count}</p>
						</div>
					))}
				</div>
			)}

			{worldClaims.length > 0 && (
				<div className="space-y-2">
					<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
						World Claims
					</p>
					<div className="space-y-2">
						{worldClaims.map((claim) => (
							<div key={claim.id} className="rounded border border-border bg-card p-3 space-y-1.5">
								<div className="flex items-center justify-between gap-2">
									<p className="text-xs font-semibold text-foreground">{claim.title}</p>
									<span className="text-[9px] font-mono text-muted-foreground/50">
										{claim.status}
									</span>
								</div>
								<div className="flex flex-wrap gap-1.5 text-[9px] text-muted-foreground/60">
									<span>{claim.sourceLayer}</span>
									<span>{claim.sourceType}</span>
									<span>{claim.artifactType}</span>
									<span>{claim.groundingStatus}</span>
								</div>
								<p className="text-xs text-foreground/90">
									{claim.preview || "No world claim preview available."}
								</p>
								{claim.provenanceRef && (
									<p className="text-[10px] font-mono text-muted-foreground/50">
										{claim.provenanceRef}
									</p>
								)}
							</div>
						))}
					</div>
				</div>
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
