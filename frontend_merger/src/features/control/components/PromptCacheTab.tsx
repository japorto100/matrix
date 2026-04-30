"use client";

import { AlertTriangle, DatabaseZap, ExternalLink, Gauge, Hash, TimerReset } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePromptCache } from "@/lib/queries/hooks";
import { mockPromptCacheReadModel } from "../mock-data";
import type { PromptCacheTrace } from "../types";

function formatNumber(value?: number | null): string {
	if (typeof value !== "number") return "unknown";
	return value.toLocaleString();
}

function shortDigest(value: string): string {
	return value ? value.slice(0, 10) : "n/a";
}

function cacheHitRatio(item: PromptCacheTrace): number {
	const prompt = item.usage.prompt_tokens ?? 0;
	const read = item.usage.cache_read_tokens ?? 0;
	if (!prompt) return 0;
	return Math.round((read / prompt) * 100);
}

export function PromptCacheTab() {
	const searchParams = useSearchParams();
	const threadFilter = searchParams.get("thread_id") ?? "";
	const query = usePromptCache();
	const data = query.data ?? mockPromptCacheReadModel;
	const traces = threadFilter
		? data.items.filter((item) => item.thread_id === threadFilter)
		: data.items;

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-base font-semibold">Prompt Cache</h2>
					<p className="text-xs text-muted-foreground">
						{traces.length} requests · {formatNumber(data.summary.cache_read_tokens)} read ·{" "}
						{formatNumber(data.summary.cache_write_tokens)} write tokens
					</p>
				</div>
				<Badge variant="outline" className="h-6 px-2 text-[10px]">
					{data.contract}
				</Badge>
			</header>

			<div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Requests</span>
						<Gauge className="h-3.5 w-3.5 text-sky-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{data.summary.requests}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Cache Read</span>
						<DatabaseZap className="h-3.5 w-3.5 text-emerald-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{formatNumber(data.summary.cache_read_tokens)}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Cache Write</span>
						<TimerReset className="h-3.5 w-3.5 text-amber-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{formatNumber(data.summary.cache_write_tokens)}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Breaks</span>
						<AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{data.summary.cache_breaks}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Unknown Cache</span>
						<Hash className="h-3.5 w-3.5 text-muted-foreground" />
					</div>
					<div className="mt-2 text-lg font-semibold">{data.summary.unknown_cache_fields}</div>
				</div>
			</div>

			<div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-sm">Recent Request Traces</CardTitle>
					</CardHeader>
					<CardContent className="overflow-x-auto">
						<table className="w-full min-w-[980px] text-xs">
							<thead>
								<tr className="border-b border-border text-left text-[10px] uppercase text-muted-foreground/70">
									<th className="py-2 pr-3">When</th>
									<th className="py-2 pr-3">Provider</th>
									<th className="py-2 pr-3">Model</th>
									<th className="py-2 pr-3">Cache</th>
									<th className="py-2 pr-3">Tokens</th>
									<th className="py-2 pr-3">Digests</th>
									<th className="py-2 pr-3">Links</th>
								</tr>
							</thead>
							<tbody>
								{traces.map((trace) => (
									<tr key={trace.event_id} className="border-b border-border/50">
										<td className="py-2 pr-3 font-mono text-[11px]">{trace.timestamp}</td>
										<td className="py-2 pr-3">{trace.provider || "unknown"}</td>
										<td className="py-2 pr-3 font-mono">{trace.model || "unknown"}</td>
										<td className="py-2 pr-3">
											<div className="flex flex-wrap gap-1">
												<Badge variant="outline" className="h-5 px-1.5 text-[10px]">
													read {formatNumber(trace.usage.cache_read_tokens)}
												</Badge>
												<Badge variant="outline" className="h-5 px-1.5 text-[10px]">
													{cacheHitRatio(trace)}%
												</Badge>
											</div>
										</td>
										<td className="py-2 pr-3">{formatNumber(trace.usage.total_tokens)} total</td>
										<td className="py-2 pr-3 font-mono text-[10px]">
											{shortDigest(trace.prompt_digest)} · {shortDigest(trace.tool_catalog_digest)}
										</td>
										<td className="py-2 pr-3">
											<div className="flex flex-wrap gap-1">
												<Link href={trace.links.ops_event}>
													<Badge variant="outline" className="h-5 gap-1 px-1.5 text-[10px]">
														<ExternalLink className="h-3 w-3" />
														Ops
													</Badge>
												</Link>
												<Link href={trace.links.context}>
													<Badge variant="outline" className="h-5 gap-1 px-1.5 text-[10px]">
														<ExternalLink className="h-3 w-3" />
														Context
													</Badge>
												</Link>
											</div>
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</CardContent>
				</Card>

				<div className="space-y-4">
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-sm">Break Reasons</CardTitle>
						</CardHeader>
						<CardContent className="flex flex-wrap gap-1.5">
							{Object.entries(data.cache_break_reasons).length === 0 ? (
								<Badge variant="outline" className="h-5 px-1.5 text-[10px]">
									no breaks
								</Badge>
							) : (
								Object.entries(data.cache_break_reasons).map(([reason, count]) => (
									<Badge key={reason} variant="outline" className="h-5 px-1.5 text-[10px]">
										{reason} {count}
									</Badge>
								))
							)}
						</CardContent>
					</Card>
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-sm">Providers</CardTitle>
						</CardHeader>
						<CardContent className="space-y-2">
							{Object.entries(data.by_provider).map(([provider, count]) => (
								<div
									key={provider}
									className="flex items-center justify-between rounded border border-border/50 px-2 py-1.5 text-xs"
								>
									<span className="truncate">{provider}</span>
									<Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
										{count}
									</Badge>
								</div>
							))}
						</CardContent>
					</Card>
				</div>
			</div>
		</div>
	);
}
