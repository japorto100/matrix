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
	description?: string;
	summary?: string;
	provider?: string; // "matrix-builtin" | "exa" | "playwright-mcp" | ...
	input_schema_summary: string; // human-readable
	categories: string[];
	group?: string;
	risk?: "low" | "medium" | "high" | "critical";
	approval?: "auto" | "inform" | "confirm" | "deny";
	progressive_disclosure_level?: number;
	policy_reasons?: string[];
	last_called_at?: string;
	call_count_24h: number;
	avg_latency_ms?: number;
	enabled: boolean;
}

export type SemanticStatus = "draft" | "active" | "deprecated";
export type SemanticMetricScope = "public" | "tenant" | "user" | "admin";

export interface SemanticTerm {
	term_id: string;
	name: string;
	aliases: string[];
	owner: string;
	status: SemanticStatus;
	description: string;
	source_refs: string[];
	allowed_use: string[];
	kg_claim_types: string[];
	rag_source_classes: string[];
	version: string;
	deprecated_by?: string | null;
}

export interface SemanticMetric {
	metric_id: string;
	name: string;
	measure: string;
	dimensions: string[];
	filters: string[];
	grain: string;
	time_field: string;
	freshness_sla: string;
	allowed_aggregations: string[];
	aliases: string[];
	owner: string;
	status: SemanticStatus;
	permission_scope: SemanticMetricScope;
	source_table: string;
	source_refs: string[];
	version: string;
	deprecated_by?: string | null;
}

export interface SemanticCatalog {
	version: string;
	terms: SemanticTerm[];
	metrics: SemanticMetric[];
}

export interface SemanticCatalogValidation {
	passed: boolean;
	failures: string[];
	alias_collisions: Record<string, string[]>;
}

export interface SemanticCatalogResponse {
	catalog: SemanticCatalog;
	validation: SemanticCatalogValidation;
}

export interface SemanticMetricPlanResponse {
	allowed: boolean;
	reason?: string;
	metric?: SemanticMetric;
	semantic_contract?: {
		measure: string;
		dimensions: string[];
		filters: string[];
		grain: string;
		time_field: string;
		source_table: string;
		source_refs: string[];
	};
	sql: string | null;
	raw_sql_allowed: boolean;
	freshness_sla?: string;
}

export type ReportArtifactStatus = "generated" | "validated" | "failed" | "published";
export type ReportRenderer = "quarkdown" | "markdown-fallback";

export interface ReportCitation {
	citation_id: string;
	source_id: string;
	title: string;
	uri?: string;
	source_type: string;
	excerpt?: string;
}

export interface ReportOutputFile {
	kind: "source" | "html" | "pdf" | "slides" | "text" | "manifest" | "data";
	path: string;
	mime_type?: string;
	size_bytes?: number;
	checksum?: string;
}

export interface ReportArtifact {
	report_id: string;
	title: string;
	owner: string;
	status: ReportArtifactStatus;
	renderer: ReportRenderer;
	renderer_version: string;
	generated_at: string;
	checksum: string;
	manifest_path: string;
	input_sources: string[];
	citations: ReportCitation[];
	output_files: ReportOutputFile[];
	validation: {
		passed: boolean;
		failures: string[];
	};
	matrix_publication?: {
		room_id?: string;
		event_id?: string;
		link?: string;
		status: "not_published" | "ready" | "published" | "blocked";
	};
}

export type MatrixWidgetApprovalStatus = "pending" | "approved" | "blocked" | "denied" | "revoked";

export interface MatrixWidgetApprovalItem {
	proposal_id: string;
	report_id?: string;
	title: string;
	room_id: string;
	requester_user_id: string;
	url?: string;
	resource_uri?: string;
	status: MatrixWidgetApprovalStatus;
	approval_required: boolean;
	can_approve: boolean;
	can_deny: boolean;
	denial_reasons: string[];
	fallback_markdown: string;
	permissions: string[];
	audit_refs: string[];
	report_artifact?: {
		manifest_id?: string;
		output_path?: string;
		renderer?: string;
	};
	matrix_publication?: {
		room_id?: string;
		event_id?: string;
		link?: string;
		status?: string;
	};
	validation?: {
		passed?: boolean;
		failures?: string[];
	};
}

