"use client";

// Control Sessions Tab — Phase 22b (AC6, read-only)
// Session lifecycle: status, filter, token pressure, drilldown.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Circle, Loader2, Skull, Square } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/utils";
import { ControlActionBadge } from "../ControlActionBadge";
import { ControlActionGuard } from "../ControlActionGuard";
import { KillSessionConfirmDialog } from "../KillSessionConfirmDialog";

interface SessionEntry {
	id: string;
	agentId: string;
	status: "running" | "paused" | "completed" | "error";
	tokenUsage: number;
	tokenLimit: number;
	startedAt: string;
	updatedAt: string;
}

interface SessionsData {
	sessions: SessionEntry[];
	total: number;
}

function StatusBadge({ status }: { status: SessionEntry["status"] }) {
	const map: Record<SessionEntry["status"], { label: string; cls: string }> = {
		running: { label: "running", cls: "bg-emerald-500/20 text-emerald-400" },
		paused: { label: "paused", cls: "bg-amber-500/20 text-amber-400" },
		completed: { label: "done", cls: "bg-muted text-muted-foreground" },
		error: { label: "error", cls: "bg-red-500/20 text-red-400" },
	};
	const { label, cls } = map[status] ?? map.error;
	return (
		<span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${cls}`}>
			{label}
		</span>
	);
}

function TokenBar({ usage, limit }: { usage: number; limit: number }) {
	const pct = limit > 0 ? Math.min((usage / limit) * 100, 100) : 0;
	const color = pct > 85 ? "bg-red-500" : pct > 60 ? "bg-amber-500" : "bg-emerald-500";
	return (
		<div className="flex items-center gap-2">
			<div className="h-1.5 w-20 rounded-full bg-muted overflow-hidden">
				<div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
			</div>
			<span className="text-[10px] font-mono text-muted-foreground">{Math.round(pct)}%</span>
		</div>
	);
}

export function ControlSessionsTab() {
	const queryClient = useQueryClient();
	const [killTarget, setKillTarget] = useState<string | null>(null);

	const { data, isLoading, error } = useQuery<SessionsData>({
		queryKey: ["control", "sessions"],
		queryFn: async () => {
			const res = await fetch("/api/control/sessions", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<SessionsData>;
		},
		staleTime: 10_000,
		refetchInterval: 20_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading sessions…
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

	const sessions = data?.sessions ?? [];

	return (
		<>
			<div className="p-4 space-y-3">
				<div className="flex items-center justify-between">
					<h2 className="text-sm font-semibold text-foreground">Sessions</h2>
					<span className="text-xs text-muted-foreground">{data?.total ?? 0} total</span>
				</div>

				{sessions.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
						<Square className="h-8 w-8 opacity-20" />
						<span className="text-sm">No active sessions</span>
					</div>
				) : (
					<div className="space-y-2">
						{sessions.map((s) => (
							<div
								key={s.id}
								className="rounded-lg border border-border bg-card px-3 py-2.5 flex items-center gap-3"
							>
								<Circle
									className={`h-2 w-2 shrink-0 ${
										s.status === "running"
											? "fill-emerald-500 text-emerald-500"
											: "fill-muted-foreground text-muted-foreground"
									}`}
								/>
								<div className="flex-1 min-w-0">
									<div className="flex items-center gap-2">
										<span className="text-xs font-mono text-foreground truncate">{s.id}</span>
										<StatusBadge status={s.status} />
									</div>
									<div className="flex items-center gap-3 mt-0.5">
										<span className="text-[10px] text-muted-foreground">{s.agentId}</span>
										<TokenBar usage={s.tokenUsage} limit={s.tokenLimit} />
									</div>
								</div>
								<span className="text-[10px] text-muted-foreground/60 shrink-0">
									{new Date(s.updatedAt).toLocaleTimeString()}
								</span>
								{/* AC17: kill-session is approval-write — badge + guard */}
								<ControlActionGuard action="kill-session" showLocked>
									<div className="flex items-center gap-1.5">
										<ControlActionBadge actionClass="approval-write" />
										<Button
											variant="ghost"
											size="sm"
											className="h-6 px-1.5 text-destructive hover:text-destructive hover:bg-destructive/10"
											onClick={() => setKillTarget(s.id)}
											disabled={s.status === "completed"}
										>
											<Skull className="h-3 w-3" />
										</Button>
									</div>
								</ControlActionGuard>
							</div>
						))}
					</div>
				)}
			</div>

			<KillSessionConfirmDialog
				open={killTarget !== null}
				sessionId={killTarget ?? ""}
				onClose={() => setKillTarget(null)}
				onSuccess={() => {
					void queryClient.invalidateQueries({ queryKey: ["control", "sessions"] });
				}}
			/>
		</>
	);
}
