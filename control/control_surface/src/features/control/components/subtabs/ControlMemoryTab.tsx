"use client";

// AC8 — Memory Tab: layer health view (episodic / kg / vector).

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Brain, Loader2 } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface MemoryLayer {
	type: "episodic" | "kg" | "vector";
	provider?: string;
	health: "healthy" | "degraded" | "offline" | "unknown";
	itemCount: number;
	lastSyncAt: string | null;
	consolidationPending?: number;
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
	route?: string;
	tokenCount?: number;
}

interface ActiveSession {
	sessionId?: string | null;
	threadId?: string | null;
	status?: string | null;
	provider?: string | null;
	model?: string | null;
	promptTokens?: number;
	completionTokens?: number;
	reasoningTokens?: number;
	cachedTokens?: number;
	totalTokens?: number;
	updatedAt?: string | null;
}

interface MemoryInspector {
	memoryProvider?: string;
	activeSession?: ActiveSession | null;
	sourceLayerCounts?: Record<string, number>;
	contextBlocks?: InspectorBlock[];
	degradationFlags?: string[];
	hasPersistedRunMetadata?: boolean;
}

interface MemoryData {
	layers: MemoryLayer[];
	ops?: { layers: MemoryLayer[]; degraded?: boolean; degradedReasons?: string[] };
	inspector?: MemoryInspector;
	degraded?: boolean;
	degradedReasons?: string[];
}

const LAYER_LABELS: Record<MemoryLayer["type"], string> = {
	episodic: "Episodic Memory",
	kg: "Knowledge Graph",
	vector: "Vector Store",
};

const HEALTH_STYLES: Record<MemoryLayer["health"], string> = {
	healthy: "bg-emerald-500/20 text-emerald-400",
	degraded: "bg-amber-500/20 text-amber-400",
	offline: "bg-red-500/20 text-red-400",
	unknown: "bg-muted text-muted-foreground",
};

export function ControlMemoryTab() {
	const { data, isLoading, error } = useQuery<MemoryData>({
		queryKey: ["control", "memory"],
		queryFn: async () => {
			const res = await fetch("/api/control/memory", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<MemoryData>;
		},
		staleTime: 15_000,
		refetchInterval: 30_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading memory layers…
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

	const layers = data?.ops?.layers ?? data?.layers ?? [];
	const inspector = data?.inspector;
	const degradedReasons = data?.degradedReasons ?? data?.ops?.degradedReasons ?? [];
	const activeSession = inspector?.activeSession;
	const sourceLayerCounts = Object.entries(inspector?.sourceLayerCounts ?? {}).filter(
		([, count]) => count > 0,
	);
	const contextBlocks = inspector?.contextBlocks ?? [];
	const degradationFlags = inspector?.degradationFlags ?? [];

	return (
		<div className="p-4 space-y-4">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Memory Layers</h2>
				{data?.degraded && degradedReasons.length > 0 && (
					<span className="text-[10px] font-mono text-amber-500">
						degraded: {degradedReasons.join(", ")}
					</span>
				)}
			</div>

			{layers.length === 0 ? (
				<div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
					<Brain className="h-8 w-8 opacity-20" />
					<span className="text-sm">No memory layer data</span>
				</div>
			) : (
				<div className="grid gap-2 sm:grid-cols-3">
					{layers.map((layer) => (
						<div
							key={layer.type}
							className="rounded-lg border border-border bg-card p-3 flex flex-col gap-2"
						>
							<div className="flex items-center justify-between">
								<span className="text-xs font-semibold text-foreground">
									{LAYER_LABELS[layer.type]}
								</span>
								<span
									className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${HEALTH_STYLES[layer.health]}`}
								>
									{layer.health}
								</span>
							</div>
							<p className="text-2xl font-mono font-bold text-foreground">
								{layer.itemCount.toLocaleString()}
							</p>
							<p className="text-[10px] text-muted-foreground/60">
								{layer.lastSyncAt
									? `synced ${new Date(layer.lastSyncAt).toLocaleTimeString()}`
									: "never synced"}
							</p>
							{layer.provider && (
								<p className="text-[10px] text-muted-foreground/50">{layer.provider}</p>
							)}
						</div>
					))}
				</div>
			)}

			{activeSession && (
				<div className="rounded-lg border border-border bg-card p-3 space-y-3">
					<div className="flex items-center justify-between gap-2">
						<div>
							<p className="text-xs font-semibold text-foreground">Latest Runtime</p>
							<p className="text-[10px] text-muted-foreground/60">
								{activeSession.model || "model unknown"} via{" "}
								{activeSession.provider || inspector?.memoryProvider || "unknown"}
							</p>
						</div>
						{activeSession.status && (
							<span className="rounded bg-muted px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground">
								{activeSession.status}
							</span>
						)}
					</div>
					<div className="grid gap-2 sm:grid-cols-4">
						{[
							{ label: "Prompt", value: activeSession.promptTokens ?? 0 },
							{ label: "Completion", value: activeSession.completionTokens ?? 0 },
							{ label: "Cached", value: activeSession.cachedTokens ?? 0 },
							{ label: "Total", value: activeSession.totalTokens ?? 0 },
						].map(({ label, value }) => (
							<div key={label} className="rounded border border-border/60 bg-muted/20 p-2">
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/60">
									{label}
								</p>
								<p className="font-mono text-sm text-foreground">{value.toLocaleString()}</p>
							</div>
						))}
					</div>
					{activeSession.updatedAt && (
						<p className="text-[10px] text-muted-foreground/60">
							Updated {new Date(activeSession.updatedAt).toLocaleString()}
						</p>
					)}
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
				<div className="space-y-2">
					<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
						Layer Contribution
					</p>
					<div className="grid gap-2 sm:grid-cols-4">
						{sourceLayerCounts.map(([layer, count]) => (
							<div key={layer} className="rounded border border-border bg-card px-3 py-2">
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/60">
									{layer.replaceAll("_", " ")}
								</p>
								<p className="font-mono text-lg text-foreground">{count}</p>
							</div>
						))}
					</div>
				</div>
			)}

			{contextBlocks.length > 0 && (
				<div className="space-y-2">
					<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
						Context Blocks
					</p>
					<div className="space-y-2">
						{contextBlocks.map((block) => (
							<div key={block.id} className="rounded border border-border bg-card p-3 space-y-1.5">
								<div className="flex items-center justify-between gap-2">
									<p className="text-xs font-semibold text-foreground">{block.title}</p>
									<span className="text-[9px] font-mono text-muted-foreground/50">
										{block.tokenCount ?? 0} tok
									</span>
								</div>
								<div className="flex flex-wrap gap-1.5 text-[9px] text-muted-foreground/60">
									<span>{block.sourceLayer}</span>
									<span>{block.sourceType}</span>
									<span>{block.artifactType}</span>
									<span>{block.groundingStatus}</span>
									{block.route && <span>{block.route}</span>}
								</div>
								<p className="text-xs text-foreground/90">{block.preview || "No preview available."}</p>
								{block.provenanceRef && (
									<p className="text-[10px] font-mono text-muted-foreground/50">
										{block.provenanceRef}
									</p>
								)}
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
}
