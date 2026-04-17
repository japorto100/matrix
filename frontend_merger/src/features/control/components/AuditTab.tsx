"use client";

// AuditTab — audit_events table viewer (exec-12 Phase 2.1)
// Slice 6.3: Audit Log
// K9 (Slice 6): CSV/JSON export via Blob download (client-side, no backend)

import { CheckCircle2, Download, Search, XCircle } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useAuditEvents } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockAuditEvents } from "../mock-data";
import type { AuditEvent } from "../types";

// ── CSV Export Helpers ──────────────────────────────────────────────────────

const CSV_COLUMNS = [
	"id",
	"timestamp",
	"action",
	"success",
	"user_id",
	"thread_id",
	"agent_role",
	"tool_name",
	"duration_ms",
	"error",
] as const;

function csvEscape(value: unknown): string {
	if (value === null || value === undefined) return "";
	const s = typeof value === "string" ? value : String(value);
	if (/[",\n\r]/.test(s)) {
		return `"${s.replace(/"/g, '""')}"`;
	}
	return s;
}

function eventsToCsv(events: AuditEvent[]): string {
	const header = CSV_COLUMNS.join(",");
	const rows = events.map((e) =>
		CSV_COLUMNS.map((col) => csvEscape((e as unknown as Record<string, unknown>)[col])).join(","),
	);
	return [header, ...rows].join("\r\n");
}

function downloadBlob(content: string, mime: string, extension: string): void {
	const blob = new Blob([content], { type: `${mime};charset=utf-8` });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `audit-${Date.now()}.${extension}`;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

const ACTION_COLOR: Record<string, string> = {
	TOOL_CALL: "border-sky-500/50 text-sky-400",
	MEMORY_RETAIN: "border-purple-500/50 text-purple-400",
	MEMORY_RECALL: "border-purple-500/50 text-purple-400",
	SANDBOX_RUN: "border-amber-500/50 text-amber-400",
	SANDBOX_FAILED: "border-rose-500/50 text-rose-400",
	SANDBOX_TIMEOUT: "border-rose-500/50 text-rose-400",
	SKILL_USED: "border-emerald-500/50 text-emerald-400",
	INGESTION_FAILED: "border-rose-500/50 text-rose-400",
	INGESTION_DONE: "border-emerald-500/50 text-emerald-400",
	ROLE_OVERRIDE_UPDATED: "border-amber-500/50 text-amber-400",
};

function colorFor(action: string): string {
	return ACTION_COLOR[action] ?? "border-muted-foreground/50 text-muted-foreground";
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

export function AuditTab() {
	const [filter, setFilter] = useState("");
	const [actionFilter, setActionFilter] = useState<string>("all");
	const [resultFilter, setResultFilter] = useState<"all" | "success" | "error">("all");
	const [selected, setSelected] = useState<AuditEvent | null>(null);

	// Slice 7 Phase H: real backend with mock fallback
	const query = useAuditEvents({ limit: 100 });
	const events = (query.data?.items as AuditEvent[] | undefined) ?? mockAuditEvents;

	const actions = useMemo(() => {
		const set = new Set<string>();
		for (const e of events) set.add(e.action);
		return Array.from(set).sort();
	}, [events]);

	const filtered = useMemo(() => {
		return events.filter((e) => {
			if (actionFilter !== "all" && e.action !== actionFilter) return false;
			if (resultFilter === "success" && !e.success) return false;
			if (resultFilter === "error" && e.success) return false;
			if (filter) {
				const f = filter.toLowerCase();
				const haystack = [e.action, e.user_id, e.thread_id, e.agent_role, e.tool_name, e.error]
					.filter(Boolean)
					.join(" ")
					.toLowerCase();
				if (!haystack.includes(f)) return false;
			}
			return true;
		});
	}, [events, filter, actionFilter, resultFilter]);

	const handleExportCsv = () => {
		downloadBlob(eventsToCsv(filtered), "text/csv", "csv");
	};

	const handleExportJson = () => {
		downloadBlob(JSON.stringify(filtered, null, 2), "application/json", "json");
	};

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between gap-4 flex-wrap">
				<div>
					<h2 className="text-base font-semibold">Audit Log</h2>
					<p className="text-xs text-muted-foreground">
						{filtered.length} of {events.length} events · <code>agent.audit_events</code> table
						(exec-12 Phase 2.1)
					</p>
				</div>
				<div className="flex items-center gap-2 flex-wrap">
					<div className="relative">
						<Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
						<Input
							placeholder="Filter..."
							value={filter}
							onChange={(e) => setFilter(e.target.value)}
							className="pl-7 h-8 w-44 text-xs"
						/>
					</div>
					<Select value={actionFilter} onValueChange={setActionFilter}>
						<SelectTrigger className="h-8 w-40 text-xs">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All actions</SelectItem>
							{actions.map((a) => (
								<SelectItem key={a} value={a}>
									{a}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
					<Select value={resultFilter} onValueChange={(v) => setResultFilter(v as never)}>
						<SelectTrigger className="h-8 w-28 text-xs">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">All results</SelectItem>
							<SelectItem value="success">Success</SelectItem>
							<SelectItem value="error">Errors</SelectItem>
						</SelectContent>
					</Select>
					<DropdownMenu>
						<DropdownMenuTrigger asChild>
							<Button
								variant="outline"
								size="sm"
								className="h-8 gap-1.5 text-xs"
								disabled={filtered.length === 0}
							>
								<Download className="h-3 w-3" />
								Export ({filtered.length})
							</Button>
						</DropdownMenuTrigger>
						<DropdownMenuContent align="end">
							<DropdownMenuItem onClick={handleExportCsv}>Export as CSV</DropdownMenuItem>
							<DropdownMenuItem onClick={handleExportJson}>Export as JSON</DropdownMenuItem>
						</DropdownMenuContent>
					</DropdownMenu>
				</div>
			</header>

			<div className="rounded-lg border border-border overflow-hidden">
				<table className="w-full text-xs">
					<thead className="bg-card/40">
						<tr className="text-left">
							<th className="py-2 px-3 font-semibold w-16">ID</th>
							<th className="py-2 px-3 font-semibold w-44">Action</th>
							<th className="py-2 px-3 font-semibold">Tool / Target</th>
							<th className="py-2 px-3 font-semibold w-32">Role</th>
							<th className="py-2 px-3 font-semibold w-20 text-right">Duration</th>
							<th className="py-2 px-3 font-semibold w-20 text-center">Result</th>
							<th className="py-2 px-3 font-semibold w-24">Time</th>
						</tr>
					</thead>
					<tbody>
						{filtered.map((event) => (
							<tr
								key={event.id}
								className="border-t border-border hover:bg-card/20 cursor-pointer"
								onClick={() => setSelected(event)}
							>
								<td className="py-2 px-3 font-mono text-[10px] text-muted-foreground">
									#{event.id}
								</td>
								<td className="py-2 px-3">
									<Badge
										variant="outline"
										className={cn("text-[10px] h-5 px-1.5", colorFor(event.action))}
									>
										{event.action}
									</Badge>
								</td>
								<td className="py-2 px-3">
									{event.tool_name ? (
										<code className="text-[11px]">{event.tool_name}</code>
									) : event.error ? (
										<span className="text-rose-400 text-[11px] line-clamp-1">{event.error}</span>
									) : (
										<span className="text-muted-foreground">—</span>
									)}
								</td>
								<td className="py-2 px-3 text-[10px] text-muted-foreground">
									{event.agent_role?.replace(/_/g, " ") ?? "—"}
								</td>
								<td className="py-2 px-3 text-right font-mono text-[10px]">
									{event.duration_ms !== undefined ? `${event.duration_ms}ms` : "—"}
								</td>
								<td className="py-2 px-3 text-center">
									{event.success ? (
										<CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mx-auto" />
									) : (
										<XCircle className="h-3.5 w-3.5 text-rose-500 mx-auto" />
									)}
								</td>
								<td className="py-2 px-3 text-[10px] text-muted-foreground">
									{formatRelative(event.timestamp)}
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
									{selected.success ? (
										<CheckCircle2 className="h-4 w-4 text-emerald-500" />
									) : (
										<XCircle className="h-4 w-4 text-rose-500" />
									)}
									<SheetTitle>Event #{selected.id}</SheetTitle>
								</div>
								<SheetDescription>
									<Badge variant="outline" className={cn("text-[10px]", colorFor(selected.action))}>
										{selected.action}
									</Badge>{" "}
									· {new Date(selected.timestamp).toLocaleString()}
								</SheetDescription>
							</SheetHeader>
							<div className="space-y-4 py-4 text-xs">
								<section className="grid grid-cols-2 gap-3">
									{selected.user_id && (
										<div>
											<div className="text-[10px] uppercase text-muted-foreground">User</div>
											<div className="font-mono">{selected.user_id}</div>
										</div>
									)}
									{selected.thread_id && (
										<div>
											<div className="text-[10px] uppercase text-muted-foreground">Thread</div>
											<div className="font-mono">{selected.thread_id}</div>
										</div>
									)}
									{selected.agent_role && (
										<div>
											<div className="text-[10px] uppercase text-muted-foreground">Role</div>
											<div>{selected.agent_role}</div>
										</div>
									)}
									{selected.tool_name && (
										<div>
											<div className="text-[10px] uppercase text-muted-foreground">Tool</div>
											<div className="font-mono">{selected.tool_name}</div>
										</div>
									)}
									{selected.duration_ms !== undefined && (
										<div>
											<div className="text-[10px] uppercase text-muted-foreground">Duration</div>
											<div className="font-mono">{selected.duration_ms}ms</div>
										</div>
									)}
								</section>

								{selected.input && (
									<section>
										<h3 className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
											Input
										</h3>
										<pre className="rounded-lg border border-border bg-card/40 p-2 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
											{JSON.stringify(selected.input, null, 2)}
										</pre>
									</section>
								)}

								{selected.output && (
									<section>
										<h3 className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
											Output
										</h3>
										<pre className="rounded-lg border border-border bg-card/40 p-2 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
											{JSON.stringify(selected.output, null, 2)}
										</pre>
									</section>
								)}

								{selected.error && (
									<section>
										<h3 className="text-[10px] uppercase tracking-wide text-rose-400 mb-1">
											Error
										</h3>
										<pre className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-2 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap text-rose-300">
											{selected.error}
										</pre>
									</section>
								)}

								{selected.metadata && Object.keys(selected.metadata).length > 0 && (
									<section>
										<h3 className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
											Metadata
										</h3>
										<pre className="rounded-lg border border-border bg-card/40 p-2 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
											{JSON.stringify(selected.metadata, null, 2)}
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
