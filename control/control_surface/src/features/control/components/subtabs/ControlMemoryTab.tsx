"use client";

// AC8 — Memory Tab: layer health view (episodic / kg / vector).

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Brain, Loader2 } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface MemoryLayer {
	type: "episodic" | "kg" | "vector";
	health: "healthy" | "degraded" | "offline" | "unknown";
	itemCount: number;
	lastSyncAt: string | null;
}

interface MemoryData {
	layers: MemoryLayer[];
	degraded?: boolean;
	degraded_reasons?: string[];
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

	const layers = data?.layers ?? [];

	return (
		<div className="p-4 space-y-3">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Memory Layers</h2>
				{data?.degraded && (
					<span className="text-[10px] font-mono text-amber-500">
						degraded: {data.degraded_reasons?.join(", ")}
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
						</div>
					))}
				</div>
			)}
		</div>
	);
}
