// Control Surface — types for Slice 5 (Agent Config) + Slice 6 (Observability)

// ─── Slice 5: Agent Configuration ──────────────────────────────────────────

// Must match backend agent/roles.py TradingRole enum values (fix 08.04.2026)
export type TradingRole =
	| "fundamentals_analyst"
	| "sentiment_analyst"
	| "technical_analyst"
	| "researcher"
	| "trader"
	| "risk_manager";

export type MemoryAccess = "read" | "read_write" | "none";

export interface AgentRole {
	id: TradingRole;
	display_name: string;
	system_prompt: string;
	allowed_tools: string[];
	memory_access: MemoryAccess;
	approval_required: boolean;
	is_default: boolean; // false = has DB overlay
	updated_at?: string;
	updated_by?: string;
}

// Permission matrix (consent_policy + overlays from D2)
export type ConsentLevel = "auto" | "inform" | "confirm" | "deny";

export interface ToolCategory {
	id: string;
	display_name: string;
	tools: string[];
}

export interface PermissionCell {
	role_id: TradingRole;
	category_id: string;
	level: ConsentLevel;
	is_overridden: boolean; // true = comes from DB overlay, not yaml default
}

// Skills (3-tier from exec-10)
export type SkillTier = "global" | "team" | "personal";

export interface Skill {
	id: string;
	name: string;
	tier: SkillTier;
	description: string;
	generation: number;
	last_used_at?: string;
	enabled: boolean;
	source: "builtin" | "github" | "local";
	github_url?: string;
	body_preview: string;
}

export interface HighlightItem {
	id: string;
	title: string;
	content: string;
	format: "paragraph" | "bullets" | "quote" | "one_liner";
	query: string;
	source_episode_ids: string[];
}

// Sandbox runs (exec-12 OpenSandbox)
export type SandboxStatus = "running" | "completed" | "failed" | "timeout" | "killed";

export interface SandboxRun {
	id: string;
	user_id: string;
	role: TradingRole;
	tool_name: string;
	code_preview: string; // first 200 chars
	status: SandboxStatus;
	started_at: string;
	completed_at?: string;
	duration_ms?: number;
	stdout_preview?: string;
	stderr_preview?: string;
	exit_code?: number;
}

// Tools registry (exec-09 MCP + builtin)
export type ToolType = "builtin" | "mcp" | "skill" | "a2a";

export interface ToolDefinition {
	id: string;
	name: string;
	type: ToolType;
	description: string;
	provider?: string; // "matrix-builtin" | "exa" | "playwright-mcp" | ...
	input_schema_summary: string; // human-readable
	categories: string[];
	last_called_at?: string;
	call_count_24h: number;
	avg_latency_ms?: number;
	enabled: boolean;
}

// ─── Slice 6: System Observability ─────────────────────────────────────────

export type ServiceHealth = "healthy" | "degraded" | "unhealthy" | "unknown";

export interface ServiceStatus {
	id: string;
	name: string;
	tier: "infra" | "app";
	port?: number;
	url?: string;
	health: ServiceHealth;
	uptime_s?: number;
	version?: string;
	last_check: string;
	error_message?: string;
}

export interface EnvVar {
	key: string;
	value: string;
	is_sensitive: boolean; // masked in UI
	source: "env" | "default" | "computed";
	description?: string;
}

// Audit Events (exec-12 Phase 2.1)
export interface AuditEvent {
	id: number;
	timestamp: string;
	action: string;
	user_id?: string;
	thread_id?: string;
	agent_class?: string;
	agent_role?: string;
	tool_name?: string;
	input?: Record<string, unknown>;
	output?: Record<string, unknown>;
	duration_ms?: number;
	success: boolean;
	error?: string;
	metadata?: Record<string, unknown>;
}

// Sessions = LangGraph thread checkpoints (exec-10)
// Backend returns minimal fields (thread_id + last_checkpoint + checkpoint_count + is_active).
// Frontend SessionsTab shows rich fields only when present — all other fields are optional.
export interface Session {
	thread_id: string;
	is_active: boolean;
	// Minimal backend fields (always present from real API)
	last_checkpoint?: string;
	checkpoint_count?: number;
	// Rich fields (mock only, backend Phase 2 may extract from checkpoint metadata)
	user_id?: string;
	role?: TradingRole;
	created_at?: string;
	last_message_at?: string;
	message_count?: number;
	tool_calls?: number;
	last_message_preview?: string;
}

// MCP Servers (exec-09)
export interface McpServer {
	id: string;
	name: string;
	url: string;
	transport: "stdio" | "http" | "sse";
	status: "connected" | "disconnected" | "error";
	tools: string[]; // tool names this server exposes
	last_ping?: string;
	error?: string;
}

// A2A Delegations (exec-10 Phase 4 scaffold)
export interface A2ADelegation {
	id: string;
	from_role: TradingRole;
	to_role: TradingRole;
	task: string;
	status: "pending" | "running" | "completed" | "failed";
	started_at: string;
	completed_at?: string;
	result_preview?: string;
	thread_id: string;
}

// ─── Slice 7: Two-Tier Mode + ApiModels + Overview + Security ──────────────

export type ControlMode = "user" | "dev";

