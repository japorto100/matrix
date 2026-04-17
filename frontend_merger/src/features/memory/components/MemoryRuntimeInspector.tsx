"use client";

import { AlertTriangle, Layers3, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MemoryInspector } from "../types";

interface MemoryRuntimeInspectorProps {
	inspector?: MemoryInspector;
}

function formatTimestamp(iso: string | null | undefined): string {
	if (!iso) return "unknown";
	const parsed = Date.parse(iso);
	if (Number.isNaN(parsed)) return iso;
	return new Date(parsed).toLocaleString();
}

export function MemoryRuntimeInspector({ inspector }: MemoryRuntimeInspectorProps) {
	if (!inspector) return null;

	const activeSession = inspector.activeSession;
	const layerCounts = Object.entries(inspector.sourceLayerCounts ?? {}).filter(
		([, count]) => count > 0,
	);
	const degradationFlags = inspector.degradationFlags ?? [];
	const contextBlocks = (inspector.contextBlocks ?? []).slice(0, 3);

	if (
		!activeSession &&
		layerCounts.length === 0 &&
		degradationFlags.length === 0 &&
		contextBlocks.length === 0
	) {
		return null;
	}

	return (
		<section className="px-6 pb-2 space-y-3">
			<div className="flex items-center gap-2">
				<Sparkles className="h-4 w-4 text-muted-foreground" />
				<h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
					Runtime Context
				</h3>
			</div>

			{activeSession && (
				<Card className="border-border/50">
					<CardHeader className="pb-3">
						<CardTitle className="text-sm">Latest Runtime</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3">
						<div className="flex flex-wrap items-center gap-2">
							<Badge variant="outline" className="text-[10px]">
								{activeSession.provider || inspector.memoryProvider || "unknown"}
							</Badge>
							{activeSession.model && (
								<Badge variant="outline" className="text-[10px]">
									{activeSession.model}
								</Badge>
							)}
							{activeSession.status && (
								<Badge variant="secondary" className="text-[10px] capitalize">
									{activeSession.status}
								</Badge>
							)}
						</div>
						<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
							{[
								{ label: "Prompt", value: activeSession.promptTokens ?? 0 },
								{ label: "Completion", value: activeSession.completionTokens ?? 0 },
								{ label: "Cached", value: activeSession.cachedTokens ?? 0 },
								{ label: "Total", value: activeSession.totalTokens ?? 0 },
							].map(({ label, value }) => (
								<div key={label}>
									<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
										{label}
									</p>
									<p className="text-base font-bold tabular-nums">{value.toLocaleString()}</p>
								</div>
							))}
						</div>
						<p className="text-[11px] text-muted-foreground">
							Updated {formatTimestamp(activeSession.updatedAt)}
						</p>
					</CardContent>
				</Card>
			)}

			{degradationFlags.length > 0 && (
				<div className="flex flex-wrap gap-2">
					{degradationFlags.map((flag) => (
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

			{layerCounts.length > 0 && (
				<Card className="border-border/50">
					<CardHeader className="pb-3">
						<CardTitle className="text-sm flex items-center gap-1.5">
							<Layers3 className="h-3.5 w-3.5" />
							Layer Contribution
						</CardTitle>
					</CardHeader>
					<CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
						{layerCounts.map(([layer, count]) => (
							<div key={layer}>
								<p className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
									{layer.replaceAll("_", " ")}
								</p>
								<p className="text-base font-bold tabular-nums">{count}</p>
							</div>
						))}
					</CardContent>
				</Card>
			)}

			{contextBlocks.length > 0 && (
				<div className="grid grid-cols-1 md:grid-cols-3 gap-3">
					{contextBlocks.map((block) => (
						<Card key={block.id} className="border-border/50">
							<CardHeader className="pb-2">
								<div className="flex items-start justify-between gap-2">
									<CardTitle className="text-sm leading-tight">{block.title}</CardTitle>
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
							</CardHeader>
							<CardContent className="space-y-2">
								<div className="flex flex-wrap gap-1">
									{[block.sourceLayer, block.sourceType, block.groundingStatus].map((value) => (
										<Badge key={`${block.id}-${value}`} variant="secondary" className="text-[10px]">
											{value}
										</Badge>
									))}
								</div>
								<p className="text-xs text-muted-foreground leading-relaxed">
									{block.preview || "No preview available."}
								</p>
								{block.provenanceRef && (
									<p className="text-[10px] font-mono text-muted-foreground/70 truncate">
										{block.provenanceRef}
									</p>
								)}
							</CardContent>
						</Card>
					))}
				</div>
			)}
		</section>
	);
}
