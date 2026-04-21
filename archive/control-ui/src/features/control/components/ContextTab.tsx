"use client";

import { AlertTriangle, Layers3, Network, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useContextInspector } from "@/lib/queries/hooks";
import { mockContextInspector } from "../mock-data";
import type { ContextInspectorResponse } from "../types";

function formatTimestamp(iso: string | null | undefined): string {
	if (!iso) return "unknown";
	const parsed = Date.parse(iso);
	if (Number.isNaN(parsed)) return iso;
	return new Date(parsed).toLocaleString();
}

export function ContextTab() {
	const query = useContextInspector();
	const data = (query.data as ContextInspectorResponse | undefined) ?? mockContextInspector;
	const sourceLayerCounts = Object.entries(data.sourceLayerCounts ?? {}).filter(
		([, count]) => count > 0,
	);

	return (
		<div className="px-6 py-4 space-y-4">
			<Card>
				<CardHeader className="pb-3">
					<div className="flex items-center justify-between gap-3">
						<div className="flex items-center gap-2">
							<Sparkles className="h-4 w-4 text-muted-foreground" />
							<CardTitle className="text-base font-semibold">Context Inspector</CardTitle>
						</div>
						<div className="flex items-center gap-2">
							<Badge variant="outline" className="text-[10px]">
								{data.stats.memoryProvider}
							</Badge>
							<Badge variant="outline" className="text-[10px] capitalize">
								KG {data.stats.kgHealth}
							</Badge>
						</div>
					</div>
				</CardHeader>
				<CardContent className="grid grid-cols-2 md:grid-cols-5 gap-3">
					{[
						{ label: "Prompt", value: data.activeSession?.promptTokens ?? 0 },
						{ label: "Completion", value: data.activeSession?.completionTokens ?? 0 },
						{ label: "Cached", value: data.activeSession?.cachedTokens ?? 0 },
						{ label: "KG Nodes", value: data.stats.kgNodeCount },
						{ label: "Context Blocks", value: data.stats.liveContextBlockCount },
					].map(({ label, value }) => (
						<div key={label}>
							<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
								{label}
							</p>
							<p className="text-lg font-bold tabular-nums">{value.toLocaleString()}</p>
						</div>
					))}
					<div className="col-span-2 md:col-span-5 text-[11px] text-muted-foreground">
						Last runtime: {formatTimestamp(data.activeSession?.updatedAt)}
					</div>
				</CardContent>
			</Card>

			{data.degradationFlags.length > 0 && (
				<div className="flex flex-wrap gap-2">
					{data.degradationFlags.map((flag) => (
						<Badge
							key={flag}
							variant="outline"
							className="border-amber-500/30 bg-amber-500/10 text-[10px] text-amber-400"
						>
							<AlertTriangle className="mr-1 h-3 w-3" />
							{flag}
						</Badge>
					))}
				</div>
			)}

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-sm flex items-center gap-1.5">
							<Layers3 className="h-3.5 w-3.5" />
							Layer Contribution
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-2">
						{sourceLayerCounts.map(([layer, count]) => (
							<div key={layer} className="flex items-center justify-between text-sm">
								<span className="text-muted-foreground">{layer.replaceAll("_", " ")}</span>
								<span className="font-mono font-semibold">{count}</span>
							</div>
						))}
					</CardContent>
				</Card>

				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-sm flex items-center gap-1.5">
							<Network className="h-3.5 w-3.5" />
							World Claims
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3">
						{data.worldClaims.length === 0 ? (
							<p className="text-xs text-muted-foreground">
								No world claims in the current runtime context.
							</p>
						) : (
							data.worldClaims.map((claim) => (
								<div key={claim.id} className="rounded border border-border/50 p-3 space-y-1">
									<div className="flex items-center justify-between gap-2">
										<p className="text-sm font-medium">{claim.title}</p>
										<Badge variant="secondary" className="text-[10px]">
											{claim.status}
										</Badge>
									</div>
									<p className="text-xs text-muted-foreground leading-relaxed">{claim.preview}</p>
									{claim.provenanceRef && (
										<p className="text-[10px] font-mono text-muted-foreground/70 truncate">
											{claim.provenanceRef}
										</p>
									)}
								</div>
							))
						)}
					</CardContent>
				</Card>
			</div>

			<Card>
				<CardHeader className="pb-3">
					<CardTitle className="text-sm">Context Blocks</CardTitle>
				</CardHeader>
				<CardContent className="space-y-3">
					{data.contextBlocks.length === 0 ? (
						<p className="text-xs text-muted-foreground">
							No context blocks recorded for the latest runtime.
						</p>
					) : (
						data.contextBlocks.map((block) => (
							<div key={block.id} className="rounded border border-border/50 p-3 space-y-2">
								<div className="flex items-center justify-between gap-2">
									<p className="text-sm font-medium">{block.title}</p>
									<div className="flex items-center gap-2">
										{block.status && (
											<Badge variant="secondary" className="text-[10px]">
												{block.status}
											</Badge>
										)}
										<span className="text-[10px] font-mono text-muted-foreground">
											{block.tokenCount ?? 0} tok
										</span>
									</div>
								</div>
								<div className="flex flex-wrap gap-1">
									{[
										block.sourceLayer,
										block.sourceType,
										block.artifactType,
										block.groundingStatus,
									].map((value) => (
										<Badge key={`${block.id}-${value}`} variant="secondary" className="text-[10px]">
											{value}
										</Badge>
									))}
								</div>
								<p className="text-xs text-muted-foreground leading-relaxed">{block.preview}</p>
								{block.provenanceRef && (
									<p className="text-[10px] font-mono text-muted-foreground/70 truncate">
										{block.provenanceRef}
									</p>
								)}
							</div>
						))
					)}
				</CardContent>
			</Card>
		</div>
	);
}
