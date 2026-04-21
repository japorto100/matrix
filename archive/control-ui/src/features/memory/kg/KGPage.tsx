"use client";

// KGPage — Trading Knowledge Graph Visualization
// Route: /memory/kg
// Backend: Kuzu (memory_engine/kg_store.py) via /api/v1/control/kg/graph (K4).
// Visualization: react-flow with 6 custom typed node components.

import { Network, RefreshCw, Search } from "lucide-react";
import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useKgGraph } from "@/lib/queries/hooks";
import { KGLegend } from "./KGLegend";
import { adaptKgGraphResponse, mockKGGraphResponse } from "./mock-data";
import { TradingKGGraph } from "./TradingKGGraph";

export function KGPage() {
	const query = useKgGraph();
	const graphData = useMemo(() => {
		const adapted = adaptKgGraphResponse(query.data);
		return adapted ?? mockKGGraphResponse;
	}, [query.data]);

	const { total_nodes, total_edges, nodes, edges } = graphData;

	const nodeTypeCounts = nodes.reduce(
		(acc, n) => {
			acc[n.type] = (acc[n.type] ?? 0) + 1;
			return acc;
		},
		{} as Record<string, number>,
	);

	const isMock = graphData === mockKGGraphResponse;

	return (
		<div className="flex flex-col h-[calc(100vh-2.5rem)]">
			{/* Header */}
			<div className="flex items-center justify-between gap-4 px-6 py-3 border-b border-border bg-card/30 shrink-0">
				<div className="flex items-center gap-3">
					<div className="rounded-md bg-accent/40 p-1.5">
						<Network className="h-4 w-4 text-foreground" />
					</div>
					<div>
						<h1 className="text-sm font-semibold">Trading Knowledge Graph</h1>
						<p className="text-[10px] text-muted-foreground font-mono">
							6 typed entities · 6 semantic edges · Kuzu backend
						</p>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<div className="relative">
						<Search className="h-3 w-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
						<Input placeholder="Search nodes..." className="h-8 w-48 pl-7 text-xs" />
					</div>
					<Badge variant="outline" className="font-mono text-[10px]">
						{total_nodes} nodes
					</Badge>
					<Badge variant="outline" className="font-mono text-[10px]">
						{total_edges} edges
					</Badge>
					{isMock && (
						<Badge variant="outline" className="font-mono text-[10px] text-amber-400">
							mock
						</Badge>
					)}
					<Button
						variant="outline"
						size="sm"
						className="h-8 gap-1.5"
						onClick={() => query.refetch()}
						disabled={query.isFetching}
					>
						<RefreshCw className={`h-3 w-3 ${query.isFetching ? "animate-spin" : ""}`} />
						<span className="text-[11px]">Reload</span>
					</Button>
				</div>
			</div>

			{/* Type breakdown bar */}
			<div className="flex items-center gap-3 px-6 py-2 border-b border-border/30 bg-card/20 shrink-0 overflow-x-auto">
				{Object.entries(nodeTypeCounts).map(([type, count]) => (
					<div key={type} className="flex items-center gap-1.5 shrink-0">
						<span className="text-[10px] text-muted-foreground">{type}</span>
						<span className="text-[10px] font-mono font-bold">{count}</span>
					</div>
				))}
			</div>

			{/* Canvas with legend overlay */}
			<div className="flex-1 relative bg-background">
				<TradingKGGraph nodes={nodes} edges={edges} />
				<KGLegend />
			</div>
		</div>
	);
}
