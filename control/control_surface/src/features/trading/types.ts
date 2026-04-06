export type SidebarPanel =
	| "watchlist"
	| "indicators"
	| "news"
	| "orders"
	| "portfolio"
	| "macro"
	| "strategy"
	| "orderbook";

export interface OrderbookLevel {
	price: number;
	amount: number;
}

export interface OrderbookSnapshot {
	exchange: string;
	assetType: string;
	bids: OrderbookLevel[];
	asks: OrderbookLevel[];
}
export type WatchlistTab =
	| "all"
	| "favorites"
	| "crypto"
	| "stocks"
	| "forex"
	| "commodities"
	| "indices"
	| "macro";
export type DataMode = "api" | "fallback";
export type LayoutMode = "single" | "2h" | "2v" | "4";

export interface CompositeSignalInsights {
	signal: "buy" | "sell" | "neutral";
	confidence: number;
	heartbeatScore: number | null;
	sma50SlopeScore: number | null;
	sma50SlopeEngine: string | null;
	volumePowerScore: number | null;
	timestamp: number;
}

export interface SignalSnapshot {
	lineState: "above" | "below" | "neutral";
	sma50: number | null;
	lastCrossLabel: string;
	rvol: number | null;
	cmf: number | null;
	obv: number | null;
	heartbeatScore: number;
	heartbeatCycleBars: number | null;
	atr: number | null;
}

// Composite signal API response shapes
export interface CompositeSignalRouteComponent {
	score?: number;
	details?: Record<string, unknown>;
}

export interface CompositeSignalRouteData {
	signal?: "buy" | "sell" | "neutral";
	confidence?: number;
	components?: Record<string, CompositeSignalRouteComponent>;
	timestamp?: number;
}

export interface CompositeSignalRouteResponse {
	success?: boolean;
	data?: CompositeSignalRouteData;
	error?: string;
}
