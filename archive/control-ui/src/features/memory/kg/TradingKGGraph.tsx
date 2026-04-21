"use client";

// TradingKGGraph — react-flow visualization of the Trading Knowledge Graph
// Backend: Kuzu (memory_engine/kg_store.py). 6 typed nodes + 6 typed edges.
// K4 (Slice 4): data passed via props, owner (KGPage) wires useKgGraph hook
// with mock fallback. No more direct mockKGGraphResponse import here.

import {
	Background,
	BackgroundVariant,
	Controls,
	type Edge,
	type EdgeMarker,
	type Node,
	ReactFlow,
	ReactFlowProvider,
	useEdgesState,
	useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo } from "react";
import { TRADING_KG_NODE_TYPES, type TradingKGNodeData } from "./nodes/TradingKGNodes";
import type { KGEdge, KGNode } from "./types";
import { EDGE_STYLES, EDGE_TYPE_COLORS, getEdgeTypeLabel } from "./types";

// Simple deterministic auto-layout: place nodes by type in horizontal lanes.
// Replace with dagre / elkjs layout in Slice 4.5 for hierarchical or force-directed.
function layoutNodesByType(kgNodes: KGNode[]): Node<TradingKGNodeData>[] {
	const lanes: Record<string, KGNode[]> = {};
	for (const node of kgNodes) {
		lanes[node.type] ??= [];
		lanes[node.type]!.push(node);
	}

	const laneOrder: KGNode["type"][] = [
		"Institution",
		"TransmissionChannel",
		"Regime",
		"BTEMarker",
		"Stratagem",
		"Asset",
	];

	const nodes: Node<TradingKGNodeData>[] = [];
	const LANE_HEIGHT = 140;
	const NODE_WIDTH = 220;

	laneOrder.forEach((type, laneIdx) => {
		const inLane = lanes[type] ?? [];
		const startX = -(inLane.length * NODE_WIDTH) / 2 + NODE_WIDTH / 2;
		inLane.forEach((kgNode, i) => {
			nodes.push({
				id: kgNode.id,
				type: kgNode.type,
				position: { x: startX + i * NODE_WIDTH, y: laneIdx * LANE_HEIGHT },
				data: {
					nodeType: kgNode.type,
					label: kgNode.label,
					properties: kgNode.properties,
					confidence: kgNode.confidence,
				},
			});
		});
	});

	return nodes;
}

function toReactFlowEdges(kgEdges: KGEdge[]): Edge[] {
	return kgEdges.map((edge) => {
		const style = EDGE_STYLES[edge.type];
		const marker: EdgeMarker | undefined = style.markerEnd
			? {
					type: "arrowclosed" as never,
					color: EDGE_TYPE_COLORS[edge.type],
					width: 14,
					height: 14,
				}
			: undefined;
		return {
			id: edge.id,
			source: edge.source,
			target: edge.target,
			type: "default",
			animated: edge.type === "transmits" || edge.type === "signals",
			label: getEdgeTypeLabel(edge.type),
			labelStyle: {
				fontSize: 9,
				fill: EDGE_TYPE_COLORS[edge.type],
				fontFamily: "var(--font-mono)",
			},
			labelBgStyle: {
				fill: "var(--background)",
				fillOpacity: 0.8,
			},
			style: {
				stroke: style.stroke,
				strokeWidth: edge.weight ? 1 + edge.weight * 1.5 : 1.5,
				strokeDasharray: style.strokeDasharray,
				opacity: 0.85,
			},
			markerEnd: marker,
		};
	});
}

interface GraphImplProps {
	kgNodes: KGNode[];
	kgEdges: KGEdge[];
}

function GraphImpl({ kgNodes, kgEdges }: GraphImplProps) {
	const initialNodes = useMemo(() => layoutNodesByType(kgNodes), [kgNodes]);
	const initialEdges = useMemo(() => toReactFlowEdges(kgEdges), [kgEdges]);

	const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
	const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

	useEffect(() => {
		setNodes(initialNodes);
	}, [initialNodes, setNodes]);

	useEffect(() => {
		setEdges(initialEdges);
	}, [initialEdges, setEdges]);

	return (
		<ReactFlow
			nodes={nodes}
			edges={edges}
			onNodesChange={onNodesChange}
			onEdgesChange={onEdgesChange}
			nodeTypes={TRADING_KG_NODE_TYPES}
			fitView
			fitViewOptions={{ padding: 0.2 }}
			minZoom={0.3}
			maxZoom={2}
			proOptions={{ hideAttribution: true }}
			colorMode="dark"
		>
			<Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#2A2F36" />
			<Controls
				showInteractive={false}
				className="!bg-card !border !border-border !rounded-lg !shadow-lg"
			/>
		</ReactFlow>
	);
}

export interface TradingKGGraphProps {
	nodes: KGNode[];
	edges: KGEdge[];
}

export function TradingKGGraph({ nodes, edges }: TradingKGGraphProps) {
	return (
		<ReactFlowProvider>
			<GraphImpl kgNodes={nodes} kgEdges={edges} />
		</ReactFlowProvider>
	);
}
