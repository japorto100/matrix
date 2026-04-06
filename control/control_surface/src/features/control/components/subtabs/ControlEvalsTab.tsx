"use client";

// AC10 — Evals Tab: evaluation run history (read-only v1).

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, FlaskConical, Loader2, XCircle } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface EvalRun {
	id: string;
	evalName: string;
	status: "running" | "passed" | "failed";
	score: number | null;
	ts: string;
}

interface EvalsData {
	runs: EvalRun[];
	total: number;
	degraded?: boolean;
	degraded_reasons?: string[];
}

function ScoreBar({ score }: { score: number }) {
	const pct = Math.min(score * 100, 100);
	const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
	return (
		<div className="flex items-center gap-2">
			<div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
				<div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
			</div>
			<span className="text-[10px] font-mono text-muted-foreground">{Math.round(pct)}%</span>
		</div>
	);
}

export function ControlEvalsTab() {
	const { data, isLoading, error } = useQuery<EvalsData>({
		queryKey: ["control", "evals"],
		queryFn: async () => {
			const res = await fetch("/api/control/evals", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<EvalsData>;
		},
		staleTime: 30_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading evals…
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

	const runs = data?.runs ?? [];

	return (
		<div className="p-4 space-y-3">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Eval Runs</h2>
				<div className="flex items-center gap-2">
					{data?.degraded && (
						<span className="text-[10px] font-mono text-amber-500">
							{data.degraded_reasons?.join(", ")}
						</span>
					)}
					<span className="text-xs text-muted-foreground">{data?.total ?? 0} total</span>
				</div>
			</div>

			{runs.length === 0 ? (
				<div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
					<FlaskConical className="h-8 w-8 opacity-20" />
					<span className="text-sm">No eval runs yet</span>
				</div>
			) : (
				<div className="space-y-1.5">
					{runs.map((r) => (
						<div
							key={r.id}
							className="rounded-lg border border-border bg-card px-3 py-2.5 flex items-center gap-3"
						>
							{r.status === "passed" ? (
								<CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
							) : r.status === "failed" ? (
								<XCircle className="h-3.5 w-3.5 shrink-0 text-red-500" />
							) : (
								<Loader2 className="h-3.5 w-3.5 shrink-0 text-blue-500 animate-spin" />
							)}
							<span className="text-xs font-mono text-foreground flex-1 truncate">
								{r.evalName}
							</span>
							{r.score !== null && <ScoreBar score={r.score} />}
							<span className="text-[10px] text-muted-foreground/40 shrink-0">
								{new Date(r.ts).toLocaleTimeString()}
							</span>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
