// Control query key factories + fetchers for all Slice 5/6/7 tabs.
//
// Pattern: each area exports a `<area>Keys` object (query key factory) and
// a `<area>Queries` object (fetchers).
//
// Usage in a Tab:
//   const { data, isLoading } = useQuery({
//     queryKey: agentsKeys.list(),
//     queryFn: () => agentsQueries.list(),
//   });

import type {
	A2ADelegation,
	AgentRole,
	AuditEvent,
	EnvVar,
	LlmProvider,
	McpServer,
	ModelRouting,
	OverviewSnapshot,
	PermissionCell,
	SandboxRun,
	SecurityPosture,
	ServiceStatus,
	Session,
	Skill,
	ToolCategory,
	ToolDefinition,
	UtilityModel,
} from "@/features/control/types";
import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

// ─── Overview ──────────────────────────────────────────────────────────────

export const overviewKeys = {
	all: ["control", "overview"] as const,
	snapshot: (userId = "local") => ["control", "overview", "snapshot", userId] as const,
};

export const overviewQueries = {
	snapshot: async (userId = "local"): Promise<OverviewSnapshot> =>
		apiGet<OverviewSnapshot>(`/api/control/overview?user_id=${encodeURIComponent(userId)}`),
};

// ─── Agents ────────────────────────────────────────────────────────────────

export const agentsKeys = {
	all: ["control", "agents"] as const,
	list: () => ["control", "agents", "list"] as const,
	detail: (id: string) => ["control", "agents", "detail", id] as const,
};

export const agentsQueries = {
	list: async (): Promise<{ items: AgentRole[]; total: number }> => apiGet("/api/control/agents"),
	get: async (id: string): Promise<AgentRole> =>
		apiGet(`/api/control/agents/${encodeURIComponent(id)}`),
	patch: async (id: string, patch: Partial<AgentRole>): Promise<AgentRole> =>
		apiPatch(`/api/control/agents/${encodeURIComponent(id)}`, patch),
	resetField: async (id: string, field: string): Promise<{ status: string }> =>
		apiDelete(
			`/api/control/agents/${encodeURIComponent(id)}/overrides/${encodeURIComponent(field)}`,
		),
};

// ─── Permissions ───────────────────────────────────────────────────────────

export const permissionsKeys = {
	all: ["control", "permissions"] as const,
	matrix: () => ["control", "permissions", "matrix"] as const,
	categories: () => ["control", "permissions", "categories"] as const,
};

export const permissionsQueries = {
	matrix: async (): Promise<{
		items: PermissionCell[];
		roles: string[];
		categories: string[];
	}> => apiGet("/api/control/permissions/matrix"),
	categories: async (): Promise<{ items: ToolCategory[] }> =>
		apiGet("/api/control/permissions/categories"),
	patchCell: async (cell: {
		role_id: string;
		category_id: string;
		level: string;
	}): Promise<{ status: string }> => apiPatch("/api/control/permissions/cell", cell),
	resetCell: async (roleId: string, categoryId: string): Promise<{ status: string }> =>
		apiDelete(
			`/api/control/permissions/cell/${encodeURIComponent(roleId)}/${encodeURIComponent(categoryId)}`,
		),
	reload: async (): Promise<{ status: string }> => apiPost("/api/control/permissions/reload"),
};

// ─── Skills ────────────────────────────────────────────────────────────────

export const skillsKeys = {
	all: ["control", "skills"] as const,
	list: (tier?: string) => ["control", "skills", "list", tier ?? "all"] as const,
	detail: (id: string) => ["control", "skills", "detail", id] as const,
};

export const skillsQueries = {
	list: async (tier?: string): Promise<{ items: Skill[]; total: number }> =>
		apiGet(`/api/control/skills${tier ? `?tier=${encodeURIComponent(tier)}` : ""}`),
	get: async (id: string): Promise<Skill & { body?: string }> =>
		apiGet(`/api/control/skills/${encodeURIComponent(id)}`),
	patch: async (id: string, patch: { enabled?: boolean }): Promise<{ status: string }> =>
		apiPatch(`/api/control/skills/${encodeURIComponent(id)}`, patch),
};

// ─── Tools ─────────────────────────────────────────────────────────────────

export const toolsKeys = {
	all: ["control", "tools"] as const,
	list: (type?: string, category?: string) =>
		["control", "tools", "list", type ?? "all", category ?? "all"] as const,
};

