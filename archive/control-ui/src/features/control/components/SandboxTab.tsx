"use client";

// SandboxTab — recent OpenSandbox runs (exec-12 Phase 1)
// Slice 5.4 (NEU coverage gap): Sandbox Runs Browser

import { AlertCircle, CheckCircle2, Clock, Loader2, Skull, XCircle } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useSandboxRuns } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockSandboxRuns } from "../mock-data";
import type { SandboxRun, SandboxStatus } from "../types";

const STATUS_ICON: Record<SandboxStatus, React.ReactNode> = {
	running: <Loader2 className="h-3 w-3 animate-spin text-sky-400" />,
	completed: <CheckCircle2 className="h-3 w-3 text-emerald-500" />,
	failed: <XCircle className="h-3 w-3 text-rose-500" />,
	timeout: <Clock className="h-3 w-3 text-amber-500" />,
	killed: <Skull className="h-3 w-3 text-rose-500" />,
};

const STATUS_COLOR: Record<SandboxStatus, string> = {
	running: "border-sky-500/50 text-sky-400",
	completed: "border-emerald-500/50 text-emerald-400",
	failed: "border-rose-500/50 text-rose-400",
	timeout: "border-amber-500/50 text-amber-400",
	killed: "border-rose-500/50 text-rose-400",
};

function formatDuration(ms: number | undefined): string {
	if (!ms) return "—";
	if (ms < 1000) return `${ms}ms`;
	if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
	return `${(ms / 60000).toFixed(1)}m`;
}

function formatRelative(iso: string): string {
	const diffMs = Date.now() - new Date(iso).getTime();
	const minutes = Math.floor(diffMs / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}

export function SandboxTab() {
	const [selected, setSelected] = useState<SandboxRun | null>(null);

	// Slice 7 Phase H: real backend with mock fallback
	const query = useSandboxRuns();
	const runs = (query.data?.items as SandboxRun[] | undefined) ?? mockSandboxRuns;

	const counts = runs.reduce<Record<SandboxStatus, number>>(
		(acc, r) => {
			acc[r.status] = (acc[r.status] ?? 0) + 1;
			return acc;
		},
		{ running: 0, completed: 0, failed: 0, timeout: 0, killed: 0 },
	);

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Sandbox Runs</h2>
					<p className="text-xs text-muted-foreground">
						{runs.length} recent runs · OpenSandbox (Port 8100)
					</p>
				</div>
				<div className="flex items-center gap-2">
					{(["running", "completed", "failed", "timeout"] as SandboxStatus[]).map((s) => (
						<div key={s} className="flex items-center gap-1.5 text-[11px]">
							{STATUS_ICON[s]}
							<span className="text-muted-foreground">{counts[s] ?? 0}</span>
						</div>
					))}
				</div>
			</header>

			<div className="rounded-lg border border-border overflow-hidden">
				<table className="w-full text-xs">
					<thead className="bg-card/40">
						<tr className="text-left">
							<th className="py-2 px-3 font-semibold w-8" />
							<th className="py-2 px-3 font-semibold">Tool</th>
							<th className="py-2 px-3 font-semibold">Role</th>
							<th className="py-2 px-3 font-semibold">Code Preview</th>
							<th className="py-2 px-3 font-semibold w-20">Duration</th>
							<th className="py-2 px-3 font-semibold w-24">Started</th>
							<th className="py-2 px-3 font-semibold w-20">Status</th>
						</tr>
					</thead>
					<tbody>
						{runs.map((run) => (
							<tr
								key={run.id}
								className="border-t border-border hover:bg-card/20 cursor-pointer"
								onClick={() => setSelected(run)}
							>
								<td className="py-2 px-3">{STATUS_ICON[run.status]}</td>
								<td className="py-2 px-3 font-mono text-[11px]">{run.tool_name}</td>
								<td className="py-2 px-3">
									<span className="text-muted-foreground">{run.role.replace(/_/g, " ")}</span>
								</td>
								<td className="py-2 px-3">
									<code className="text-[10px] line-clamp-1 text-muted-foreground">
										{run.code_preview.replace(/\n/g, " ")}
									</code>
								</td>
								<td className="py-2 px-3 font-mono text-[10px]">
									{formatDuration(run.duration_ms)}
								</td>
								<td className="py-2 px-3 text-[10px] text-muted-foreground">
									{formatRelative(run.started_at)}
								</td>
								<td className="py-2 px-3">
									<Badge
										variant="outline"
										className={cn("text-[9px] h-4 px-1.5", STATUS_COLOR[run.status])}
									>
										{run.status}
									</Badge>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>

			<Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
				<SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
					{selected && (
						<>
							<SheetHeader>
								<div className="flex items-center gap-2">
									{STATUS_ICON[selected.status]}
									<SheetTitle className="font-mono text-sm">{selected.id}</SheetTitle>
								</div>
								<SheetDescription>
									{selected.tool_name} · {selected.role} · {selected.user_id}
								</SheetDescription>
							</SheetHeader>

							<div className="space-y-4 py-4">
								<section className="grid grid-cols-2 gap-3 text-xs">
									<div>
										<div className="text-[10px] uppercase text-muted-foreground">Started</div>
										<div className="font-mono">
											{new Date(selected.started_at).toLocaleString()}
										</div>
									</div>
									<div>
										<div className="text-[10px] uppercase text-muted-foreground">Duration</div>
										<div className="font-mono">{formatDuration(selected.duration_ms)}</div>
									</div>
									{selected.exit_code !== undefined && (
										<div>
											<div className="text-[10px] uppercase text-muted-foreground">Exit Code</div>
											<div
												className={cn(
													"font-mono",
													selected.exit_code === 0 ? "text-emerald-400" : "text-rose-400",
												)}
											>
												{selected.exit_code}
											</div>
										</div>
									)}
								</section>

								<section>
									<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
										Code
									</h3>
									<pre className="rounded-lg border border-border bg-card/40 p-3 text-[11px] leading-relaxed font-mono overflow-x-auto whitespace-pre-wrap">
										{selected.code_preview}
									</pre>
								</section>

								{selected.stdout_preview && (
									<section>
										<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
											stdout
										</h3>
										<pre className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3 text-[11px] leading-relaxed font-mono overflow-x-auto whitespace-pre-wrap">
											{selected.stdout_preview}
										</pre>
									</section>
								)}

								{selected.stderr_preview && (
									<section>
										<h3 className="text-xs font-semibold uppercase tracking-wide text-rose-400 mb-2 flex items-center gap-1">
											<AlertCircle className="h-3 w-3" />
											stderr
										</h3>
										<pre className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-[11px] leading-relaxed font-mono overflow-x-auto whitespace-pre-wrap text-rose-300">
											{selected.stderr_preview}
										</pre>
									</section>
								)}
							</div>
						</>
					)}
				</SheetContent>
			</Sheet>
		</div>
	);
}
