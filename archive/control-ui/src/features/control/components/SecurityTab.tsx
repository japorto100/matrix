"use client";

// SecurityTab — TT8 User Mode + Dev Mode
// Posture Score (4 Pillars) + Recent Security Events + Access List

import {
	AlertCircle,
	CheckCircle2,
	Globe,
	Info,
	KeyRound,
	Lock,
	Monitor,
	Shield,
	ShieldAlert,
	ShieldCheck,
	XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSecurityPosture } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockSecurity } from "../mock-data";
import type {
	SecurityEventType,
	SecurityPillarStatus,
	SecurityPosture,
	SecuritySeverity,
} from "../types";

const STATUS_COLOR: Record<SecurityPillarStatus, string> = {
	good: "border-emerald-500/30 bg-emerald-950/10",
	warning: "border-amber-500/30 bg-amber-950/10",
	critical: "border-rose-500/30 bg-rose-950/10",
};

const STATUS_ICON: Record<SecurityPillarStatus, React.ReactNode> = {
	good: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
	warning: <AlertCircle className="h-3.5 w-3.5 text-amber-500" />,
	critical: <XCircle className="h-3.5 w-3.5 text-rose-500" />,
};

const PILLAR_ICON: Record<string, React.ReactNode> = {
	Authentication: <KeyRound className="h-3.5 w-3.5" />,
	Encryption: <Lock className="h-3.5 w-3.5" />,
	Audit: <Shield className="h-3.5 w-3.5" />,
	Network: <Globe className="h-3.5 w-3.5" />,
};

const EVENT_TYPE_LABEL: Record<SecurityEventType, string> = {
	login: "Login",
	role_change: "Role Change",
	sensitive_tool_call: "Sensitive Tool",
	policy_change: "Policy Change",
	audit_export: "Audit Export",
	permission_change: "Permission Change",
};

const SEVERITY_COLOR: Record<SecuritySeverity, string> = {
	info: "border-sky-500/50 text-sky-400",
	warning: "border-amber-500/50 text-amber-400",
	critical: "border-rose-500/50 text-rose-400",
};

const SEVERITY_ICON: Record<SecuritySeverity, React.ReactNode> = {
	info: <Info className="h-3 w-3" />,
	warning: <AlertCircle className="h-3 w-3" />,
	critical: <ShieldAlert className="h-3 w-3" />,
};

function formatRelative(iso: string | null | undefined): string {
	if (!iso) return "—";
	const parsed = new Date(iso).getTime();
	if (Number.isNaN(parsed)) return "—";
	const diffMs = Date.now() - parsed;
	const minutes = Math.floor(diffMs / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}

function scoreColor(score: number): string {
	if (score >= 90) return "text-emerald-400";
	if (score >= 70) return "text-amber-400";
	return "text-rose-400";
}

export function SecurityTab() {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useSecurityPosture();
	const data = (query.data as SecurityPosture | undefined) ?? mockSecurity;

	return (
		<div className="px-6 py-4 space-y-4">
			{/* Overall Score Hero */}
			<Card>
				<CardHeader className="pb-3">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-2">
							<ShieldCheck className="h-5 w-5 text-emerald-400" />
							<CardTitle className="text-base font-semibold">Security Posture</CardTitle>
						</div>
						<div className={cn("text-3xl font-bold tabular-nums", scoreColor(data.overall_score))}>
							{data.overall_score}
							<span className="text-sm text-muted-foreground font-normal">/100</span>
						</div>
					</div>
				</CardHeader>
				<CardContent>
					<div className="h-2 rounded-full bg-card/60 overflow-hidden">
						<div
							className={cn(
								"h-full transition-all",
								data.overall_score >= 90
									? "bg-emerald-500"
									: data.overall_score >= 70
										? "bg-amber-500"
										: "bg-rose-500",
							)}
							style={{ width: `${data.overall_score}%` }}
						/>
					</div>
				</CardContent>
			</Card>

			{/* 4 Pillars */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
				{data.pillars.map((pillar) => (
					<Card key={pillar.name} className={cn("transition-colors", STATUS_COLOR[pillar.status])}>
						<CardHeader className="pb-2">
							<div className="flex items-center justify-between gap-2">
								<div className="flex items-center gap-1.5">
									{PILLAR_ICON[pillar.name] ?? <Shield className="h-3.5 w-3.5" />}
									<CardTitle className="text-sm font-semibold">{pillar.name}</CardTitle>
								</div>
								{STATUS_ICON[pillar.status]}
							</div>
						</CardHeader>
						<CardContent className="space-y-2">
							<div className={cn("text-2xl font-bold tabular-nums", scoreColor(pillar.score))}>
								{pillar.score}
								<span className="text-xs text-muted-foreground font-normal">/100</span>
							</div>
							<p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-3">
								{pillar.message}
							</p>
						</CardContent>
					</Card>
				))}
			</div>

			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				{/* Recent Events */}
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm font-semibold">Recent Security Events</CardTitle>
					</CardHeader>
					<CardContent className="space-y-2">
						{data.recent_events.map((event) => (
							<div
								key={event.timestamp}
								className="flex items-start gap-2 text-xs py-2 border-b border-border/30 last:border-b-0"
							>
								<div className="mt-0.5 shrink-0">{SEVERITY_ICON[event.severity]}</div>
								<div className="flex-1 min-w-0 space-y-1">
									<div className="flex items-center gap-2 flex-wrap">
										<Badge
											variant="outline"
											className={cn("text-[9px] h-4 px-1.5", SEVERITY_COLOR[event.severity])}
										>
											{EVENT_TYPE_LABEL[event.type]}
										</Badge>
										<span className="text-[10px] text-muted-foreground">
											{event.actor} · {formatRelative(event.timestamp)}
										</span>
									</div>
									<p className="leading-snug line-clamp-2">{event.description}</p>
								</div>
							</div>
						))}
						{data.recent_events.length === 0 && (
							<div className="text-xs text-muted-foreground py-3">No recent events</div>
						)}
					</CardContent>
				</Card>

				{/* Access List */}
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm font-semibold">Access List</CardTitle>
					</CardHeader>
					<CardContent className="space-y-2">
						{data.access_list.map((entry) => (
							<div
								key={entry.session_id}
								className="flex items-start gap-2 text-xs py-2 border-b border-border/30 last:border-b-0"
							>
								<Monitor className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
								<div className="flex-1 min-w-0">
									<div className="flex items-center gap-2">
										<code className="font-mono text-[11px]">{entry.ip}</code>
										<span className="text-[10px] text-muted-foreground">
											last seen {formatRelative(entry.last_seen)}
										</span>
									</div>
									<p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
										{entry.user_agent}
									</p>
								</div>
							</div>
						))}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