export const toolsQueries = {
	list: async (
		type?: string,
		category?: string,
	): Promise<{ items: ToolDefinition[]; total: number }> => {
		const params = new URLSearchParams();
		if (type) params.set("type", type);
		if (category) params.set("category", category);
		const qs = params.toString();
		return apiGet(`/api/control/tools${qs ? `?${qs}` : ""}`);
	},
};

// ─── Sandbox ───────────────────────────────────────────────────────────────

export const sandboxKeys = {
	all: ["control", "sandbox"] as const,
	list: (status?: string, role?: string) =>
		["control", "sandbox", "list", status ?? "all", role ?? "all"] as const,
};

export const sandboxQueries = {
	list: async (status?: string, role?: string): Promise<{ items: SandboxRun[]; total: number }> => {
		const params = new URLSearchParams();
		if (status) params.set("status", status);
		if (role) params.set("role", role);
		const qs = params.toString();
		return apiGet(`/api/control/sandbox/runs${qs ? `?${qs}` : ""}`);
	},
};

// ─── System ────────────────────────────────────────────────────────────────

export const systemKeys = {
	all: ["control", "system"] as const,
	health: () => ["control", "system", "health"] as const,
};

export const systemQueries = {
	health: async (): Promise<{
		items: ServiceStatus[];
		total: number;
		counts: Record<string, number>;
	}> => apiGet("/api/control/system/health"),
};

// ─── API / Models ──────────────────────────────────────────────────────────

export const modelsKeys = {
	all: ["control", "models"] as const,
	providers: () => ["control", "models", "providers"] as const,
	routing: () => ["control", "models", "routing"] as const,
	utility: () => ["control", "models", "utility"] as const,
	env: () => ["control", "models", "env"] as const,
};

export const modelsQueries = {
	providers: async (): Promise<{ items: LlmProvider[]; total: number; active: number }> =>
		apiGet("/api/control/models/providers"),
	routing: async (): Promise<{ items: ModelRouting[] }> => apiGet("/api/control/models/routing"),
	utility: async (): Promise<{ items: UtilityModel[] }> => apiGet("/api/control/models/utility"),
	env: async (): Promise<{ items: EnvVar[]; total: number }> => apiGet("/api/control/models/env"),
};

// ─── Audit ─────────────────────────────────────────────────────────────────

export const auditKeys = {
	all: ["control", "audit"] as const,
	list: (filters: Record<string, unknown>) => ["control", "audit", "list", filters] as const,
};

export const auditQueries = {
	list: async (
		filters: Partial<{
			action: string;
			user_id: string;
			role: string;
			success: boolean;
			from: string;
			to: string;
			limit: number;
			offset: number;
		}> = {},
	): Promise<{ items: AuditEvent[]; total: number }> => {
		const params = new URLSearchParams();
		for (const [k, v] of Object.entries(filters)) {
			if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
		}
		const qs = params.toString();
		return apiGet(`/api/control/audit${qs ? `?${qs}` : ""}`);
	},
};

// ─── Sessions ──────────────────────────────────────────────────────────────

export const sessionsKeys = {
	all: ["control", "sessions"] as const,
	list: (activeOnly: boolean) => ["control", "sessions", "list", activeOnly] as const,
	detail: (id: string) => ["control", "sessions", "detail", id] as const,
};

export const sessionsQueries = {
	list: async (activeOnly = false): Promise<{ items: Session[]; total: number }> =>
		apiGet(`/api/control/sessions?active_only=${activeOnly}`),
	get: async (id: string): Promise<Session> =>
		apiGet(`/api/control/sessions/${encodeURIComponent(id)}`),
	kill: async (id: string): Promise<{ status: string }> =>
		apiDelete(`/api/control/sessions/${encodeURIComponent(id)}`),
};

// ─── MCP ───────────────────────────────────────────────────────────────────

export const mcpKeys = {
	all: ["control", "mcp"] as const,
	servers: () => ["control", "mcp", "servers"] as const,
};

export const mcpQueries = {
	servers: async (): Promise<{ items: McpServer[]; total: number }> =>
		apiGet("/api/control/mcp/servers"),
};

// ─── A2A ───────────────────────────────────────────────────────────────────

export const a2aKeys = {
	all: ["control", "a2a"] as const,
	list: (status?: string) => ["control", "a2a", "list", status ?? "all"] as const,
};

export const a2aQueries = {
	list: async (status?: string): Promise<{ items: A2ADelegation[]; total: number }> =>
		apiGet(`/api/control/a2a/delegations${status ? `?status=${status}` : ""}`),
};

// ─── Security ──────────────────────────────────────────────────────────────

