"use client";

// Typed React Query hooks for all Slice 5/6/7 Control tabs.
//
// Usage in a Tab:
//   const { data: agents } = useAgents();
//   const list = agents?.items ?? mockAgentRoles;  // mock fallback
//
// When the backend is reachable we get live data; when it's down (or endpoint
// not yet built) we fall back to mock-data.ts. This means the UI is always
// functional even without backend — key for Slice 7 pragmatic wiring.

import { type UseQueryResult, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	a2aKeys,
	a2aQueries,
	agentsKeys,
	agentsQueries,
	auditKeys,
	auditQueries,
	type IngestDocumentInput,
	type IngestLinkInput,
	type IngestNoteInput,
	ingestionQueries,
	kgGraphQueries,
	mcpKeys,
	mcpQueries,
	memoryKeys,
	memoryQueries,
	modelsKeys,
	modelsQueries,
	overviewKeys,
	overviewQueries,
	permissionsKeys,
	permissionsQueries,
	sandboxKeys,
	sandboxQueries,
	securityKeys,
	securityQueries,
	sessionsKeys,
	sessionsQueries,
	skillsKeys,
	skillsQueries,
	systemKeys,
	systemQueries,
	toolsKeys,
	toolsQueries,
} from "./control";

// Default UseQuery options — short stale, graceful retry.
const DEFAULTS = {
	staleTime: 5_000,
	retry: 1,
	refetchOnWindowFocus: false,
};

type Awaited_<T> = T extends Promise<infer U> ? U : T;

// ─── Overview ──────────────────────────────────────────────────────────────
export function useOverview(
	userId = "local",
): UseQueryResult<Awaited_<ReturnType<typeof overviewQueries.snapshot>>> {
	return useQuery({
		...DEFAULTS,
		queryKey: overviewKeys.snapshot(userId),
		queryFn: () => overviewQueries.snapshot(userId),
	});
}

// ─── Agents ────────────────────────────────────────────────────────────────
export function useAgents() {
	return useQuery({
		...DEFAULTS,
		queryKey: agentsKeys.list(),
		queryFn: () => agentsQueries.list(),
	});
}

// K5 (Slice 5): Agent edit mutations
export function usePatchAgent() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, patch }: { id: string; patch: Record<string, unknown> }) =>
			agentsQueries.patch(id, patch as Parameters<typeof agentsQueries.patch>[1]),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: agentsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

export function useResetAgentField() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, field }: { id: string; field: string }) =>
			agentsQueries.resetField(id, field),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: agentsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

// ─── Permissions ───────────────────────────────────────────────────────────
export function usePermissionMatrix() {
	return useQuery({
		...DEFAULTS,
		queryKey: permissionsKeys.matrix(),
		queryFn: () => permissionsQueries.matrix(),
	});
}

export function useToolCategories() {
	return useQuery({
		...DEFAULTS,
		queryKey: permissionsKeys.categories(),
		queryFn: () => permissionsQueries.categories(),
	});
}

// K6 (Slice 5): Permission cell mutations
export function usePatchPermissionCell() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (cell: { role_id: string; category_id: string; level: string }) =>
			permissionsQueries.patchCell(cell),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: permissionsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

export function useResetPermissionCell() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ roleId, categoryId }: { roleId: string; categoryId: string }) =>
			permissionsQueries.resetCell(roleId, categoryId),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: permissionsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

export function useReloadPermissions() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: () => permissionsQueries.reload(),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: permissionsKeys.all });
		},
	});
}

// ─── Skills ────────────────────────────────────────────────────────────────
export function useSkills(tier?: string) {
	return useQuery({
		...DEFAULTS,
		queryKey: skillsKeys.list(tier),
		queryFn: () => skillsQueries.list(tier),
	});
}

// K7 (Slice 5): Skills toggle persisted in backend
export function usePatchSkill() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
			skillsQueries.patch(id, { enabled }),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: skillsKeys.all });
		},
	});
}

