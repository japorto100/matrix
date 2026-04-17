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

export interface MemoryInspectorBlock {
	id: string;
	title: string;
	preview: string;
	sourceLayer: string;
	sourceType: string;
	artifactType: string;
	groundingStatus: string;
	provenanceRef: string;
	status: string;
	route?: string;
	tokenCount?: number;
}

export interface MemoryActiveSession {
	sessionId?: string | null;
	threadId?: string | null;
	status?: string | null;
	provider?: string | null;
	model?: string | null;
	promptTokens?: number;
	completionTokens?: number;
	reasoningTokens?: number;
	cachedTokens?: number;
	totalTokens?: number;
	contextPressure?: number;
	updatedAt?: string | null;
}

export interface MemoryInspector {
	memoryProvider?: string;
	activeSession?: MemoryActiveSession | null;
	sourceLayerCounts?: Record<string, number>;
	contextBlocks?: MemoryInspectorBlock[];
	degradationFlags?: string[];
	hasPersistedRunMetadata?: boolean;
	liveContextBlockCount?: number;
}

export interface MemoryOverviewResponse {
	layers: MemoryLayer[];
	ops?: {
		layers: Array<{
			type: MemoryLayerType;
			provider: string;
			health: "healthy" | "degraded" | "offline" | "unknown";
			itemCount: number;
			lastSyncAt: string | null;
			consolidationPending: number;
		}>;
		degraded?: boolean;
		degradedReasons?: string[];
	};
	inspector?: MemoryInspector;
	degraded?: boolean;
	degraded_reasons?: string[];
	degradedReasons?: string[];
	bank_id?: string;
	user_id?: string;
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
