"use client";

// OverviewTab — TT1 User Mode Simplified + Dev Mode Full
// AI Health Indicator + counters + recent activity + last error + "View Memory →" link

import {
	Activity,
	AlertCircle,
	ArrowRight,
	Brain,
	CheckCircle2,
	ChevronRight,
	GitGraph,
	MessageCircle,
	Network,
	Wrench,
	XCircle,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useOverview } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockOverview } from "../mock-data";
import type { AiHealth, OverviewSnapshot } from "../types";

const HEALTH_ICON: Record<AiHealth, React.ReactNode> = {
	online: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
	degraded: <AlertCircle className="h-4 w-4 text-amber-500" />,
	offline: <XCircle className="h-4 w-4 text-rose-500" />,
};

const HEALTH_COLOR: Record<AiHealth, string> = {
	online: "border-emerald-500/30 bg-emerald-950/10",
	degraded: "border-amber-500/30 bg-amber-950/10",
	offline: "border-rose-500/30 bg-rose-950/10",
};

const HEALTH_BADGE: Record<AiHealth, string> = {
	online: "border-emerald-500/50 text-emerald-400",
	degraded: "border-amber-500/50 text-amber-400",
	offline: "border-rose-500/50 text-rose-400",
};

const ACTIVITY_KIND_ICON: Record<
	OverviewSnapshot["recent_activity"][number]["kind"],
	React.ReactNode
> = {
	tool_call: <Wrench className="h-2.5 w-2.5" />,
	memory: <Brain className="h-2.5 w-2.5" />,
	sandbox: <Activity className="h-2.5 w-2.5" />,
	error: <AlertCircle className="h-2.5 w-2.5 text-rose-400" />,
	ingestion: <GitGraph className="h-2.5 w-2.5" />,
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

export function OverviewTab() {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useOverview();
	const data = (query.data as OverviewSnapshot | undefined) ?? mockOverview;

	return (
		<div className="px-6 py-4 space-y-4">
			{/* AI Health Hero Card */}
			<Card className={cn("transition-colors", HEALTH_COLOR[data.ai_health])}>
				<CardHeader className="pb-3">
					<div className="flex items-start justify-between gap-2">
						<div className="flex items-center gap-2">
							{HEALTH_ICON[data.ai_health]}
							<CardTitle className="text-base font-semibold">AI Health</CardTitle>
							<Badge
								variant="outline"
								className={cn("text-[10px] capitalize", HEALTH_BADGE[data.ai_health])}
							>
								{data.ai_health}
							</Badge>
						</div>
					</div>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">{data.ai_health_message}</p>
				</CardContent>
			</Card>

			{/* Stats Grid */}
			<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
				<Card>
					<CardHeader className="pb-2">
						<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
							<Activity className="h-3 w-3" />
							Active Sessions
						</div>
					</CardHeader>
					<CardContent>
						<div className="text-2xl font-bold">{data.active_sessions}</div>
					</CardContent>
				</Card>

				<Card>
					<CardHeader className="pb-2">
						<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
							<Wrench className="h-3 w-3" />
							Running Tasks
						</div>
					</CardHeader>
					<CardContent>
						<div className="text-2xl font-bold">{data.active_tasks}</div>
					</CardContent>
				</Card>

				<Link href="/memory" className="block">
					<Card className="hover:border-accent transition-colors cursor-pointer h-full">
						<CardHeader className="pb-2">
							<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
								<Brain className="h-3 w-3" />
								Memory Facts
							</div>
						</CardHeader>
						<CardContent>
							<div className="flex items-baseline justify-between">
								<div className="text-2xl font-bold">{data.memory_facts_total.toLocaleString()}</div>
								<ChevronRight className="h-4 w-4 text-muted-foreground" />
							</div>
						</CardContent>
					</Card>
				</Link>

				<Link href="/memory/kg" className="block">
					<Card className="hover:border-accent transition-colors cursor-pointer h-full">
						<CardHeader className="pb-2">
							<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
								<Network className="h-3 w-3" />
								KG Nodes
							</div>
						</CardHeader>
						<CardContent>
							<div className="flex items-baseline justify-between">
								<div className="text-2xl font-bold">{data.kg_nodes_total}</div>
								<ChevronRight className="h-4 w-4 text-muted-foreground" />
							</div>
						</CardContent>
					</Card>
				</Link>
			</div>

			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				{/* Recent Activity */}
				<Card>
					<CardHeader className="pb-2">
						<div className="flex items-center justify-between">
							<CardTitle className="text-sm font-semibold flex items-center gap-1.5">
								<MessageCircle className="h-3.5 w-3.5" />
								Recent Activity
							</CardTitle>
							<Link href="/control/audit">
								<Button variant="ghost" size="sm" className="h-6 text-[10px] gap-1">
									Audit log
									<ArrowRight className="h-2.5 w-2.5" />
								</Button>
							</Link>
						</div>
					</CardHeader>
					<CardContent className="space-y-2">
						{data.recent_activity.map((activity) => (
							<div
								key={activity.timestamp}
								className="flex items-start gap-2 text-xs py-1 border-b border-border/30 last:border-b-0"
							>
								<div className="mt-0.5 shrink-0">{ACTIVITY_KIND_ICON[activity.kind]}</div>
								<div className="flex-1 min-w-0">
									<p className="leading-snug line-clamp-1">{activity.text}</p>
								</div>
								<span className="text-[10px] text-muted-foreground shrink-0">
									{formatRelative(activity.timestamp)}
								</span>
							</div>
						))}
					</CardContent>
				</Card>

				{/* Last Agent Error */}
				<Card className={data.last_agent_error ? "border-rose-500/30 bg-rose-950/5" : undefined}>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm font-semibold flex items-center gap-1.5">
							<AlertCircle
								className={cn(
									"h-3.5 w-3.5",
									data.last_agent_error ? "text-rose-400" : "text-muted-foreground",
								)}
							/>
							Last Agent Error
						</CardTitle>
					</CardHeader>
					<CardContent>
						{data.last_agent_error ? (
							<div className="space-y-2">
								<div className="flex items-center gap-2">
									<Badge variant="secondary" className="text-[10px] capitalize">
										{data.last_agent_error.role.replace(/_/g, " ")}
									</Badge>
									<span className="text-[10px] text-muted-foreground">
										{formatRelative(data.last_agent_error.timestamp)}
									</span>
								</div>
								<pre className="text-[11px] text-rose-300 font-mono leading-relaxed whitespace-pre-wrap rounded border border-rose-500/30 bg-rose-950/20 p-2">
									{data.last_agent_error.message}
								</pre>
							</div>
						) : (
							<div className="text-xs text-muted-foreground py-3">No recent errors</div>
						)}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
