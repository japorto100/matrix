// Mock Trading KG data — replace with real Kuzu CRUD endpoints in Slice 4.5
// (agent/control/kg_crud.py + GET /api/v1/control/kg/nodes + edges).
//
// Aligns with python-backend/memory_engine/seed_data.py seed structure.

import type { KGEdge, KGGraphResponse, KGNode } from "./types";

const NOW = "2026-04-07T11:00:00Z";

export const mockKGNodes: KGNode[] = [
	// ── Stratagems ─────────────────────────────────────────────────────────
	{
		id: "strat_001",
		type: "Stratagem",
		label: "Mean Reversion",
		properties: {
			timeframe: "1H-4H",
			indicator: "RSI + Bollinger Bands",
			win_rate: 0.62,
		},
		confidence: 0.88,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "strat_002",
		type: "Stratagem",
		label: "Trend Following",
		properties: {
			timeframe: "Daily",
			indicator: "EMA Crossover",
			win_rate: 0.55,
		},
		confidence: 0.92,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "strat_003",
		type: "Stratagem",
		label: "Breakout Momentum",
		properties: {
			timeframe: "15m-1H",
			indicator: "Volume Profile",
			win_rate: 0.48,
		},
		confidence: 0.71,
		created_at: NOW,
		updated_at: NOW,
	},

	// ── Regimes ────────────────────────────────────────────────────────────
	{
		id: "reg_001",
		type: "Regime",
		label: "Risk-On",
		properties: {
			vix_range: "<20",
			yields: "rising",
			equity_flows: "inflow",
		},
		confidence: 0.85,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "reg_002",
		type: "Regime",
		label: "Risk-Off",
		properties: {
			vix_range: ">25",
			yields: "falling",
			equity_flows: "outflow",
		},
		confidence: 0.85,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "reg_003",
		type: "Regime",
		label: "Stagflation",
		properties: {
			vix_range: "20-30",
			inflation: "rising",
			growth: "stalling",
		},
		confidence: 0.68,
		created_at: NOW,
		updated_at: NOW,
	},

	// ── TransmissionChannels ───────────────────────────────────────────────
	{
		id: "ch_001",
		type: "TransmissionChannel",
		label: "FOMC Statement",
		properties: { latency: "minutes", impact: "high" },
		confidence: 0.95,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "ch_002",
		type: "TransmissionChannel",
		label: "DXY Move",
		properties: { latency: "hours", impact: "medium-high" },
		confidence: 0.88,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "ch_003",
		type: "TransmissionChannel",
		label: "Bond Yields",
		properties: { latency: "minutes", impact: "high" },
		confidence: 0.91,
		created_at: NOW,
		updated_at: NOW,
	},

	// ── Assets ─────────────────────────────────────────────────────────────
	{
		id: "ast_001",
		type: "Asset",
		label: "BTC/USD",
		properties: { class: "crypto", volatility: "high" },
		confidence: 1.0,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "ast_002",
		type: "Asset",
		label: "EUR/USD",
		properties: { class: "fx", volatility: "low-medium" },
		confidence: 1.0,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "ast_003",
		type: "Asset",
		label: "SPY",
		properties: { class: "equity-etf", volatility: "low-medium" },
		confidence: 1.0,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "ast_004",
		type: "Asset",
		label: "Gold (XAU)",
		properties: { class: "commodity", volatility: "medium" },
		confidence: 1.0,
		created_at: NOW,
		updated_at: NOW,
	},

	// ── Institutions ──────────────────────────────────────────────────────
	{
		id: "inst_001",
		type: "Institution",
		label: "Federal Reserve",
		properties: { region: "US", influence: "global" },
		confidence: 1.0,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "inst_002",
		type: "Institution",
		label: "ECB",
		properties: { region: "EU", influence: "regional" },
		confidence: 1.0,
		created_at: NOW,
		updated_at: NOW,
	},

	// ── BTEMarkers (Black-Tuple-Event markers) ────────────────────────────
	{
		id: "bte_001",
		type: "BTEMarker",
		label: "Volatility Spike",
		properties: { trigger: "VIX > 30 for 3d", severity: "high" },
		confidence: 0.78,
		created_at: NOW,
		updated_at: NOW,
	},
	{
		id: "bte_002",
		type: "BTEMarker",
		label: "Flash Crash Pattern",
		properties: { trigger: "5% drop in 1h", severity: "critical" },
		confidence: 0.82,
		created_at: NOW,
		updated_at: NOW,
	},
];

