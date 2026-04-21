"use client";

// A2aTab — Agent-to-Agent delegation log (exec-10 Phase 4 scaffold)
// Slice 6.7 (NEU coverage gap, optional): A2A Delegation Log

import { ArrowRight, CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useA2ADelegations } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockA2A } from "../mock-data";
import type { A2ADelegation } from "../types";

const STATUS_ICON: Record<A2ADelegation["status"], React.ReactNode> = {
	pending: <Clock className="h-3.5 w-3.5 text-muted-foreground" />,
	running: <Loader2 className="h-3.5 w-3.5 text-sky-400 animate-spin" />,
	completed: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
	failed: <XCircle className="h-3.5 w-3.5 text-rose-500" />,
};

const STATUS_COLOR: Record<A2ADelegation["status"], string> = {
	pending: "border-muted-foreground/50 text-muted-foreground",
	running: "border-sky-500/50 text-sky-400",
	completed: "border-emerald-500/50 text-emerald-400",
	failed: "border-rose-500/50 text-rose-400",
};

function formatRelative(iso: string): string {
	const diffMs = Date.now() - new Date(iso).getTime();
	const minutes = Math.floor(diffMs / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}

function formatDuration(start: string, end?: string): string {
	if (!end) return "running";
	const ms = new Date(end).getTime() - new Date(start).getTime();
	if (ms < 1000) return `${ms}ms`;
	if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
	return `${(ms / 60000).toFixed(1)}m`;
}

export function A2aTab() {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useA2ADelegations();
	const delegations = (query.data?.items as A2ADelegation[] | undefined) ?? mockA2A;

	const counts = delegations.reduce<Record<A2ADelegation["status"], number>>(
		(acc, d) => {
			acc[d.status] = (acc[d.status] ?? 0) + 1;
			return acc;
		},
		{ pending: 0, running: 0, completed: 0, failed: 0 },
	);

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">A2A Delegations</h2>
					<p className="text-xs text-muted-foreground">
						{delegations.length} delegations · {counts.completed} completed · {counts.running}{" "}
						running · {counts.pending} pending · {counts.failed} failed
					</p>
				</div>
				<Badge variant="outline" className="text-[10px] border-amber-500/50 text-amber-400">
					exec-10 Phase 4 scaffold (optional)
				</Badge>
			</header>

			<div className="space-y-3">
				{delegations.map((deleg) => (
					<Card key={deleg.id}>
						<CardHeader className="pb-2">
							<div className="flex items-start justify-between gap-3">
								<div className="flex items-center gap-2 flex-wrap">
									{STATUS_ICON[deleg.status]}
									<Badge variant="secondary" className="text-[10px] capitalize">
										{deleg.from_role.replace(/_/g, " ")}
									</Badge>
									<ArrowRight className="h-3 w-3 text-muted-foreground" />
									<Badge variant="secondary" className="text-[10px] capitalize">
										{deleg.to_role.replace(/_/g, " ")}
									</Badge>
								</div>
								<div className="flex flex-col items-end gap-0.5">
									<Badge
										variant="outline"
										className={cn("text-[9px] h-4", STATUS_COLOR[deleg.status])}
									>
										{deleg.status}
									</Badge>
									<span className="text-[10px] text-muted-foreground">
										{formatDuration(deleg.started_at, deleg.completed_at)}
									</span>
								</div>
							</div>
						</CardHeader>
						<CardContent className="space-y-2 pt-0">
							<div>
								<div className="text-[10px] uppercase text-muted-foreground mb-0.5">Task</div>
								<p className="text-xs leading-relaxed">{deleg.task}</p>
							</div>
							{deleg.result_preview && (
								<div>
									<div className="text-[10px] uppercase text-muted-foreground mb-0.5">Result</div>
									<p
										className={cn(
											"text-xs leading-relaxed line-clamp-3 rounded border p-2",
											deleg.status === "failed"
												? "text-rose-300 border-rose-500/30 bg-rose-950/20"
												: "text-muted-foreground border-border bg-card/40",
										)}
									>
										{deleg.result_preview}
									</p>
								</div>
							)}
							<div className="flex items-center gap-2 text-[10px] text-muted-foreground pt-1">
								<span>{formatRelative(deleg.started_at)}</span>
								<span>·</span>
								<code>{deleg.thread_id}</code>
							</div>
						</CardContent>
					</Card>
				))}
			</div>
		</div>
	);
}
