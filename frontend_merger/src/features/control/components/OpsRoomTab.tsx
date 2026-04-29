"use client";

import {
	Activity,
	AlertTriangle,
	CheckCircle2,
	Clock,
	ExternalLink,
	History,
	Radar,
	Wrench,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuditEvents, useSessions, useTools } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockAuditEvents, mockSessions, mockTools } from "../mock-data";
import type { AuditEvent, Session, ToolDefinition } from "../types";

type LaneStatus = "active" | "waiting" | "blocked" | "replay";

const STATUS_COLOR: Record<LaneStatus, string> = {
	active: "border-emerald-500/40 text-emerald-400",
	waiting: "border-sky-500/40 text-sky-400",
	blocked: "border-rose-500/40 text-rose-400",
	replay: "border-amber-500/40 text-amber-400",
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

function statusForSession(session: Session, events: AuditEvent[]): LaneStatus {
	if (session.is_active) return "active";
	const failedEvent = events.find(
		(event) => event.thread_id === session.thread_id && !event.success,
	);
	if (failedEvent) return "blocked";
	if ((session.tool_calls ?? 0) > 0) return "waiting";
	return "replay";
}

export function OpsRoomTab() {
	const sessionsQuery = useSessions();
	const toolsQuery = useTools();
	const auditQuery = useAuditEvents({ limit: 12 });
	const sessions = (sessionsQuery.data?.items as Session[] | undefined) ?? mockSessions;
	const tools = (toolsQuery.data?.items as ToolDefinition[] | undefined) ?? mockTools;
	const events = (auditQuery.data?.items as AuditEvent[] | undefined) ?? mockAuditEvents;
	const toolByName = new Map(tools.map((tool) => [tool.name, tool]));
	const toolEvents = events.filter((event) => event.tool_name);
	const blockedEvents = events.filter((event) => !event.success);
	const approvalTools = tools.filter(
		(tool) => tool.approval === "confirm" || tool.approval === "deny" || tool.risk === "high",
	);

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-base font-semibold">Agent Ops Room</h2>
					<p className="text-xs text-muted-foreground">
						{sessions.length} sessions · {toolEvents.length} recent tool events ·{" "}
						{blockedEvents.length} blockers
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

			<div className="grid grid-cols-1 gap-3 md:grid-cols-4">
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Active</span>
						<Activity className="h-3.5 w-3.5 text-emerald-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{sessions.filter((session) => session.is_active).length}
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
						{sessions.filter((session) => !session.is_active).length}
					</div>
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
							const status = statusForSession(session, events);
							return (
								<div key={session.thread_id} className="rounded border border-border/50 p-3">
									<div className="flex flex-wrap items-start justify-between gap-2">
										<div className="min-w-0">
											<p className="truncate font-mono text-xs">{session.thread_id}</p>
											<p className="text-[10px] text-muted-foreground">
												{session.role?.replaceAll("_", " ") ?? "unknown role"}
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
										{session.last_message_preview ?? "No preview available"}
									</p>
									<div className="mt-3 flex flex-wrap gap-2 text-[10px] text-muted-foreground">
										<span>{session.message_count ?? session.checkpoint_count ?? 0} events</span>
										<span>{session.tool_calls ?? 0} tools</span>
										<span>
											{formatRelative(session.last_message_at ?? session.last_checkpoint)}
										</span>
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
								<Wrench className="h-3.5 w-3.5" />
								Tool Timeline
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							{toolEvents.slice(0, 8).map((event) => {
								const tool = event.tool_name ? toolByName.get(event.tool_name) : undefined;
								return (
									<div key={event.id} className="rounded border border-border/50 p-3">
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
												{event.action}
											</span>
											<span className="flex items-center gap-1">
												<Clock className="h-3 w-3" />
												{formatRelative(event.timestamp)}
											</span>
										</div>
									</div>
								);
							})}
						</CardContent>
					</Card>

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
