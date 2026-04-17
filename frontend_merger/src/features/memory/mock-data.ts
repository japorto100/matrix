// Mock data for Memory Surface — used until Slice 2/3 backend (agent/control/) lands.
// Replace with real fetch() calls in Slice 3.5 (BFF wiring).

import type {
	Episode,
	MemoryLayer,
	MemoryOverviewResponse,
	TimelineMarker,
	TimelineResponse,
} from "./types";

export const mockMemoryOverview: MemoryOverviewResponse = {
	layers: [
		{
			type: "episodic",
			provider: "sqlite",
			health: "ok",
			item_count: 1247,
			last_sync_at: "2026-04-07T10:30:00Z",
			consolidation_pending: 3,
		},
		{
			type: "kg",
			provider: "kuzu",
			health: "ok",
			item_count: 184,
			last_sync_at: "2026-04-07T10:25:00Z",
			consolidation_pending: 0,
		},
		{
			type: "vector",
			provider: "chroma",
			health: "degraded",
			item_count: 5421,
			last_sync_at: "2026-04-06T22:14:00Z",
			consolidation_pending: 12,
		},
	],
};

const NOW = Date.parse("2026-04-07T11:00:00Z");
function isoOffset(minutesAgo: number): string {
	return new Date(NOW - minutesAgo * 60_000).toISOString();
}

export const mockEpisodes: Episode[] = [
	{
		id: "ep_001",
		session_id: "sess_a1b2",
		user_id: "local",
		agent_role: "researcher",
		input: "Analyze BTC/USD volatility regime over the last 90 days",
		output:
			"Looking at BTC/USD over 90 days, we see a clear shift from low-volatility consolidation (Jan-Feb) into a high-volatility expansion phase from March onward. **Key findings:**\n\n- ATR-14 jumped from $1,200 to $3,800\n- Realized volatility doubled from 42% to 85% annualized\n- Volume profile shows accumulation at $89k support",
		tools_used: ["sandbox_execute", "memory_search", "get_chart_state"],
		duration_ms: 18420,
		token_count: 4231,
		confidence: 0.91,
		tags: ["btc", "volatility", "regime-analysis"],
		created_at: isoOffset(15),
		retain_until: null,
	},
	{
		id: "ep_002",
		session_id: "sess_a1b2",
		user_id: "local",
		agent_role: "technical_analyst",
		input: "What's the RSI divergence pattern on EUR/USD daily chart?",
		output:
			"Bearish divergence forming on EUR/USD daily — price made higher high at 1.0892 but RSI made lower high (68 vs 73). This is a classic Wyckoff distribution pattern.",
		tools_used: ["get_chart_state", "sandbox_execute"],
		duration_ms: 8900,
		token_count: 2148,
		confidence: 0.78,
		tags: ["eurusd", "rsi", "divergence"],
		created_at: isoOffset(42),
		retain_until: null,
	},
	{
		id: "ep_003",
		session_id: "sess_c3d4",
		user_id: "local",
		agent_role: "fundamentals_analyst",
		input: "Check NVDA's P/E vs sector median",
		output:
			"NVDA P/E currently 47.2 vs semiconductor sector median 28.1. Premium of 68%, justified by earnings growth (+89% YoY) but elevated risk if AI capex slows.",
		tools_used: ["portfolio_summary", "memory_add"],
		duration_ms: 12100,
		token_count: 1842,
		confidence: 0.85,
		tags: ["nvda", "valuation", "pe-ratio"],
		created_at: isoOffset(67),
		retain_until: null,
	},
	{
		id: "ep_004",
		session_id: "sess_c3d4",
		user_id: "local",
		agent_role: "risk_manager",
		input: "Approve or deny the proposed long position on TSLA",
		output:
			"**DENIED.** Position size 8% of portfolio exceeds risk policy (max 5% per single name). Drawdown scenarios:\n\n- 1-sigma: -$4,200\n- 2-sigma: -$8,400\n\nRecommend reducing to 4% or splitting across TSLA + RIVN.",
		tools_used: ["portfolio_summary"],
		duration_ms: 3200,
		token_count: 980,
		confidence: 0.94,
		tags: ["tsla", "risk", "position-sizing", "denied"],
		created_at: isoOffset(98),
		retain_until: null,
	},
	{
		id: "ep_005",
		session_id: "sess_e5f6",
		user_id: "local",
		agent_role: "sentiment_analyst",
		input: "Twitter sentiment for $SPY this week",
		output:
			"$SPY twitter sentiment: 42% bullish, 31% bearish, 27% neutral. Sentiment ratio dropped from 1.8 → 1.35 over the week.",
		tools_used: ["sandbox_browser", "memory_search"],
		duration_ms: 24800,
		token_count: 3120,
		confidence: 0.62,
		tags: ["spy", "sentiment", "twitter"],
		created_at: isoOffset(135),
		retain_until: null,
	},
	{
		id: "ep_006",
		session_id: "sess_e5f6",
		user_id: "local",
		agent_role: "trader",
		input: "Set up a swing trade entry at EUR/USD 1.0850",
		output:
			"Entry order placed:\n- Symbol: EUR/USD\n- Side: Long\n- Entry: 1.0850\n- Stop: 1.0820 (-30 pips)\n- Target 1: 1.0905 (+55 pips, R:R 1.83)\n- Target 2: 1.0960 (+110 pips, R:R 3.67)",
		tools_used: ["set_chart_state"],
		duration_ms: 5400,
		token_count: 1520,
		confidence: 0.88,
		tags: ["eurusd", "swing", "long-entry"],
		created_at: isoOffset(180),
		retain_until: null,
	},
	{
		id: "ep_007",
		session_id: "sess_g7h8",
		user_id: "local",
		agent_role: "researcher",
		input: "What macro events are scheduled for next week?",
		output:
			"Next week macro calendar:\n- **Mon:** ISM Manufacturing PMI (US, 9:45 ET)\n- **Wed:** FOMC Minutes (US, 14:00 ET)\n- **Thu:** ECB rate decision (08:15 ET)\n- **Fri:** NFP report (US, 08:30 ET)",
		tools_used: ["sandbox_browser"],
		duration_ms: 14200,
		token_count: 2840,
		confidence: 0.96,
		tags: ["macro", "calendar", "fomc", "ecb", "nfp"],
		created_at: isoOffset(245),
		retain_until: null,
	},
	{
		id: "ep_008",
		session_id: "sess_g7h8",
		user_id: "local",
		agent_role: "fundamentals_analyst",
		input: "Pull the latest 10-Q filing for AAPL",
		output:
			"AAPL 10-Q (Q1 FY26) summary:\n- Revenue: $124.3B (+4% YoY)\n- iPhone revenue: $69.7B (+1.8%)\n- Services: $26.3B (+14%)\n- Net income: $36.3B\n- Cash + securities: $173B",
		tools_used: ["sandbox_execute", "file_analyze"],
		duration_ms: 32100,
		token_count: 5240,
		confidence: 0.89,
		tags: ["aapl", "10q", "earnings"],
		created_at: isoOffset(310),
		retain_until: null,
	},
	{
		id: "ep_009",
		session_id: "sess_i9j0",
		user_id: "local",
		agent_role: "technical_analyst",
		input: "Check if SPY is overbought",
		output:
			"SPY overbought signals:\n- RSI-14 daily: 72.4 (above 70)\n- Stoch %K: 89\n- BB %B: 0.92\n\n**Verdict:** Short-term overbought, watch for mean reversion at 580 support.",
		tools_used: ["get_chart_state", "sandbox_execute"],
		duration_ms: 6800,
		token_count: 1340,
		confidence: 0.81,
		tags: ["spy", "overbought", "rsi"],
		created_at: isoOffset(380),
		retain_until: null,
	},
	{
		id: "ep_010",
		session_id: "sess_i9j0",
		user_id: "local",
		agent_role: "researcher",
		input: "Find correlations between gold and DXY this month",
		output:
			"Gold vs DXY correlation (last 30d): -0.78 (strong negative). Confirms classic dollar-gold inverse relationship. When DXY broke 104 on Apr 3, gold rallied $42 within 48h.",
		tools_used: ["sandbox_execute", "memory_search"],
		duration_ms: 21500,
		token_count: 3680,
		confidence: 0.87,
		tags: ["gold", "dxy", "correlation"],
		created_at: isoOffset(450),
		retain_until: null,
	},
];

