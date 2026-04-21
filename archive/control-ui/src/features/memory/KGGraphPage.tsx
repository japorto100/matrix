"use client";

// KGGraphPage — Episode-Memory Provenance visualization
// Uses MemoryGraph component from @/lib/kg-graph (1:1 adopted from
// _ref/supermemory/packages/memory-graph). K4 (Slice 4): also calls
// useKgGraph() so the backend cache is warm and the badge can reflect
// backend availability — but the actual `documents` shape (memory-graph
// format) is distinct from the Trading KG nodes/edges shape, so the
// rendering still uses generateMockGraphData. Unifying both graphs into
// one feed is a Phase 2 task.

import { Network, RefreshCw } from "lucide-react";
import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MemoryGraph } from "@/lib/kg-graph";
import { generateMockGraphData } from "@/lib/kg-graph/mock-data";
import { useKgGraph } from "@/lib/queries/hooks";

export function KGGraphPage() {
	// Warm the cache so the Trading KG tab can reuse it; shape is different
	// so we still render mock documents here.
	const query = useKgGraph();

	const { documents } = useMemo(
		() => generateMockGraphData({ documentCount: 30, memoriesPerDoc: [1, 4], seed: 42 }),
		[],
	);

	const totalNodes = documents.reduce((sum, doc) => sum + 1 + (doc.memories?.length ?? 0), 0);
	const totalEdges = documents.reduce((sum, doc) => sum + (doc.memories?.length ?? 0), 0);
	const backendNodeCount =
		query.data && Array.isArray(query.data.nodes) ? query.data.nodes.length : null;

	return (
		<div className="flex flex-col h-[calc(100vh-2.5rem)]">
			{/* Header bar */}
			<div className="flex items-center justify-between gap-4 px-6 py-3 border-b border-border bg-card/30 shrink-0">
				<div className="flex items-center gap-3">
					<div className="rounded-md bg-accent/40 p-1.5">
						<Network className="h-4 w-4 text-foreground" />
					</div>
					<div>
						<h1 className="text-sm font-semibold">Knowledge Graph</h1>
						<p className="text-[10px] text-muted-foreground font-mono">
							Stratagems · Regimes · Channels · Assets · Institutions · BTE Markers
						</p>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<Badge variant="outline" className="font-mono text-[10px]">
						{documents.length} documents
					</Badge>
					<Badge variant="outline" className="font-mono text-[10px]">
						{totalNodes} nodes
					</Badge>
					<Badge variant="outline" className="font-mono text-[10px]">
						{totalEdges} edges
					</Badge>
					{backendNodeCount !== null && (
						<Badge variant="outline" className="font-mono text-[10px] text-emerald-400">
							backend: {backendNodeCount} KG nodes
						</Badge>
					)}
					<Button
						variant="outline"
						size="sm"
						className="h-7 gap-1.5"
						onClick={() => query.refetch()}
						disabled={query.isFetching}
					>
						<RefreshCw className={`h-3 w-3 ${query.isFetching ? "animate-spin" : ""}`} />
						<span className="text-[11px]">Reload</span>
					</Button>
				</div>
			</div>

			{/* Graph canvas */}
			<div className="flex-1 relative overflow-hidden">
				<MemoryGraph documents={documents} variant="console" maxNodes={200} showFps={false} />
			</div>
		</div>
	);
}