export const securityKeys = {
	all: ["control", "security"] as const,
	posture: () => ["control", "security", "posture"] as const,
	events: () => ["control", "security", "events"] as const,
};

export const securityQueries = {
	posture: async (): Promise<SecurityPosture> => apiGet("/api/control/security/posture"),
};

// ─── Ingestion (Slice 2 write path) ───────────────────────────────────────

export const ingestionKeys = {
	all: ["ingestion"] as const,
	status: () => ["ingestion", "status"] as const,
	jobs: (jobId: string) => ["ingestion", "jobs", jobId] as const,
};

export interface IngestNoteInput {
	text: string;
	user_id?: string;
	tags?: string[];
	title?: string;
}

export interface IngestDocumentInput {
	file_id: string;
	user_id?: string;
	tags?: string[];
	sinks?: string[];
}

export interface IngestLinkInput {
	url: string;
	user_id?: string;
	tags?: string[];
	title?: string;
}

export const ingestionQueries = {
	ingestNote: async (
		input: IngestNoteInput,
	): Promise<{ status: string; job_id?: string; chunks?: number }> =>
		apiPost("/api/control/ingest/note", {
			text: input.text,
			user_id: input.user_id ?? "local",
			tags: input.tags ?? [],
			title: input.title,
		}),
	ingestDocument: async (
		input: IngestDocumentInput,
	): Promise<{ status: string; file_id: string }> =>
		apiPost("/api/control/ingest/document", {
			file_id: input.file_id,
			user_id: input.user_id ?? "local",
			tags: input.tags ?? [],
			sinks: input.sinks ?? ["hindsight", "storage"],
		}),
	ingestLink: async (input: IngestLinkInput): Promise<{ status: string; url: string }> =>
		apiPost("/api/control/ingest/link", {
			url: input.url,
			user_id: input.user_id ?? "local",
			tags: input.tags ?? [],
			title: input.title,
		}),
	status: async (): Promise<{
		counts: Record<string, number>;
		total: number;
		done: number;
		failed: number;
		pending: number;
		running: number;
	}> => apiGet("/api/control/ingestion/status"),
	reindex: async (
		fileId: string,
		input: Omit<IngestDocumentInput, "file_id"> = {},
	): Promise<{ status: string; file_id: string; mode: string }> =>
		apiPost(`/api/control/ingest/document/${encodeURIComponent(fileId)}/reindex`, {
			file_id: fileId,
			user_id: input.user_id ?? "local",
			tags: input.tags ?? [],
			sinks: input.sinks ?? ["hindsight", "storage"],
		}),
};

// ─── Memory ────────────────────────────────────────────────────────────────

export const memoryKeys = {
	all: ["memory"] as const,
	health: () => ["memory", "health"] as const,
	episodes: (filters: Record<string, unknown>) => ["memory", "episodes", "list", filters] as const,
	episode: (id: string) => ["memory", "episodes", "detail", id] as const,
	kgGraph: (type?: string) => ["memory", "kg", "graph", type ?? "all"] as const,
};

// ─── KG Graph (K4 Slice 4) ────────────────────────────────────────────────

export interface KgGraphResponse {
	nodes: Array<Record<string, unknown>>;
	edges: Array<Record<string, unknown>>;
	total_nodes: number;
	total_edges: number;
}

export const kgGraphQueries = {
	graph: async (type?: string, limit = 500): Promise<KgGraphResponse> => {
		const params = new URLSearchParams();
		if (type) params.set("type", type);
		params.set("limit", String(limit));
		return apiGet(`/api/memory/kg/graph?${params.toString()}`);
	},
};

export const memoryQueries = {
	health: async (): Promise<{ bank_id: string; layers: Record<string, unknown> }> =>
		apiGet("/api/memory/health"),
	listEpisodes: async (
		filters: Partial<{
			role: string;
			session_id: string;
			search: string;
			fact_type: string;
			from: string;
			to: string;
			limit: number;
			offset: number;
		}> = {},
	): Promise<{ items: unknown[]; total: number; limit: number; offset: number }> => {
		const params = new URLSearchParams();
		for (const [k, v] of Object.entries(filters)) {
			if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
		}
		const qs = params.toString();
		return apiGet(`/api/memory/episodes${qs ? `?${qs}` : ""}`);
	},
	getEpisode: async (id: string): Promise<unknown> =>
		apiGet(`/api/memory/episodes/${encodeURIComponent(id)}`),
	deleteEpisode: async (id: string): Promise<{ status: string }> =>
		apiDelete(`/api/memory/episodes/${encodeURIComponent(id)}`),
};
