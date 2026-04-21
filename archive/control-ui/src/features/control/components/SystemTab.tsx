"use client";

// SystemTab — Service health dashboard
// Slice 6.1: Service Status

import { AlertCircle, CheckCircle2, ExternalLink, HelpCircle, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSystemHealth } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockServices } from "../mock-data";
import type { ServiceHealth, ServiceStatus } from "../types";

const HEALTH_ICON: Record<ServiceHealth, React.ReactNode> = {
	healthy: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
	degraded: <AlertCircle className="h-3.5 w-3.5 text-amber-500" />,
	unhealthy: <XCircle className="h-3.5 w-3.5 text-rose-500" />,
	unknown: <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />,
};

const HEALTH_COLOR: Record<ServiceHealth, string> = {
	healthy: "border-emerald-500/30 bg-emerald-950/10",
	degraded: "border-amber-500/30 bg-amber-950/10",
	unhealthy: "border-rose-500/30 bg-rose-950/10",
	unknown: "border-border bg-card/40",
};

const HEALTH_BADGE: Record<ServiceHealth, string> = {
	healthy: "border-emerald-500/50 text-emerald-400",
	degraded: "border-amber-500/50 text-amber-400",
	unhealthy: "border-rose-500/50 text-rose-400",
	unknown: "border-muted-foreground/50 text-muted-foreground",
};

function formatUptime(seconds: number | undefined): string {
	if (!seconds) return "—";
	const days = Math.floor(seconds / 86400);
	const hours = Math.floor((seconds % 86400) / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	if (days > 0) return `${days}d ${hours}h`;
	if (hours > 0) return `${hours}h ${minutes}m`;
	return `${minutes}m`;
}

function ServiceCard({ service }: { service: ServiceStatus }) {
	return (
		<Card className={cn("transition-colors", HEALTH_COLOR[service.health])}>
			<CardHeader className="pb-2">
				<div className="flex items-start justify-between gap-2">
					<div className="flex items-start gap-2 flex-1 min-w-0">
						{HEALTH_ICON[service.health]}
						<div className="flex-1 min-w-0">
							<CardTitle className="text-sm font-semibold leading-tight truncate">
								{service.name}
							</CardTitle>
							<div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-muted-foreground">
								<Badge variant="outline" className="text-[9px] h-4 px-1.5 capitalize">
									{service.tier}
								</Badge>
								{service.port && <span className="font-mono">:{service.port}</span>}
								{service.version && <span>v{service.version}</span>}
							</div>
						</div>
					</div>
					<Badge
						variant="outline"
						className={cn("text-[10px] capitalize", HEALTH_BADGE[service.health])}
					>
						{service.health}
					</Badge>
				</div>
			</CardHeader>
			<CardContent className="pt-0 space-y-1">
				{service.error_message && (
					<div className="text-[11px] text-rose-400 line-clamp-2">{service.error_message}</div>
				)}
				<div className="flex items-center justify-between text-[10px] text-muted-foreground">
					<span>uptime: {formatUptime(service.uptime_s)}</span>
					{service.url && (
						<a
							href={service.url}
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 hover:text-sky-400"
						>
							<ExternalLink className="h-2.5 w-2.5" />
							open
						</a>
					)}
				</div>
			</CardContent>
		</Card>
	);
}

export function SystemTab() {
	// Slice 7 Phase H: real backend + 30s auto-refresh + mock fallback
	const { data, isError } = useSystemHealth();
	const services = (data?.items as ServiceStatus[] | undefined) ?? mockServices;
	const counts =
		(data?.counts as Record<ServiceHealth, number> | undefined) ??
		services.reduce<Record<ServiceHealth, number>>(
			(acc, s) => {
				acc[s.health] = (acc[s.health] ?? 0) + 1;
				return acc;
			},
			{ healthy: 0, degraded: 0, unhealthy: 0, unknown: 0 },
		);
	const infraServices = services.filter((s) => s.tier === "infra");
	const appServices = services.filter((s) => s.tier === "app");

	return (
		<div className="px-6 py-4 space-y-6">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">System Status</h2>
					<p className="text-xs text-muted-foreground">
						{services.length} services · {counts.healthy} healthy · {counts.degraded} degraded ·{" "}
						{counts.unhealthy} down · {counts.unknown} unknown
						{isError && <span className="ml-2 text-amber-400">· backend offline (mock data)</span>}
					</p>
				</div>
				<div className="text-[10px] text-muted-foreground">Auto-refresh every 30s</div>
			</header>

			<section className="space-y-2">
				<div className="flex items-baseline justify-between border-b border-border pb-1">
					<h3 className="text-sm font-semibold">Infrastructure</h3>
					<Badge variant="outline" className="text-[10px]">
						{infraServices.length}
					</Badge>
				</div>
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					{infraServices.map((s) => (
						<ServiceCard key={s.id} service={s} />
					))}
				</div>
			</section>

			<section className="space-y-2">
				<div className="flex items-baseline justify-between border-b border-border pb-1">
					<h3 className="text-sm font-semibold">Application</h3>
					<Badge variant="outline" className="text-[10px]">
						{appServices.length}
					</Badge>
				</div>
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					{appServices.map((s) => (
						<ServiceCard key={s.id} service={s} />
					))}
				</div>
			</section>
		</div>
	);
}
