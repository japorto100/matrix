// Memory & Episode types — mirrors python-backend/memory_engine/episodic_store.py
// + agent/control/episodes.py response shape (NOT YET IMPLEMENTED — Slice 3 backend)

export type MemoryLayerType = "episodic" | "kg" | "vector";
export type MemoryLayerHealth = "ok" | "degraded" | "error";

export interface MemoryLayer {
	type: MemoryLayerType;
	provider: string; // "kuzu" | "chroma" | "sqlite" | etc.
	health: MemoryLayerHealth;
	item_count: number;
	last_sync_at: string | null; // ISO 8601
	consolidation_pending: number;
}

export interface MemoryOverviewResponse {
	layers: MemoryLayer[];
}

// ── Episode (matches agent_episodes table) ─────────────────────────────────

export type AgentRoleId =
	| "fundamentals_analyst"
	| "sentiment_analyst"
	| "technical_analyst"
	| "researcher"
	| "trader"
	| "risk_manager";

export interface Episode {
	id: string;
	session_id: string;
	user_id: string;
	agent_role: AgentRoleId;
	input: string; // user message
	output: string; // agent response (markdown)
	tools_used: string[];
	duration_ms: number;
	token_count: number;
	confidence: number; // 0..1
	tags: string[];
	created_at: string; // ISO
	retain_until: string | null;
}

export interface EpisodesResponse {
	episodes: Episode[];
	total: number;
	has_more: boolean;
}

export interface EpisodesQuery {
	role?: AgentRoleId[];
	session_id?: string;
	from?: string;
	to?: string;
	tags?: string[];
	confidence_min?: number;
	limit?: number;
	offset?: number;
}

// ── Memory Timeline (Slice 3.4) ───────────────────────────────────────────

export type TimelineMarkerType =
	| "recall"
	| "retain"
	| "reflect"
	| "consolidate"
	| "failed"
	| "expiring";

export interface TimelineMarker {
	id: string;
	timestamp: string;
	type: TimelineMarkerType;
	label: string;
	episode_id?: string;
	memory_id?: string;
}

export interface TimelineResponse {
	markers: TimelineMarker[];
}
