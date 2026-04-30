"use client";

import {
	Activity,
	AlertTriangle,
	CheckCircle2,
	Clock,
	ExternalLink,
	History,
	Radar,
	Search,
	Wrench,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useOpsEvents, useTools } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockOpsReadModel, mockTools } from "../mock-data";
import type {
	AgentOpsEvent,
	AgentOpsReadModel,
	AgentOpsSession,
	AgentRuntimeEvent,
	ToolDefinition,
} from "../types";

type LaneStatus = "active" | "waiting" | "blocked" | "replay" | "needs_approval" | "failed";

const STATUS_COLOR: Record<LaneStatus, string> = {
	active: "border-emerald-500/40 text-emerald-400",
	waiting: "border-sky-500/40 text-sky-400",
	blocked: "border-rose-500/40 text-rose-400",
	replay: "border-amber-500/40 text-amber-400",
	needs_approval: "border-orange-500/40 text-orange-400",
	failed: "border-rose-500/40 text-rose-400",
};

function formatRelative(iso?: string): string {
	if (!iso) return "unknown";
	const diffMs = Date.now() - new Date(iso).getTime();
	if (Number.isNaN(diffMs)) return iso;
	const minutes = Math.floor(diffMs / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}

function riskClass(tool?: ToolDefinition): string {
	if (!tool?.risk) return "border-border text-muted-foreground";
	if (tool.risk === "critical" || tool.risk === "high") return "border-rose-500/40 text-rose-400";
	if (tool.risk === "medium") return "border-amber-500/40 text-amber-400";
	return "border-emerald-500/40 text-emerald-400";
}

function compactJson(value: unknown): string {
	if (!value || typeof value !== "object") return "";
	try {
		return JSON.stringify(value, null, 2);
	} catch {
		return String(value);
	}
}

function countEntries(counts?: Record<string, number>): Array<[string, number]> {
	return Object.entries(counts ?? {}).sort(([, a], [, b]) => b - a);
}

function runtimeLabel(event?: AgentRuntimeEvent): string {
	if (!event) return "runtime";
	return event.name || [event.kind, event.status].filter(Boolean).join(":") || "runtime";
}

export function OpsRoomTab() {
	const [statusFilter, setStatusFilter] = useState("all");
	const [riskFilter, setRiskFilter] = useState("all");
	const [toolFilter, setToolFilter] = useState("all");
	const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
	const filters = useMemo(() => {
		const next: Record<string, string> = {};
		if (statusFilter !== "all") next.status = statusFilter;
		if (riskFilter !== "all") next.risk = riskFilter;
		if (toolFilter !== "all") next.tool = toolFilter;
		return next;
	}, [riskFilter, statusFilter, toolFilter]);
	const opsQuery = useOpsEvents(filters);
	const toolsQuery = useTools();
	const tools = (toolsQuery.data?.items as ToolDefinition[] | undefined) ?? mockTools;
	const ops = (opsQuery.data as AgentOpsReadModel | undefined) ?? mockOpsReadModel;
	const sessions = ops.sessions as AgentOpsSession[];
	const events = ops.items as AgentOpsEvent[];
	const runtimeEvents = ops.runtime_events ?? [];
	const runtimeSummary = ops.runtime_summary ?? {
		total: runtimeEvents.length,
		by_kind: {},
		by_status: {},
		latest: runtimeEvents[0],
	};
	const toolByName = new Map(tools.map((tool) => [tool.name, tool]));
	const toolEvents = events.filter((event) => event.tool_name);
	const blockedEvents = ops.blockers;
	const selectedEvent = events.find((event) => event.id === selectedEventId) ?? toolEvents[0];
	const approvalTools = tools.filter(
		(tool) => tool.approval === "confirm" || tool.approval === "deny" || tool.risk === "high",
	);
	const toolNames = Array.from(new Set(toolEvents.map((event) => event.tool_name).filter(Boolean)));

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-base font-semibold">Agent Ops Room</h2>
					<p className="text-xs text-muted-foreground">
						{ops.summary.sessions} sessions · {ops.summary.tool_events} recent tool events ·{" "}
						{ops.summary.blockers} blockers · {runtimeSummary.total} runtime events
					</p>
				</div>
				<div className="flex flex-wrap items-center gap-2">
					<Link href="/control/audit">
						<Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
							<History className="h-3 w-3" />
							Audit
						</Button>
					</Link>
					<Link href="/matrix">
						<Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
							<ExternalLink className="h-3 w-3" />
							Matrix
						</Button>
					</Link>
				</div>
			</header>

			<div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card/30 p-2">
				<Search className="h-3.5 w-3.5 text-muted-foreground" />
				<select
					value={statusFilter}
					onChange={(event) => setStatusFilter(event.target.value)}
					className="h-8 rounded border border-border bg-background px-2 text-xs"
				>
					<option value="all">All status</option>
					<option value="active">Active</option>
					<option value="waiting">Waiting</option>
					<option value="blocked">Blocked</option>
					<option value="needs_approval">Needs approval</option>
				</select>
				<select
					value={riskFilter}
					onChange={(event) => setRiskFilter(event.target.value)}
					className="h-8 rounded border border-border bg-background px-2 text-xs"
				>
					<option value="all">All risk</option>
					<option value="critical">Critical</option>
					<option value="high">High</option>
					<option value="medium">Medium</option>
					<option value="low">Low</option>
					<option value="unrated">Unrated</option>
				</select>
				<select
					value={toolFilter}
					onChange={(event) => setToolFilter(event.target.value)}
					className="h-8 rounded border border-border bg-background px-2 text-xs"
				>
					<option value="all">All tools</option>
					{toolNames.map((name) => (
						<option key={name} value={name}>
							{name}
						</option>
					))}
				</select>
				<Badge variant="outline" className="ml-auto h-6 px-2 text-[10px]">
					{ops.contract}
				</Badge>
			</div>

			<div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Active</span>
						<Activity className="h-3.5 w-3.5 text-emerald-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{sessions.filter((session) => session.status === "active").length}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Tool Events</span>
						<Wrench className="h-3.5 w-3.5 text-sky-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{toolEvents.length}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Approval Watch</span>
						<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{approvalTools.length}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Replay Ready</span>
						<Radar className="h-3.5 w-3.5 text-purple-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{sessions.filter((session) => session.status === "replay").length}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Runtime Events</span>
						<Activity className="h-3.5 w-3.5 text-cyan-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{runtimeSummary.total}</div>
				</div>
			</div>

			<div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_390px]">
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="flex items-center gap-1.5 text-sm">
							<Radar className="h-3.5 w-3.5" />
							Session Board
						</CardTitle>
					</CardHeader>
					<CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
						{sessions.map((session) => {
							const status = session.status;
							return (
								<div key={session.thread_id} className="rounded border border-border/50 p-3">
									<div className="flex flex-wrap items-start justify-between gap-2">
										<div className="min-w-0">
											<p className="truncate font-mono text-xs">{session.thread_id}</p>
											<p className="text-[10px] text-muted-foreground">
												{session.agent_role?.replaceAll("_", " ") ?? "unknown role"}
											</p>
										</div>
										<Badge
											variant="outline"
											className={cn("h-5 px-1.5 text-[10px]", STATUS_COLOR[status])}
										>
											{status}
										</Badge>
									</div>
									<p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
										{session.event_count} ops events · {session.tool_count} tool calls
									</p>
									<div className="mt-3 flex flex-wrap gap-2 text-[10px] text-muted-foreground">
										<span>{session.checkpoint_count} checkpoints</span>
										<span>{session.tool_count} tools</span>
										<span>{formatRelative(session.last_checkpoint)}</span>
									</div>
								</div>
							);
						})}
					</CardContent>
				</Card>

				<div className="space-y-4">
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="flex items-center gap-1.5 text-sm">
								<Activity className="h-3.5 w-3.5" />
								Runtime Lanes
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							<div className="flex flex-wrap gap-1.5">
								{countEntries(runtimeSummary.by_kind).length === 0 ? (
									<Badge variant="outline" className="h-5 px-1.5 text-[10px]">
										no events
									</Badge>
								) : (
									countEntries(runtimeSummary.by_kind).map(([kind, count]) => (
										<Badge key={kind} variant="outline" className="h-5 px-1.5 text-[10px]">
											{kind} {count}
										</Badge>
									))
								)}
							</div>
							<div className="flex flex-wrap gap-1.5">
								{countEntries(runtimeSummary.by_status)
									.slice(0, 6)
									.map(([status, count]) => (
										<Badge
											key={status}
											variant="outline"
											className={cn(
												"h-5 px-1.5 text-[10px]",
												STATUS_COLOR[(status as LaneStatus) || "waiting"] ??
													"border-border text-muted-foreground",
											)}
										>
											{status} {count}
										</Badge>
									))}
							</div>
							{runtimeEvents.slice(0, 5).map((event, index) => (
								<div
									key={event.event_id ?? `${event.name}-${index}`}
									className="rounded border border-border/50 p-2"
								>
									<div className="flex items-start justify-between gap-2">
										<p className="min-w-0 truncate font-mono text-xs">{runtimeLabel(event)}</p>
										<Badge variant="outline" className="h-5 px-1.5 text-[10px]">
											{event.kind ?? "unknown"}
										</Badge>
									</div>
									<p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
										{event.summary || event.status || "runtime event"}
									</p>
								</div>
							))}
						</CardContent>
					</Card>

					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="flex items-center gap-1.5 text-sm">
								<Wrench className="h-3.5 w-3.5" />
								Tool Timeline
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							{toolEvents.slice(0, 8).map((event) => {
								const tool = event.tool_name ? toolByName.get(event.tool_name) : undefined;
								return (
									<button
										key={event.id}
										type="button"
										onClick={() => setSelectedEventId(event.id)}
										className={cn(
											"w-full rounded border border-border/50 p-3 text-left transition hover:border-primary/40",
											selectedEvent?.id === event.id && "border-primary/60 bg-primary/5",
										)}
									>
										<div className="flex items-center justify-between gap-2">
											<p className="truncate font-mono text-xs">{event.tool_name}</p>
											<Badge
												variant="outline"
												className={cn("h-5 px-1.5 text-[10px]", riskClass(tool))}
											>
												{tool?.risk ?? "unrated"}
											</Badge>
										</div>
										<div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
											<span className="flex items-center gap-1">
												{event.success ? (
													<CheckCircle2 className="h-3 w-3 text-emerald-400" />
												) : (
													<AlertTriangle className="h-3 w-3 text-rose-400" />
												)}
												{event.status}
											</span>
											<span className="flex items-center gap-1">
												<Clock className="h-3 w-3" />
												{formatRelative(event.timestamp)}
											</span>
										</div>
									</button>
								);
							})}
						</CardContent>
					</Card>

					{selectedEvent ? (
						<Card>
							<CardHeader className="pb-3">
								<CardTitle className="flex items-center gap-1.5 text-sm">
									<Wrench className="h-3.5 w-3.5" />
									Tool Drilldown
								</CardTitle>
							</CardHeader>
							<CardContent className="space-y-3 text-xs">
								<div className="flex flex-wrap gap-2">
									<Badge variant="outline">{selectedEvent.tool_name ?? selectedEvent.action}</Badge>
									<Badge variant="outline">{selectedEvent.risk}</Badge>
									<Badge variant="outline">{selectedEvent.status}</Badge>
								</div>
								<div className="grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
									<span>audit {selectedEvent.audit_ref || "n/a"}</span>
									<span>approval {selectedEvent.approval_ref || "n/a"}</span>
									<span>{selectedEvent.agent_role || "unknown role"}</span>
									<span>{selectedEvent.duration_ms ?? 0}ms</span>
								</div>
								{selectedEvent.error ? (
									<p className="rounded border border-rose-500/30 bg-rose-500/5 p-2 text-rose-300">
										{selectedEvent.error}
									</p>
								) : null}
								<pre className="max-h-44 overflow-auto rounded border border-border/60 bg-muted/20 p-2 text-[10px] leading-relaxed">
									{compactJson({
										input: selectedEvent.input,
										output: selectedEvent.output,
										metadata: selectedEvent.metadata,
										request_telemetry: selectedEvent.request_telemetry,
										runtime_events: selectedEvent.runtime_events,
									})}
								</pre>
							</CardContent>
						</Card>
					) : null}

					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="flex items-center gap-1.5 text-sm">
								<AlertTriangle className="h-3.5 w-3.5" />
								Blockers
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-2">
							{blockedEvents.length === 0 ? (
								<p className="text-xs text-muted-foreground">No failed events in current window.</p>
							) : (
								blockedEvents.slice(0, 5).map((event) => (
									<div
										key={event.id}
										className="rounded border border-rose-500/30 bg-rose-500/5 p-2"
									>
										<p className="text-xs font-medium">{event.action}</p>
										<p className="line-clamp-2 text-[11px] text-muted-foreground">
											{event.error ?? "Failed event requires audit drilldown"}
										</p>
									</div>
								))
							)}
						</CardContent>
					</Card>
				</div>
			</div>
		</div>
	);
}
