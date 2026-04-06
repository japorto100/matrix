"use client";

// AC10 — Agents Tab: agent registry observability (read-only v1).

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Bot, Circle, Loader2 } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface AgentEntry {
	id: string;
	name: string;
	role: string;
	status: "active" | "idle" | "error" | "offline";
	sessionCount: number;
	lastActiveAt: string | null;
}

interface AgentsData {
	agents: AgentEntry[];
	degraded?: boolean;
	degraded_reasons?: string[];
}

const STATUS_DOT: Record<AgentEntry["status"], string> = {
	active: "fill-emerald-500 text-emerald-500",
	idle: "fill-amber-500/50 text-amber-500/50",
	error: "fill-red-500 text-red-500",
	offline: "fill-muted-foreground/30 text-muted-foreground/30",
};

const STATUS_BADGE: Record<AgentEntry["status"], string> = {
	active: "bg-emerald-500/20 text-emerald-400",
	idle: "bg-amber-500/20 text-amber-400",
	error: "bg-red-500/20 text-red-400",
	offline: "bg-muted text-muted-foreground",
};

export function ControlAgentsTab() {
	const { data, isLoading, error } = useQuery<AgentsData>({
		queryKey: ["control", "agents"],
		queryFn: async () => {
			const res = await fetch("/api/control/agents", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<AgentsData>;
		},
		staleTime: 10_000,
		refetchInterval: 20_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading agents…
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

	const agents = data?.agents ?? [];

	return (
		<div className="p-4 space-y-3">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Agents</h2>
				<div className="flex items-center gap-2">
					{data?.degraded && (
						<span className="text-[10px] font-mono text-amber-500">
							{data.degraded_reasons?.join(", ")}
						</span>
					)}
					<span className="text-xs text-muted-foreground">{agents.length} registered</span>
				</div>
			</div>

			{agents.length === 0 ? (
				<div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
					<Bot className="h-8 w-8 opacity-20" />
					<span className="text-sm">No agents registered</span>
				</div>
			) : (
				<div className="space-y-1.5">
					{agents.map((a) => (
						<div
							key={a.id}
							className="rounded-lg border border-border bg-card px-3 py-2.5 flex items-center gap-3"
						>
							<Circle className={`h-2 w-2 shrink-0 ${STATUS_DOT[a.status]}`} />
							<Bot className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
							<div className="flex-1 min-w-0">
								<div className="flex items-center gap-2">
									<span className="text-xs font-semibold text-foreground truncate">{a.name}</span>
									<span
										className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${STATUS_BADGE[a.status]}`}
									>
										{a.status}
									</span>
								</div>
								<div className="flex items-center gap-3 mt-0.5">
									<span className="text-[10px] text-muted-foreground/60 font-mono">{a.role}</span>
									<span className="text-[10px] text-muted-foreground/40">
										{a.sessionCount} session{a.sessionCount !== 1 ? "s" : ""}
									</span>
								</div>
							</div>
							{a.lastActiveAt && (
								<span className="text-[10px] text-muted-foreground/40 shrink-0">
									{new Date(a.lastActiveAt).toLocaleTimeString()}
								</span>
							)}
						</div>
					))}
				</div>
			)}
		</div>
	);
}