export const mockKGEdges: KGEdge[] = [
	// Stratagem ↔ Regime relations (inhibits)
	{ id: "e1", source: "reg_002", target: "strat_001", type: "inhibits", weight: 0.7 },
	{ id: "e2", source: "reg_001", target: "strat_002", type: "activates", weight: 0.85 },
	{ id: "e3", source: "reg_003", target: "strat_002", type: "inhibits", weight: 0.6 },
	{ id: "e4", source: "reg_001", target: "strat_003", type: "activates", weight: 0.7 },

	// Channel → Regime causation
	{ id: "e5", source: "ch_001", target: "reg_001", type: "causes", weight: 0.65 },
	{ id: "e6", source: "ch_001", target: "reg_002", type: "causes", weight: 0.65 },
	{ id: "e7", source: "ch_003", target: "reg_002", type: "causes", weight: 0.78 },

	// Institution → Channel
	{ id: "e8", source: "inst_001", target: "ch_001", type: "transmits", weight: 1.0 },
	{ id: "e9", source: "inst_001", target: "ch_003", type: "transmits", weight: 0.9 },
	{ id: "e10", source: "inst_002", target: "ch_001", type: "transmits", weight: 0.5 },

	// Channel → Asset signals
	{ id: "e11", source: "ch_002", target: "ast_002", type: "signals", weight: 0.85 },
	{ id: "e12", source: "ch_002", target: "ast_004", type: "signals", weight: 0.78 },
	{ id: "e13", source: "ch_003", target: "ast_003", type: "signals", weight: 0.72 },
	{ id: "e14", source: "ch_001", target: "ast_001", type: "signals", weight: 0.55 },

	// BTE Markers precede Regimes
	{ id: "e15", source: "bte_001", target: "reg_002", type: "precedes", weight: 0.88 },
	{ id: "e16", source: "bte_002", target: "reg_002", type: "precedes", weight: 0.92 },

	// Stratagem → Asset (which assets each strat trades)
	{ id: "e17", source: "strat_001", target: "ast_002", type: "transmits", weight: 0.6 },
	{ id: "e18", source: "strat_002", target: "ast_003", type: "transmits", weight: 0.8 },
	{ id: "e19", source: "strat_003", target: "ast_001", type: "transmits", weight: 0.7 },
];

export const mockKGGraphResponse: KGGraphResponse = {
	nodes: mockKGNodes,
	edges: mockKGEdges,
	total_nodes: mockKGNodes.length,
	total_edges: mockKGEdges.length,
};

// ── Backend Adapter ─────────────────────────────────────────────────────────
// K4 (Slice 4): The backend /api/v1/control/kg/graph response uses a looser
// shape than the frontend KGGraphResponse (e.g., Kuzu may return {id, name,
// node_type} without confidence/timestamps). Map to the strict frontend shape,
// filling sensible defaults. If the response is empty or malformed we return
// null and callers fall back to mockKGGraphResponse.

type RawKgNode = {
	id?: string;
	type?: string;
	_type?: string;
	node_type?: string;
	label?: string;
	name?: string;
	properties?: Record<string, unknown>;
	confidence?: number;
	created_at?: string;
	updated_at?: string;
	[k: string]: unknown;
};

type RawKgEdge = {
	id?: string;
	source?: string;
	target?: string;
	from_id?: string;
	to_id?: string;
	type?: string;
	edge_type?: string;
	weight?: number;
	properties?: Record<string, unknown>;
};

const ALLOWED_NODE_TYPES = new Set<KGNode["type"]>([
	"Stratagem",
	"Regime",
	"TransmissionChannel",
	"Asset",
	"Institution",
	"BTEMarker",
]);

const ALLOWED_EDGE_TYPES = new Set<KGEdge["type"]>([
	"causes",
	"inhibits",
	"activates",
	"precedes",
	"transmits",
	"signals",
]);

export function adaptKgGraphResponse(
	raw:
		| {
				nodes?: unknown[];
				edges?: unknown[];
				total_nodes?: number;
				total_edges?: number;
		  }
		| null
		| undefined,
): KGGraphResponse | null {
	if (!raw || !Array.isArray(raw.nodes)) return null;
	const now = new Date().toISOString();

	const nodes: KGNode[] = [];
	for (const item of raw.nodes as RawKgNode[]) {
		if (!item || typeof item !== "object") continue;
		const rawType = (item.type ?? item._type ?? item.node_type) as string | undefined;
		if (!rawType || !ALLOWED_NODE_TYPES.has(rawType as KGNode["type"])) continue;
		const id = item.id;
		if (typeof id !== "string" || !id) continue;
		const label = item.label ?? item.name ?? id;
		nodes.push({
			id,
			type: rawType as KGNode["type"],
			label: String(label),
			properties: (item.properties as KGNode["properties"]) ?? {},
			confidence: typeof item.confidence === "number" ? item.confidence : 0.5,
			created_at: item.created_at ?? now,
			updated_at: item.updated_at ?? now,
		});
	}

	if (nodes.length === 0) return null;

	const edges: KGEdge[] = [];
	for (const item of (raw.edges ?? []) as RawKgEdge[]) {
		if (!item || typeof item !== "object") continue;
		const source = item.source ?? item.from_id;
		const target = item.target ?? item.to_id;
		const rawType = item.type ?? item.edge_type;
		if (typeof source !== "string" || typeof target !== "string" || typeof rawType !== "string") {
			continue;
		}
		if (!ALLOWED_EDGE_TYPES.has(rawType as KGEdge["type"])) continue;
		edges.push({
			id: item.id ?? `${source}-${target}-${rawType}`,
			source,
			target,
			type: rawType as KGEdge["type"],
			weight: item.weight,
			properties: item.properties as KGEdge["properties"],
		});
	}

	return {
		nodes,
		edges,
		total_nodes: raw.total_nodes ?? nodes.length,
		total_edges: raw.total_edges ?? edges.length,
	};
}
