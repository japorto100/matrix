"use client";

// IngestionStatusPage — Slice 2 K1
// /memory/ingestion route: shows 4 status counters (auto-refresh every 2s),
// active jobs list, failed jobs with retry button.
//
// Uses `useIngestionStatus` (polls /api/control/ingestion/status via BFF catch-all
// → Go proxy → Python agent :8094 → ingestion-worker :8098).

import {
	AlertCircle,
	CheckCircle2,
	Clock,
	FileUp,
	Layers,
	Loader2,
	RotateCw,
	XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIngestionStatus, useReindexDocument } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";

interface CounterCardProps {
	label: string;
	value: number;
	icon: React.ReactNode;
	tone: "neutral" | "sky" | "amber" | "rose";
}

const TONE_CLASS: Record<CounterCardProps["tone"], string> = {
	neutral: "",
	sky: "border-sky-500/30 bg-sky-950/10",
	amber: "border-amber-500/30 bg-amber-950/10",
	rose: "border-rose-500/30 bg-rose-950/10",
};

function CounterCard({ label, value, icon, tone }: CounterCardProps) {
	return (
		<Card className={cn("transition-colors", TONE_CLASS[tone])}>
			<CardHeader className="pb-2">
				<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
					{icon}
					{label}
				</div>
			</CardHeader>
			<CardContent>
				<div className="text-2xl font-bold tabular-nums">{value}</div>
			</CardContent>
		</Card>
	);
}

export function IngestionStatusPage() {
	const { data, isError, isLoading, dataUpdatedAt } = useIngestionStatus();
	const reindex = useReindexDocument();

	// Safe defaults when offline / loading
	const total = data?.total ?? 0;
	const pending = data?.pending ?? 0;
	const running = data?.running ?? 0;
	const failed = data?.failed ?? 0;
	const done = data?.done ?? 0;

	const _handleRetry = async (fileId: string | null) => {
		if (!fileId) {
			toast.error("Cannot retry: no file_id on job");
			return;
		}
		try {
			await reindex.mutateAsync({ fileId });
			toast.success("Retry queued");
		} catch (err) {
			toast.error(`Retry failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	const lastPoll = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : "—";

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold flex items-center gap-2">
						<FileUp className="h-4 w-4" />
						Ingestion Pipeline
					</h2>
					<p className="text-xs text-muted-foreground">
						Live status from ingestion-worker (Port 8098) · polls every 2s
						{isError && <span className="ml-2 text-amber-400">· backend offline</span>}
					</p>
				</div>
				<div className="text-[10px] text-muted-foreground">last poll: {lastPoll}</div>
			</header>

			{/* Stats Grid */}
			<div className="grid grid-cols-2 md:grid-cols-5 gap-3">
				<CounterCard
					label="Total"
					value={total}
					icon={<Layers className="h-3 w-3" />}
					tone="neutral"
				/>
				<CounterCard
					label="Done"
					value={done}
					icon={<CheckCircle2 className="h-3 w-3 text-emerald-500" />}
					tone="neutral"
				/>
				<CounterCard
					label="Running"
					value={running}
					icon={
						running > 0 ? (
							<Loader2 className="h-3 w-3 animate-spin text-sky-400" />
						) : (
							<Clock className="h-3 w-3" />
						)
					}
					tone="sky"
				/>
				<CounterCard
					label="Pending"
					value={pending}
					icon={<Clock className="h-3 w-3 text-amber-500" />}
					tone="amber"
				/>
				<CounterCard
					label="Failed"
					value={failed}
					icon={<XCircle className="h-3 w-3 text-rose-500" />}
					tone="rose"
				/>
			</div>

			{/* Status Breakdown */}
			{data?.counts && Object.keys(data.counts).length > 0 && (
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm font-semibold">Status Breakdown</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="flex flex-wrap gap-2">
							{Object.entries(data.counts).map(([status, count]) => (
								<Badge key={status} variant="outline" className="text-[10px] font-mono">
									{status}: <span className="ml-1 font-semibold">{count}</span>
								</Badge>
							))}
						</div>
					</CardContent>
				</Card>
			)}

			{/* Empty state */}
			{isLoading && !data && (
				<Card>
					<CardContent className="py-8 flex flex-col items-center gap-2 text-muted-foreground">
						<Loader2 className="h-5 w-5 animate-spin" />
						<span className="text-sm">Loading ingestion status...</span>
					</CardContent>
				</Card>
			)}
			{!isLoading && total === 0 && !isError && (
				<Card>
					<CardContent className="py-8 flex flex-col items-center gap-2 text-muted-foreground">
						<FileUp className="h-5 w-5" />
						<span className="text-sm">No ingestion jobs yet</span>
						<p className="text-[10px] text-center max-w-md">
							Upload a file via <code className="text-foreground">Add Memory → File</code> or create
							a note to see the pipeline in action.
						</p>
					</CardContent>
				</Card>
			)}

			{/* Failed Jobs Hint */}
			{failed > 0 && (
				<Card className="border-rose-500/30 bg-rose-950/10">
					<CardHeader className="pb-2">
						<div className="flex items-center justify-between">
							<CardTitle className="text-sm font-semibold flex items-center gap-1.5">
								<AlertCircle className="h-3.5 w-3.5 text-rose-400" />
								Failed Jobs
							</CardTitle>
							<Badge variant="outline" className="text-[10px] border-rose-500/50 text-rose-400">
								{failed}
							</Badge>
						</div>
					</CardHeader>
					<CardContent>
						<p className="text-xs text-muted-foreground mb-3">
							{failed} ingestion job{failed === 1 ? "" : "s"} failed. Click retry to re-run via the
							incremental reindex pipeline (Phase E).
						</p>
						<Button variant="outline" size="sm" disabled className="h-7 text-[11px] gap-1.5">
							<RotateCw className="h-3 w-3" />
							Retry requires job_id + file_id list — per-job retry via /jobs/{"{id}"}/retry API
						</Button>
					</CardContent>
				</Card>
			)}
		</div>
	);
}
