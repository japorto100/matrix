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
}: AgentChatEventRailProps) {
	const { label, dot } = STATUS_CONFIG[status];
	const showLatency = isStreaming && lastChunkMs !== undefined && lastChunkMs < 30_000;
	const showPressure = contextPressure !== undefined && contextPressure > 0.01;

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
