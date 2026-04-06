"use client";

// AC7 — Tool Events Tab: collapsible timeline of tool invocations.

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ChevronDown, ChevronRight, Loader2, Wrench } from "lucide-react";
import { useState } from "react";
import { getErrorMessage } from "@/lib/utils";

interface ToolEvent {
	id: string;
	toolName: string;
	agentId: string;
	status: "ok" | "error" | "running";
	durationMs: number;
	ts: string;
	inputSummary?: string;
	errorCode?: string;
}

interface ToolEventsData {
	events: ToolEvent[];
	total: number;
	degraded?: boolean;
	degraded_reasons?: string[];
}

function StatusBadge({ status }: { status: ToolEvent["status"] }) {
	const map = {
		ok: "bg-emerald-500/20 text-emerald-400",
		error: "bg-red-500/20 text-red-400",
		running: "bg-blue-500/20 text-blue-400",
	};
	return (
		<span
			className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${map[status]}`}
		>
			{status}
		</span>
	);
}

function ToolEventRow({ event }: { event: ToolEvent }) {
	const [open, setOpen] = useState(false);

	return (
		<div className="rounded-lg border border-border bg-card overflow-hidden">
			<button
				type="button"
				onClick={() => setOpen((v) => !v)}
				className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-accent/30 transition-colors"
			>
				{open ? (
					<ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
				) : (
					<ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
				)}
				<Wrench className="h-3 w-3 shrink-0 text-muted-foreground" />
				<span className="text-xs font-mono text-foreground flex-1 truncate">{event.toolName}</span>
				<StatusBadge status={event.status} />
				<span className="text-[10px] text-muted-foreground font-mono shrink-0">
					{event.durationMs}ms
				</span>
				<span className="text-[10px] text-muted-foreground/60 shrink-0">
					{new Date(event.ts).toLocaleTimeString()}
				</span>
			</button>
			{open && (
				<div className="px-3 pb-2.5 border-t border-border/50 space-y-1.5 pt-2">
					<p className="text-[10px] text-muted-foreground font-mono">
						agent: <span className="text-foreground/70">{event.agentId}</span>
					</p>
					{event.inputSummary && (
						<p className="text-[10px] text-muted-foreground/70 font-mono break-all">
							{event.inputSummary}
						</p>
					)}
					{event.errorCode && (
						<p className="text-[10px] text-red-400 font-mono">{event.errorCode}</p>
					)}
				</div>
			)}
		</div>
	);
}

export function ControlToolEventsTab() {
	const { data, isLoading, error } = useQuery<ToolEventsData>({
		queryKey: ["control", "tool-events"],
		queryFn: async () => {
			const res = await fetch("/api/control/tool-events", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<ToolEventsData>;
		},
		staleTime: 10_000,
		refetchInterval: 15_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading events…
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

	const events = data?.events ?? [];

	return (
		<div className="p-4 space-y-3">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Tool Events</h2>
				<div className="flex items-center gap-2">
					{data?.degraded && (
						<span className="text-[10px] font-mono text-amber-500">
							degraded: {data.degraded_reasons?.join(", ")}
						</span>
					)}
					<span className="text-xs text-muted-foreground">{data?.total ?? 0} total</span>
				</div>
			</div>

			{events.length === 0 ? (
				<div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
					<Wrench className="h-8 w-8 opacity-20" />
					<span className="text-sm">No tool events yet</span>
				</div>
			) : (
				<div className="space-y-1.5">
					{events.map((e) => (
						<ToolEventRow key={e.id} event={e} />
					))}
				</div>
			)}
		</div>
	);
}
