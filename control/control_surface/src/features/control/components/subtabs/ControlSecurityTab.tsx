"use client";

// Control Security Tab — Phase 22b (AC9, read-only)
// Security posture, blocked/approved events, trust indicators.

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle, Loader2, ShieldAlert } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface SecurityEvent {
	id: string;
	type: "blocked" | "approved" | "rate_limit" | "injection_detected";
	description: string;
	actorId?: string;
	ts: string;
}

interface SecurityData {
	postureScore: number; // 0-100
	postureTrend: "improving" | "stable" | "declining";
	recentEvents: SecurityEvent[];
	totalBlocked: number;
	totalApproved: number;
	lastUpdated: string;
}

function PostureMeter({ score }: { score: number }) {
	const color = score >= 80 ? "text-emerald-500" : score >= 50 ? "text-amber-500" : "text-red-500";
	const bgColor = score >= 80 ? "bg-emerald-500" : score >= 50 ? "bg-amber-500" : "bg-red-500";
	return (
		<div className="flex items-center gap-3">
			<span className={`text-3xl font-bold tabular-nums ${color}`}>{score}</span>
			<div className="flex flex-col gap-1">
				<div className="h-2 w-32 rounded-full bg-muted overflow-hidden">
					<div
						className={`h-full rounded-full ${bgColor} transition-all`}
						style={{ width: `${score}%` }}
					/>
				</div>
				<span className="text-[10px] text-muted-foreground">posture score / 100</span>
			</div>
		</div>
	);
}

function EventTypeBadge({ type }: { type: SecurityEvent["type"] }) {
	const map: Record<SecurityEvent["type"], { label: string; cls: string }> = {
		blocked: { label: "blocked", cls: "bg-red-500/20 text-red-400" },
		approved: { label: "approved", cls: "bg-emerald-500/20 text-emerald-400" },
		rate_limit: { label: "rate-limit", cls: "bg-amber-500/20 text-amber-400" },
		injection_detected: { label: "injection", cls: "bg-red-600/30 text-red-300" },
	};
	const { label, cls } = map[type] ?? map.blocked;
	return (
		<span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${cls}`}>
			{label}
		</span>
	);
}

export function ControlSecurityTab() {
	const { data, isLoading, error } = useQuery<SecurityData>({
		queryKey: ["control", "security"],
		queryFn: async () => {
			const res = await fetch("/api/control/security", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<SecurityData>;
		},
		staleTime: 15_000,
		refetchInterval: 30_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading security…
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

	if (!data) return null;

	return (
		<div className="p-4 space-y-4">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Security Posture</h2>
				<span
					className={`text-[10px] font-medium ${
						data.postureTrend === "improving"
							? "text-emerald-500"
							: data.postureTrend === "declining"
								? "text-red-500"
								: "text-muted-foreground"
					}`}
				>
					{data.postureTrend}
				</span>
			</div>

			<PostureMeter score={data.postureScore} />

			<div className="grid grid-cols-2 gap-3">
				<div className="rounded-lg border border-border bg-card px-4 py-3 flex flex-col gap-1">
					<div className="flex items-center gap-1.5">
						<CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
						<span className="text-xs text-muted-foreground font-medium">Approved</span>
					</div>
					<span className="text-xl font-bold text-foreground">{data.totalApproved}</span>
				</div>
				<div className="rounded-lg border border-border bg-card px-4 py-3 flex flex-col gap-1">
					<div className="flex items-center gap-1.5">
						<ShieldAlert className="h-3.5 w-3.5 text-red-500" />
						<span className="text-xs text-muted-foreground font-medium">Blocked</span>
					</div>
					<span className="text-xl font-bold text-foreground">{data.totalBlocked}</span>
				</div>
			</div>

			<div className="space-y-2">
				<h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
					Recent Events
				</h3>
				{data.recentEvents.length === 0 ? (
					<p className="text-sm text-muted-foreground py-4 text-center">No recent events</p>
				) : (
					data.recentEvents.map((ev) => (
						<div
							key={ev.id}
							className="rounded border border-border bg-card/50 px-3 py-2 flex items-center gap-2"
						>
							<EventTypeBadge type={ev.type} />
							<span className="flex-1 text-xs text-foreground truncate">{ev.description}</span>
							{ev.actorId && (
								<span className="text-[10px] font-mono text-muted-foreground/60 truncate max-w-[80px]">
									{ev.actorId}
								</span>
							)}
							<span className="text-[10px] text-muted-foreground/60 shrink-0">
								{new Date(ev.ts).toLocaleTimeString()}
							</span>
						</div>
					))
				)}
			</div>

			<p className="text-[10px] text-muted-foreground/60">Updated: {data.lastUpdated}</p>
		</div>
	);
}