export const mockTimeline: TimelineResponse = {
	markers: mockEpisodes.flatMap((ep): TimelineMarker[] => [
		{
			id: `${ep.id}-recall`,
			timestamp: ep.created_at,
			type: "recall",
			label: `${ep.agent_role.replace("_", " ")} · recall`,
			episode_id: ep.id,
		},
		{
			id: `${ep.id}-retain`,
			timestamp: new Date(Date.parse(ep.created_at) + ep.duration_ms).toISOString(),
			type: "retain",
			label: `Stored: ${ep.tags.slice(0, 2).join(", ")}`,
			episode_id: ep.id,
		},
	]),
};

// Memory layer color helper (used by health cards, timeline markers)
export function getLayerColor(type: MemoryLayer["type"]): string {
	switch (type) {
		case "episodic":
			return "var(--status-recall)"; // blue
		case "kg":
			return "var(--status-reflect)"; // violet
		case "vector":
			return "var(--status-retain)"; // green
		default:
			return "var(--muted-foreground)";
	}
}

export function getRoleLabel(role: Episode["agent_role"]): string {
	const map: Record<Episode["agent_role"], string> = {
		fundamentals_analyst: "Fundamentals",
		sentiment_analyst: "Sentiment",
		technical_analyst: "Technical",
		researcher: "Researcher",
		trader: "Trader",
		risk_manager: "Risk Manager",
	};
	return map[role];
}

export function getRoleColor(role: Episode["agent_role"]): string {
	const map: Record<Episode["agent_role"], string> = {
		fundamentals_analyst: "#3B73B8",
		sentiment_analyst: "#A78BFA",
		technical_analyst: "#10B981",
		researcher: "#38BDF8",
		trader: "#F59E0B",
		risk_manager: "#EF4444",
	};
	return map[role];
}
