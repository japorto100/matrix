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
import type { ScheduledTaskStatus } from "@/features/control/types";
import {
	a2aKeys,
	a2aQueries,
	agentsKeys,
	agentsQueries,
	auditKeys,
	auditQueries,
	contextKeys,
	contextQueries,
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
	schedulerKeys,
	schedulerQueries,
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
	userLlmKeys,
	userLlmQueries,
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

export function useContextInspector(
	userId = "local",
): UseQueryResult<Awaited_<ReturnType<typeof contextQueries.inspector>>> {
	return useQuery({
		...DEFAULTS,
		queryKey: contextKeys.inspector(userId),
		queryFn: () => contextQueries.inspector(userId),
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

// ─── User LLM Settings (exec-16) ─────────────────────────────────────────

export function useUserLlmSettings() {
	return useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.settings(),
		queryFn: () => userLlmQueries.settings(),
	});
}

export function useModelList(filters: Record<string, string> = {}) {
	return useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.models(filters),
		queryFn: () => userLlmQueries.listModels(filters),
		staleTime: 30_000,
	});
}

export function useSelectedModels() {
	const qc = useQueryClient();
	const query = useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.selectedModels(),
		queryFn: async () => {
			const data = await userLlmQueries.getSelectedModels();
			return new Set(data.selected_models ?? []);
		},
		staleTime: 60_000,
	});

	const mutation = useMutation({
		mutationFn: (models: Set<string>) => userLlmQueries.setSelectedModels(Array.from(models)),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: userLlmKeys.selectedModels() });
		},
	});

	return {
		selected: query.data ?? new Set<string>(),
		isLoading: query.isLoading,
		save: mutation.mutateAsync,
		isSaving: mutation.isPending,
	};
}

export function useAccountInfo() {
	return useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.accountInfo(),
		queryFn: () => userLlmQueries.getAccountInfo(),
		staleTime: 60_000,
	});
}

export function useSpendActivity(startDate?: string, endDate?: string) {
	return useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.spendActivity(`${startDate}-${endDate}`),
		queryFn: () => userLlmQueries.getSpendActivity(startDate, endDate),
		staleTime: 60_000,
	});
}

export function useSpendByModel(startDate?: string, endDate?: string) {
	return useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.spendByModel(`${startDate}-${endDate}`),
		queryFn: () => userLlmQueries.getSpendByModel(startDate, endDate),
		staleTime: 60_000,
	});
}

export function useSpendByProvider() {
	return useQuery({
		...DEFAULTS,
		queryKey: userLlmKeys.spendByProvider(),
		queryFn: () => userLlmQueries.getSpendByProvider(),
		staleTime: 60_000,
	});
}

export function useSetDefaultModel() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (model: string) => userLlmQueries.setDefaultModel(model),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: userLlmKeys.all });
		},
	});
}

export function useSetRoleOverrides() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (overrides: Record<string, string>) => userLlmQueries.setRoleOverrides(overrides),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: userLlmKeys.all });
		},
	});
}

export function useSetApiKey() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({
			providerId,
			apiKey,
			maxBudget,
			budgetDuration,
			budgetCurrency,
		}: {
			providerId: string;
			apiKey: string;
			maxBudget?: number;
			budgetDuration?: string;
			budgetCurrency?: string;
		}) => userLlmQueries.setApiKey(providerId, apiKey, maxBudget, budgetDuration, budgetCurrency),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: userLlmKeys.all });
			qc.invalidateQueries({ queryKey: modelsKeys.all });
		},
	});
}

export function useDeleteApiKey() {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (providerId: string) => userLlmQueries.deleteApiKey(providerId),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: userLlmKeys.all });
			qc.invalidateQueries({ queryKey: modelsKeys.all });
		},
	});
}

export function useValidateApiKey() {
	return useMutation({
		mutationFn: ({ providerId, apiKey }: { providerId: string; apiKey: string }) =>
			userLlmQueries.validateApiKey(providerId, apiKey),
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

export function useMcpCatalog() {
	return useQuery({
		...DEFAULTS,
		queryKey: mcpKeys.catalog(),
		queryFn: () => mcpQueries.catalog(),
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

// ─── Scheduler (exec-scheduler Lane D) ────────────────────────────────────

export function useScheduledTasks(userId = "local") {
	return useQuery({
		...DEFAULTS,
		queryKey: schedulerKeys.list(userId),
		queryFn: () => schedulerQueries.list(userId),
	});
}

export function useTaskRuns(userId: string, taskId: string | null) {
	return useQuery({
		...DEFAULTS,
		queryKey: schedulerKeys.runs(taskId ?? ""),
		queryFn: () => schedulerQueries.runs(userId, taskId as string),
		enabled: !!taskId,
	});
}

export function usePatchTask(userId: string) {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: ({ taskId, status }: { taskId: string; status: ScheduledTaskStatus }) =>
			schedulerQueries.patch(userId, taskId, status),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: schedulerKeys.all });
		},
	});
}

export function useDeleteTask(userId: string) {
	const qc = useQueryClient();
	return useMutation({
		mutationFn: (taskId: string) => schedulerQueries.remove(userId, taskId),
		onSuccess: () => {
			qc.invalidateQueries({ queryKey: schedulerKeys.all });
		},
	});
}
