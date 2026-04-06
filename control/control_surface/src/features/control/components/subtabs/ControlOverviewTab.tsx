"use client";

// Control Overview — Phase 22b (AC5, read-only)
// Runtime health summary: SSE, Memory/KG, Security posture, Tool errors.

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle, Loader2, MinusCircle } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface OverviewData {
	runtimeHealth: "live" | "degraded" | "unknown";
	memoryHealth: "ok" | "degraded" | "unknown";
	securityPosture: "ok" | "warn" | "alert" | "unknown";
	activeSessions: number;
	recentToolErrors: number;
	lastUpdated: string;
}

function StatusIcon({ status }: { status: string }) {
	if (status === "live" || status === "ok") {
		return <CheckCircle className="h-4 w-4 text-emerald-500" />;
	}
	if (status === "degraded" || status === "warn") {
		return <AlertCircle className="h-4 w-4 text-amber-500" />;
	}
	if (status === "alert") {
		return <AlertCircle className="h-4 w-4 text-red-500" />;
	}
	return <MinusCircle className="h-4 w-4 text-muted-foreground" />;
}

function StatCard({
	label,
	value,
	status,
	sub,
}: {
	label: string;
	value: string | number;
	status?: string;
	sub?: string;
}) {
	return (
		<div className="rounded-lg border border-border bg-card px-4 py-3 flex flex-col gap-1">
			<div className="flex items-center justify-between">
				<span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
					{label}
				</span>
				{status && <StatusIcon status={status} />}
			</div>
			<span className="text-xl font-bold text-foreground">{value}</span>
			{sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
		</div>
	);
}

export function ControlOverviewTab() {
	const { data, isLoading, error } = useQuery<OverviewData>({
		queryKey: ["control", "overview"],
		queryFn: async () => {
			const res = await fetch("/api/control/overview", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<OverviewData>;
		},
		staleTime: 15_000,
		refetchInterval: 30_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading overview…
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
			<h2 className="text-sm font-semibold text-foreground">Runtime Overview</h2>
			<div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
				<StatCard label="Runtime" value={data.runtimeHealth} status={data.runtimeHealth} />
				<StatCard label="Memory / KG" value={data.memoryHealth} status={data.memoryHealth} />
				<StatCard label="Security" value={data.securityPosture} status={data.securityPosture} />
				<StatCard label="Active Sessions" value={data.activeSessions} />
				<StatCard label="Tool Errors (recent)" value={data.recentToolErrors} sub="last 1h" />
			</div>
			<p className="text-[10px] text-muted-foreground/60">Updated: {data.lastUpdated}</p>
		</div>
	);
}
