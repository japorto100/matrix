"use client";

// AC70: Stream status rail — live/degraded/reconnecting badge + latency + provider label
// AC64: Context-Window-Pressure-Bar — colored bar when context > 50% full

import { Activity } from "lucide-react";

export type RailStatus = "idle" | "live" | "degraded" | "reconnecting";

interface AgentChatEventRailProps {
	status: RailStatus;
	/** ms since last chunk — shown during active streaming */
	lastChunkMs?: number;
	/** Provider label from SSE metadata */
	provider?: string;
	isStreaming: boolean;
	/** AC64: context fill ratio 0-1 (promptTokens / model max context) */
	contextPressure?: number;
	degradationFlags?: string[];
	sourceLayerCounts?: Record<string, number>;
	requestTelemetry?: Array<Record<string, unknown>>;
	runtimeEvents?: Array<Record<string, unknown>>;
}

const STATUS_CONFIG: Record<RailStatus, { label: string; dot: string }> = {
	idle: { label: "idle", dot: "bg-muted-foreground/40" },
	live: { label: "live", dot: "bg-emerald-500 animate-pulse" },
	degraded: { label: "degraded", dot: "bg-orange-500" },
	reconnecting: { label: "reconnecting", dot: "bg-amber-500 animate-pulse" },
};

function pressureColor(p: number): string {
	if (p >= 0.9) return "bg-red-500";
	if (p >= 0.75) return "bg-orange-500";
	if (p >= 0.5) return "bg-amber-400";
	return "bg-emerald-500";
}

export function AgentChatEventRail({
	status,
	lastChunkMs,
	provider,
	isStreaming,
	contextPressure,
	degradationFlags = [],
	sourceLayerCounts = {},
	requestTelemetry = [],
	runtimeEvents = [],
}: AgentChatEventRailProps) {
	const { label, dot } = STATUS_CONFIG[status];
	const showLatency = isStreaming && lastChunkMs !== undefined && lastChunkMs < 30_000;
	const showPressure = contextPressure !== undefined && contextPressure > 0.01;
	const layerSummary = Object.entries(sourceLayerCounts)
		.filter(([, count]) => count > 0)
		.map(([layer, count]) => `${layer}:${count}`)
		.join(" ");
	const latestTelemetry = requestTelemetry.at(-1);
	const usage =
		latestTelemetry?.usage && typeof latestTelemetry.usage === "object"
			? (latestTelemetry.usage as Record<string, unknown>)
			: undefined;
	const cacheBreakReasons = Array.isArray(latestTelemetry?.cache_break_reasons)
		? latestTelemetry.cache_break_reasons.map((item) => String(item)).filter(Boolean)
		: [];
	const unknownFields = Array.isArray(usage?.unknown_fields)
		? usage.unknown_fields.map((item) => String(item)).filter(Boolean)
		: [];
	const runtimeSummary =
		runtimeEvents.length > 0
			? `${runtimeEvents.length} evt ${String(runtimeEvents.at(-1)?.status ?? "")}`.trim()
			: "";

	return (
		<div className="flex flex-col shrink-0">
			<div className="flex items-center gap-2 px-3 py-0.5 border-b border-border/30 bg-muted/20">
				<Activity className="h-2.5 w-2.5 text-muted-foreground/40" />
				<div className={`h-1.5 w-1.5 rounded-full ${dot}`} />
				<span className="text-[9px] text-muted-foreground/60 font-mono">{label}</span>
				{showLatency && (
					<span className="text-[9px] text-muted-foreground/40 font-mono">+{lastChunkMs}ms</span>
				)}
				{provider && (
					<span className="ml-auto text-[9px] text-muted-foreground/40 font-mono truncate">
						{provider}
					</span>
				)}
				{showPressure && !provider && (
					<span className="ml-auto text-[9px] text-muted-foreground/40 font-mono">
						{Math.round(contextPressure * 100)}% ctx
					</span>
				)}
			</div>
			{(degradationFlags.length > 0 || layerSummary) && (
				<div className="flex items-center gap-2 px-3 py-1 border-b border-border/20 bg-muted/10 text-[9px] font-mono text-muted-foreground/50 overflow-x-auto">
					{degradationFlags.map((flag) => (
						<span key={flag} className="text-amber-400">
							{flag}
						</span>
					))}
					{layerSummary && <span className="whitespace-nowrap">{layerSummary}</span>}
				</div>
			)}
			{(runtimeSummary || cacheBreakReasons.length > 0 || unknownFields.length > 0) && (
				<div className="flex items-center gap-2 px-3 py-1 border-b border-border/20 bg-background/70 text-[9px] font-mono text-muted-foreground/50 overflow-x-auto">
					{runtimeSummary && <span className="whitespace-nowrap">{runtimeSummary}</span>}
					{cacheBreakReasons.map((reason) => (
						<span key={`cache-${reason}`} className="text-sky-400 whitespace-nowrap">
							cache:{reason}
						</span>
					))}
					{unknownFields.length > 0 && (
						<span className="text-muted-foreground/40 whitespace-nowrap">
							unknown:{unknownFields.join(",")}
						</span>
					)}
				</div>
			)}
			{/* AC64: context pressure bar */}
			{showPressure && (
				<div className="h-0.5 w-full bg-border/20">
					<div
						className={`h-full transition-all duration-700 ${pressureColor(contextPressure)}`}
						style={{ width: `${Math.min(contextPressure * 100, 100)}%` }}
					/>
				</div>
			)}
		</div>
	);
}
