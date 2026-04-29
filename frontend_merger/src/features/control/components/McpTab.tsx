"use client";

// McpTab — MCP server registry (exec-09)
// Slice 6.6 (NEU coverage gap): MCP Server Browser

import { CheckCircle2, Network, Plug, RefreshCw, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMcpCatalog, useMcpServers } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockMcpServers } from "../mock-data";
import type { McpServer } from "../types";

const STATUS_COLOR: Record<McpServer["status"], string> = {
	connected: "border-emerald-500/30 bg-emerald-950/10",
	disconnected: "border-amber-500/30 bg-amber-950/10",
	error: "border-rose-500/30 bg-rose-950/10",
};

export function McpTab() {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useMcpServers();
	const catalogQuery = useMcpCatalog();
	const servers = (query.data?.items as McpServer[] | undefined) ?? mockMcpServers;
	const catalog = catalogQuery.data?.items ?? [];
	const connected = servers.filter((s) => s.status === "connected").length;
	const totalTools = servers.reduce((sum, s) => sum + s.tools.length, 0);
	const visibleTools = catalog.filter((entry) => entry.visible).length;
	const blockedTools = catalog.filter((entry) => !entry.visible).length;

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">MCP Servers</h2>
					<p className="text-xs text-muted-foreground">
						{servers.length} servers · {connected} connected · {totalTools} tools exposed
						{catalog.length > 0 && ` · ${visibleTools} visible · ${blockedTools} blocked`}
					</p>
				</div>
				<Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs" disabled>
					<RefreshCw className="h-3 w-3" />
					Reconnect All
				</Button>
			</header>

			<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
				{servers.map((server) => (
					<Card key={server.id} className={cn("transition-colors", STATUS_COLOR[server.status])}>
						<CardHeader className="pb-2">
							<div className="flex items-start justify-between gap-2">
								<div className="flex items-start gap-2 flex-1 min-w-0">
									{server.status === "connected" ? (
										<CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
									) : server.status === "error" ? (
										<XCircle className="h-3.5 w-3.5 text-rose-500 mt-0.5 shrink-0" />
									) : (
										<Plug className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
									)}
									<div className="flex-1 min-w-0">
										<CardTitle className="text-sm font-semibold leading-tight">
											{server.name}
										</CardTitle>
										<code className="text-[10px] text-muted-foreground line-clamp-1">
											{server.url}
										</code>
									</div>
								</div>
								<div className="flex flex-col items-end gap-1 shrink-0">
									<Badge variant="outline" className="text-[9px] h-4 px-1.5 uppercase">
										{server.transport}
									</Badge>
									<Badge
										variant="outline"
										className={cn(
											"text-[9px] h-4 px-1.5",
											server.status === "connected"
												? "border-emerald-500/50 text-emerald-400"
												: server.status === "error"
													? "border-rose-500/50 text-rose-400"
													: "border-amber-500/50 text-amber-400",
										)}
									>
										{server.status}
									</Badge>
								</div>
							</div>
						</CardHeader>
						<CardContent className="space-y-2 pt-0">
							{server.error && <div className="text-[11px] text-rose-400">{server.error}</div>}
							<div>
								<div className="flex items-center gap-1 text-[10px] text-muted-foreground mb-1">
									<Network className="h-2.5 w-2.5" />
									{server.tools.length} tools exposed
								</div>
								<div className="flex flex-wrap gap-1">
									{server.tools.map((tool) => (
										<Badge
											key={tool}
											variant="secondary"
											className="text-[9px] h-4 px-1.5 font-mono"
										>
											{tool}
										</Badge>
									))}
								</div>
							</div>
							{server.last_ping && (
								<div className="text-[10px] text-muted-foreground">
									last ping: {new Date(server.last_ping).toLocaleTimeString()}
								</div>
							)}
						</CardContent>
					</Card>
				))}
			</div>

			<div className="rounded-lg border border-border overflow-hidden">
				<table className="w-full text-xs">
					<thead className="bg-card/40">
						<tr className="text-left">
							<th className="py-2 px-3 font-semibold">Tool</th>
							<th className="py-2 px-3 font-semibold w-28">Approval</th>
							<th className="py-2 px-3 font-semibold">Risk / Denial</th>
							<th className="py-2 px-3 font-semibold w-28">Visible</th>
						</tr>
					</thead>
					<tbody>
						{catalog.map((entry) => (
							<tr key={entry.tool.matrix_name} className="border-t border-border hover:bg-card/20">
								<td className="py-2 px-3">
									<div className="font-mono text-[11px]">{entry.tool.matrix_name}</div>
									<div className="text-[10px] text-muted-foreground line-clamp-1">
										{entry.provenance?.server_label ?? entry.server.server_id}
									</div>
								</td>
								<td className="py-2 px-3">
									<Badge variant="outline" className="text-[9px] h-4 px-1.5">
										{entry.tool.approval_level}
									</Badge>
								</td>
								<td className="py-2 px-3">
									<div className="flex flex-wrap gap-1">
										{entry.tool.risk_flags.map((flag) => (
											<Badge key={flag} variant="secondary" className="text-[9px] h-4 px-1.5">
												{flag}
											</Badge>
										))}
										{entry.denial_reasons.map((reason) => (
											<Badge
												key={reason}
												variant="outline"
												className="text-[9px] h-4 px-1.5 border-rose-500/50 text-rose-400"
											>
												{reason}
											</Badge>
										))}
									</div>
								</td>
								<td className="py-2 px-3">
									<Badge
										variant="outline"
										className={cn(
											"text-[9px] h-4 px-1.5",
											entry.visible
												? "border-emerald-500/50 text-emerald-400"
												: "border-rose-500/50 text-rose-400",
										)}
									>
										{entry.visible ? "visible" : "blocked"}
									</Badge>
								</td>
							</tr>
						))}
						{catalog.length === 0 && (
							<tr className="border-t border-border">
								<td colSpan={4} className="py-6 px-3 text-center text-muted-foreground">
									No effective MCP catalog entries
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
}
