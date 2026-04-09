// Trading Knowledge Graph types — mirrors python-backend/memory_engine/kg_store.py
// + memory_engine/seed_data.py node/edge schemas (exec-11).
// 6 typed entity classes + 6 typed semantic edges.

export type KGNodeType =
	| "Stratagem"
	| "Regime"
	| "TransmissionChannel"
	| "Asset"
	| "Institution"
	| "BTEMarker";

export type KGEdgeType = "causes" | "inhibits" | "activates" | "precedes" | "transmits" | "signals";

export interface KGNodeProperties {
	[key: string]: string | number | boolean | null;
}

export interface KGNode {
	id: string;
	type: KGNodeType;
	label: string;
	properties: KGNodeProperties;
	confidence: number; // 0..1
	created_at: string;
	updated_at: string;
}

export interface KGEdge {
	id: string;
	source: string; // KGNode.id
	target: string; // KGNode.id
	type: KGEdgeType;
	weight?: number; // 0..1, edge strength
	properties?: KGNodeProperties;
}

export interface KGGraphResponse {
	nodes: KGNode[];
	edges: KGEdge[];
	total_nodes: number;
	total_edges: number;
}

export interface KGStats {
	by_type: Record<KGNodeType, number>;
	by_edge: Record<KGEdgeType, number>;
	total_nodes: number;
	total_edges: number;
	last_updated: string;
}

// ── UI Display Helpers ────────────────────────────────────────────────────

export const NODE_TYPE_COLORS: Record<KGNodeType, string> = {
	Stratagem: "#3B73B8", // blue
	Regime: "#A78BFA", // violet
	TransmissionChannel: "#38BDF8", // cyan
	Asset: "#10B981", // green
	Institution: "#94A3B8", // slate gray
	BTEMarker: "#EF4444", // red
};

export const EDGE_TYPE_COLORS: Record<KGEdgeType, string> = {
	causes: "#EF4444", // red — strong directional
	inhibits: "#F59E0B", // amber — opposition
	activates: "#10B981", // green — positive
	precedes: "#3B73B8", // blue — temporal
	transmits: "#38BDF8", // cyan — flow
	signals: "#A78BFA", // violet — signal
};

export const EDGE_STYLES: Record<
	KGEdgeType,
	{ stroke: string; strokeDasharray?: string; markerEnd?: boolean }
> = {
	causes: { stroke: "#EF4444", markerEnd: true },
	inhibits: { stroke: "#F59E0B", strokeDasharray: "5 3", markerEnd: true },
	activates: { stroke: "#10B981", strokeDasharray: "1 3", markerEnd: true },
	precedes: { stroke: "#3B73B8", markerEnd: true },
	transmits: { stroke: "#38BDF8", markerEnd: false },
	signals: { stroke: "#A78BFA", markerEnd: true },
};

export function getNodeTypeIcon(type: KGNodeType): string {
	const map: Record<KGNodeType, string> = {
		Stratagem: "S",
		Regime: "R",
		TransmissionChannel: "C",
		Asset: "A",
		Institution: "I",
		BTEMarker: "B",
	};
	return map[type];
}

export function getNodeTypeLabel(type: KGNodeType): string {
	const map: Record<KGNodeType, string> = {
		Stratagem: "Stratagem",
		Regime: "Regime",
		TransmissionChannel: "Channel",
		Asset: "Asset",
		Institution: "Institution",
		BTEMarker: "BTE Marker",
	};
	return map[type];
}

export function getEdgeTypeLabel(type: KGEdgeType): string {
	const map: Record<KGEdgeType, string> = {
		causes: "causes",
		inhibits: "inhibits",
		activates: "activates",
		precedes: "precedes",
		transmits: "transmits",
		signals: "signals",
	};
	return map[type];
}