export interface MatrixWidgetApprovalResponse {
	items: MatrixWidgetApprovalItem[];
	total: number;
	summary: {
		pending: number;
		approved: number;
		blocked: number;
	};
	contract: "matrix-widget-approval/v1";
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

export type AgentOpsEventStatus = "active" | "waiting" | "blocked" | "failed" | "needs_approval";
export type AgentOpsEventType =
	| "trace"
	| "tool_call"
	| "approval"
	| "memory"
	| "rag"
	| "kg"
	| "llm"
	| "matrix_transport";
export type AgentRuntimeEventKind =
	| "run"
	| "turn"
	| "llm"
	| "tool"
	| "memory"
	| "rag"
	| "kg"
	| "artifact"
	| "subagent"
	| "mcp"
	| "matrix"
	| "control"
	| "unknown";
export type AgentRuntimeEventStatus =
	| "accepted"
	| "started"
	| "active"
	| "waiting"
	| "needs_approval"
	| "blocked"
	| "failed"
	| "completed"
	| "stale"
	| "cancelled"
	| "unknown";

export interface AgentRuntimeEvent {
	contract?: "agent-runtime-event/v1" | string;
	event_id?: string;
	parent_event_id?: string;
	kind?: AgentRuntimeEventKind | string;
	status?: AgentRuntimeEventStatus | string;
	name?: string;
	summary?: string;
	session_id?: string;
	thread_id?: string;
	turn?: number;
	timestamp?: string;
	audit_ref?: string;
	metadata?: Record<string, unknown>;
}

export interface AgentOpsSurfaceLink {
	surface: "prompt_cache" | "report_artifact" | string;
	label: string;
	href: string;
	provider?: string;
	model?: string;
	prompt_digest?: string;
	prompt_layout_digest?: string;
	tool_catalog_digest?: string;
	cache_read_tokens?: number | null;
	cache_write_tokens?: number | null;
	cache_break_reasons?: string[];
	report_id?: string;
	manifest_path?: string;
	output_path?: string;
	status?: string;
}

export interface AgentSubagentRun {
	run_id: string;
	child_task_id?: string;
	parent_thread_id?: string;
	role?: string;
	delegate_kind?: string;
	status: AgentRuntimeEventStatus | string;
	started_at?: string;
	ended_at?: string;
	event_count: number;
	spawn_depth?: number;
	next_spawn_depth?: number;
	max_spawn_depth?: number;
	last_event?: AgentRuntimeEvent;
	controls?: Record<string, string>;
}

export interface AgentOpsEvent {
	id: string;
	source: "audit" | "trace" | "meta_harness";
	event_type: AgentOpsEventType;
	status: AgentOpsEventStatus;
	timestamp: string;
	thread_id?: string;
	user_id?: string;
	agent_role?: string;
	tool_name?: string;
	action: string;
	success: boolean;
	risk: "low" | "medium" | "high" | "critical" | "unrated";
	approval_ref?: string;
	audit_ref?: string;
	duration_ms?: number;
	error?: string;
	input?: Record<string, unknown>;
	output?: Record<string, unknown>;
	metadata?: Record<string, unknown>;
	request_telemetry?: Record<string, unknown>;
	linked_surfaces?: {
		prompt_cache?: AgentOpsSurfaceLink;
		report_artifacts?: AgentOpsSurfaceLink[];
	};
	runtime_events?: AgentRuntimeEvent[];
	runtime_event_count?: number;
	blocker_reason?: string;
	matrix_room_id?: string;
	matrix_event_id?: string;
	matrix_thread_id?: string;
}

export interface AgentOpsSession {
	thread_id: string;
	status: AgentOpsEventStatus | "replay";
	agent_role?: string;
	last_checkpoint?: string;
	checkpoint_count: number;
	event_count: number;
	tool_count: number;
}

export interface AgentOpsReadModel {
	items: AgentOpsEvent[];
	sessions: AgentOpsSession[];
	blockers: AgentOpsEvent[];
	approvals: AgentOpsEvent[];
	runtime_events: AgentRuntimeEvent[];
	subagent_runs: AgentSubagentRun[];
	runtime_summary: {
		total: number;
		by_kind: Record<string, number>;
		by_status: Record<string, number>;
		latest?: AgentRuntimeEvent;
	};
	filters: Record<string, string>;
	summary: {
		total_events: number;
		sessions: number;
		tool_events: number;
		blockers: number;
		approvals: number;
		runtime_events?: number;
		subagent_runs?: number;
		generated_at: string;
	};
	limit: number;
	offset: number;
	contract: "agent-ops-event/v1";
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

export interface McpCatalogEntry {
	server: {
		server_id: string;
		transport: string;
		url?: string;
		enabled: boolean;
		env_keys: string[];
	};
	tool: {
		original_name: string;
		matrix_name: string;
		descriptor_hash: string;
		first_seen: string;
		last_seen: string;
		risk_flags: string[];
		approval_level: "auto" | "confirm" | "destructive" | "admin" | "blocked";
		enabled: boolean;
	};
	visible: boolean;
	denial_reasons: string[];
	descriptor_diff?: {
		changed: boolean;
		changed_fields: string[];
		added_risk_flags: string[];
		risk_escalated: boolean;
		requires_reapproval: boolean;
	};
	provenance?: {
		server_id: string;
		server_label: string;
		server_domain: string;
		source: string;
		tool_name: string;
		matrix_name: string;
	};
	secrets_redacted: boolean;
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