// LLM Provider config (ApiModelsTab)
export type LlmProviderId =
	| "anthropic"
	| "openai"
	| "gemini"
	| "mistral"
	| "groq"
	| "cohere"
	| "openrouter"
	| "deepseek"
	| "qwen"
	| "ollama"
	| "vllm"
	| "lmstudio"
	| (string & {}); // allow extension

export type LlmProviderType = "cloud" | "local";

export interface LlmProvider {
	id: LlmProviderId;
	display_name: string;
	type: LlmProviderType;
	api_key_set: boolean;
	api_key_preview?: string;
	endpoint_url?: string;
	is_active: boolean;
	available_models: string[];
	last_test_at?: string;
	last_test_status?: "ok" | "error";
}

// exec-16: User LLM Settings (from /api/control/user/llm)
export interface UserLlmSettings {
	user_id: string;
	default_model: string | null;
	providers: LlmProvider[];
}

export interface ModelRouting {
	role_id: TradingRole;
	provider_id: LlmProviderId;
	model_id: string;
	is_default: boolean;
}

export type UtilityPurpose =
	| "embedder_text"
	| "embedder_visual"
	| "reranker"
	| "summarizer"
	| "stt"
	| "tts";

export interface UtilityModel {
	purpose: UtilityPurpose;
	display_name: string;
	provider_id: string;
	model_id: string;
	is_local: boolean;
	is_active: boolean;
	notes?: string;
}

// Overview Tab (TT1 - both modes, simplified in User)
export type AiHealth = "online" | "degraded" | "offline";

export interface OverviewSnapshot {
	ai_health: AiHealth;
	ai_health_message: string;
	active_sessions: number;
	active_tasks: number;
	memory_facts_total: number;
	kg_nodes_total: number;
	last_agent_error?: {
		timestamp: string;
		// Raw role string from agent.audit_events.agent_role (may be "unknown")
		role: string;
		message: string;
	};
	recent_activity: {
		timestamp: string;
		text: string;
		kind: "tool_call" | "memory" | "sandbox" | "error" | "ingestion";
	}[];
}

export interface ContextInspectorBlock {
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

export interface ContextActiveSession {
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

export interface ContextInspectorStats {
	memoryProvider: string;
	kgNodeCount: number;
	kgEdgeCount: number;
	kgHealth: "healthy" | "degraded" | "offline" | "unknown";
	hasPersistedRunMetadata: boolean;
	liveContextBlockCount: number;
}

export interface ContextInspectorResponse {
	stats: ContextInspectorStats;
	activeSession?: ContextActiveSession | null;
	sourceLayerCounts: Record<string, number>;
	contextBlocks: ContextInspectorBlock[];
	degradationFlags: string[];
	worldClaims: ContextInspectorBlock[];
	userId: string;
	bankId: string;
}

// Security Tab (TT8 - both modes)
export type SecurityPillarStatus = "good" | "warning" | "critical";

export interface SecurityPillar {
	name: string;
	score: number;
	status: SecurityPillarStatus;
	message: string;
}

export type SecurityEventType =
	| "login"
	| "role_change"
	| "sensitive_tool_call"
	| "policy_change"
	| "audit_export"
	| "permission_change";

export type SecuritySeverity = "info" | "warning" | "critical";

export interface SecurityEvent {
	timestamp: string;
	type: SecurityEventType;
	actor: string;
	description: string;
	severity: SecuritySeverity;
}

export interface AccessEntry {
	session_id: string;
	ip: string;
	user_agent: string;
	first_seen?: string | null;
	last_seen?: string | null;
}

export interface SecurityPosture {
	overall_score: number; // 0-100
	pillars: SecurityPillar[];
	recent_events: SecurityEvent[];
	access_list: AccessEntry[];
}

// ─── Scheduler (exec-scheduler Lane D) ────────────────────────────────────

export type ScheduledTaskKind =
	| "recurring"
	| "one_shot"
	| "reminder"
	| "routine"
	| "condition"
	| "infra";

export type ScheduledTaskStatus = "active" | "paused" | "completed" | "cancelled" | "errored";

export type ScheduledTaskSource =
	| "chat_agent"
	| "chat_matrix_dm"
	| "chat_matrix_group"
	| "api"
	| "github_webhook"
	| "system";

export interface ScheduledTask {
	task_id: string;
	user_id: string;
	source: ScheduledTaskSource;
	kind: ScheduledTaskKind;
	cron_expr?: string;
	scheduled_at_ms?: number;
	tz: string;
	prompt?: string;
	skill_ids?: string[];
	delivery_target?: Record<string, unknown>;
	status: ScheduledTaskStatus;
	max_executions?: number;
	execution_count: number;
	next_run_at_ms?: number;
	last_run_at_ms?: number;
	created_at_ms: number;
	updated_at_ms?: number;
}

export type TaskExecutionStatus = "running" | "completed" | "failed" | "cancelled" | "timeout";

export interface TaskExecution {
	execution_id: string;
	task_id: string;
	started_at: number; // epoch-ms
	completed_at?: number | null;
	status: TaskExecutionStatus;
	result_summary?: string | null;
	error?: string | null;
	trace_id?: string | null;
	duration_ms?: number | null;
}