export function useImportSkillFromGithub() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (input: {
			github_url: string;
			name?: string;
			description?: string;
			tier?: "team" | "personal";
		}) => skillsQueries.importFromGithub(input),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: skillsKeys.all });
			qc.invalidateQueries({ queryKey: toolsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

// ─── Tools ─────────────────────────────────────────────────────────────────
export function useTools(type?: string, category?: string) {
	return useQuery({
		...DEFAULTS,
		queryKey: toolsKeys.list(type, category),
		queryFn: () => toolsQueries.list(type, category),
	});
}

export function useAddToolFromUrl() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (input: { url: string; name?: string; description?: string; category?: string }) =>
			toolsQueries.addFromUrl(input),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: toolsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

// ─── Sandbox ───────────────────────────────────────────────────────────────
export function useSandboxRuns(status?: string, role?: string) {
	return useQuery({
		...DEFAULTS,
		queryKey: sandboxKeys.list(status, role),
		queryFn: () => sandboxQueries.list(status, role),
	});
}

// ─── System ────────────────────────────────────────────────────────────────
export function useSystemHealth() {
	return useQuery({
		...DEFAULTS,
		queryKey: systemKeys.health(),
		queryFn: () => systemQueries.health(),
		refetchInterval: 30_000, // auto-refresh every 30s
	});
}

// ─── API / Models ──────────────────────────────────────────────────────────
export function useLlmProviders() {
	return useQuery({
		...DEFAULTS,
		queryKey: modelsKeys.providers(),
		queryFn: () => modelsQueries.providers(),
	});
}

export function useModelRouting() {
	return useQuery({
		...DEFAULTS,
		queryKey: modelsKeys.routing(),
		queryFn: () => modelsQueries.routing(),
	});
}

export function useUtilityModels() {
	return useQuery({
		...DEFAULTS,
		queryKey: modelsKeys.utility(),
		queryFn: () => modelsQueries.utility(),
	});
}

export function useEnvVars() {
	return useQuery({
		...DEFAULTS,
		queryKey: modelsKeys.env(),
		queryFn: () => modelsQueries.env(),
	});
}

// ─── Audit ─────────────────────────────────────────────────────────────────
export function useAuditEvents(filters: Parameters<typeof auditQueries.list>[0] = {}) {
	return useQuery({
		...DEFAULTS,
		queryKey: auditKeys.list(filters),
		queryFn: () => auditQueries.list(filters),
	});
}

// ─── Sessions ──────────────────────────────────────────────────────────────
export function useSessions(activeOnly = false) {
	return useQuery({
		...DEFAULTS,
		queryKey: sessionsKeys.list(activeOnly),
		queryFn: () => sessionsQueries.list(activeOnly),
	});
}

// K8 (Slice 6): Kill session (Dev Mode only — guarded at call site)
export function useKillSession() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (threadId: string) => sessionsQueries.kill(threadId),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: sessionsKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
			qc.invalidateQueries({ queryKey: ["control", "overview"] });
		},
	});
}

// ─── MCP ───────────────────────────────────────────────────────────────────
export function useMcpServers() {
	return useQuery({
		...DEFAULTS,
		queryKey: mcpKeys.servers(),
		queryFn: () => mcpQueries.servers(),
	});
}

// ─── A2A ───────────────────────────────────────────────────────────────────
export function useA2ADelegations(status?: string) {
	return useQuery({
		...DEFAULTS,
		queryKey: a2aKeys.list(status),
		queryFn: () => a2aQueries.list(status),
	});
}

// ─── Security ──────────────────────────────────────────────────────────────
export function useSecurityPosture() {
	return useQuery({
		...DEFAULTS,
		queryKey: securityKeys.posture(),
		queryFn: () => securityQueries.posture(),
	});
}

// ─── Memory ────────────────────────────────────────────────────────────────
export function useMemoryHealth() {
	return useQuery({
		...DEFAULTS,
		queryKey: memoryKeys.health(),
		queryFn: () => memoryQueries.health(),
	});
}

export function useEpisodes(filters: Parameters<typeof memoryQueries.listEpisodes>[0] = {}) {
	return useQuery({
		...DEFAULTS,
		queryKey: memoryKeys.episodes(filters),
		queryFn: () => memoryQueries.listEpisodes(filters),
	});
}

// K4 (Slice 4): Combined nodes+edges for KG visualization
export function useKgGraph(type?: string, limit = 500) {
	return useQuery({
		...DEFAULTS,
		queryKey: memoryKeys.kgGraph(type),
		queryFn: () => kgGraphQueries.graph(type, limit),
	});
}

// K3 (Slice 3): Delete Episode mutation
export function useDeleteEpisode() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (id: string) => memoryQueries.deleteEpisode(id),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: memoryKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "overview"] });
		},
	});
}

// ─── Ingestion Status (Slice 2 — K1 /memory/ingestion polling) ───────────

export function useIngestionStatus() {
	return useQuery({
		...DEFAULTS,
		queryKey: ["ingestion", "status"] as const,
		queryFn: () => ingestionQueries.status(),
		refetchInterval: 2000,
	});
}

// ─── Ingestion Mutations (Slice 2 write path) ────────────────────────────
// Invalidate episodes + memory health after successful ingest so the UI
// reflects new data without manual refetch.

export function useIngestNote() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (input: IngestNoteInput) => ingestionQueries.ingestNote(input),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: memoryKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "overview"] });
			qc.invalidateQueries({ queryKey: ["control", "audit"] });
		},
	});
}

export function useIngestDocument() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (input: IngestDocumentInput) => ingestionQueries.ingestDocument(input),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: memoryKeys.all });
			qc.invalidateQueries({ queryKey: ["control", "overview"] });
		},
	});
}

export function useIngestLink() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (input: IngestLinkInput) => ingestionQueries.ingestLink(input),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: memoryKeys.all });
		},
	});
}

export function useReindexDocument() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ fileId, input }: { fileId: string; input?: Partial<IngestDocumentInput> }) =>
			ingestionQueries.reindex(fileId, input),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: memoryKeys.all });
		},
	});
}
