"use client";

// ApiModelsTab — exec-16: Interactive LLM provider config
// Provider cards with key management, dynamic model discovery, default model picker

import {
	Box,
	Cloud,
	HardDrive,
	Key,
	Lock,
	RefreshCw,
	Search,
	Server,
	Sparkles,
	TestTube,
	Trash2,
	Workflow,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
	useDeleteApiKey,
	useEnvVars,
	useModelRouting,
	useSetDefaultModel,
	useSetRoleOverrides,
	useUserLlmSettings,
	useUtilityModels,
} from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import {
	mockAgentRoles,
	mockEnvVars,
	mockModelRouting,
	mockUtilityModels,
} from "../mock-data";
import type { EnvVar, LlmProvider, ModelRouting, UtilityModel, UtilityPurpose } from "../types";
import { EditApiKeyModal } from "./EditApiKeyModal";

const UTILITY_ICON: Record<UtilityPurpose, React.ReactNode> = {
	embedder_text: <Box className="h-3.5 w-3.5" />,
	embedder_visual: <Sparkles className="h-3.5 w-3.5" />,
	reranker: <Workflow className="h-3.5 w-3.5" />,
	summarizer: <Workflow className="h-3.5 w-3.5" />,
	stt: <TestTube className="h-3.5 w-3.5" />,
	tts: <TestTube className="h-3.5 w-3.5" />,
};

export function ApiModelsTab() {
	const [envFilter, setEnvFilter] = useState("");
	const [editProvider, setEditProvider] = useState<LlmProvider | null>(null);

	// exec-16: User LLM settings (live from backend)
	const llmQuery = useUserLlmSettings();
	const routingQuery = useModelRouting();
	const utilityQuery = useUtilityModels();
	const envQuery = useEnvVars();
	const setDefaultModel = useSetDefaultModel();
	const setRoleOverrides = useSetRoleOverrides();
	const deleteKey = useDeleteApiKey();

	// Data with mock fallback
	const providers = llmQuery.data?.providers ?? [];
	const defaultModel = llmQuery.data?.default_model ?? null;
	const routing = (routingQuery.data?.items as ModelRouting[] | undefined) ?? mockModelRouting;
	const utility = (utilityQuery.data?.items as UtilityModel[] | undefined) ?? mockUtilityModels;
	const envVars = (envQuery.data?.items as EnvVar[] | undefined) ?? mockEnvVars;

	// All available models across all active providers
	const allModels = useMemo(() => {
		const models: { model: string; provider: string }[] = [];
		for (const p of providers) {
			if (!p.is_active) continue;
			for (const m of p.available_models) {
				models.push({ model: m, provider: p.display_name });
			}
		}
		return models;
	}, [providers]);

	const providerById = useMemo(() => {
		const m: Record<string, LlmProvider> = {};
		for (const p of providers) m[p.id] = p;
		return m;
	}, [providers]);

	const filteredEnv = useMemo(() => {
		if (!envFilter) return envVars;
		const f = envFilter.toLowerCase();
		return envVars.filter(
			(v) => v.key.toLowerCase().includes(f) || v.description?.toLowerCase().includes(f),
		);
	}, [envFilter, envVars]);

	const activeCount = providers.filter((p) => p.is_active).length;
	const sensitiveCount = envVars.filter((v) => v.is_sensitive).length;

	const handleSetDefault = async (model: string) => {
		try {
			await setDefaultModel.mutateAsync(model);
			toast.success(`Default model: ${model}`);
		} catch {
			toast.error("Failed to set default model");
		}
	};

	const handleDeleteKey = async (provider: LlmProvider) => {
		try {
			await deleteKey.mutateAsync(provider.id);
			toast.success(`Key for ${provider.display_name} removed`);
		} catch {
			toast.error("Failed to delete key");
		}
	};

	return (
		<div className="px-6 py-4 space-y-6">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">API &amp; Models</h2>
					<p className="text-xs text-muted-foreground">
						LLM providers, model routing, embedders, env config
					</p>
				</div>
				<div className="flex items-center gap-2">
					<Button
						variant="ghost"
						size="sm"
						className="h-6 text-[10px] gap-1"
						onClick={() => llmQuery.refetch()}
						disabled={llmQuery.isFetching}
					>
						<RefreshCw className={cn("h-2.5 w-2.5", llmQuery.isFetching && "animate-spin")} />
						Refresh
					</Button>
					<Badge variant="outline" className="text-[10px]">
						{activeCount}/{providers.length} providers active
					</Badge>
				</div>
			</header>

			{/* ─── Default Model Picker ────────────────────────────────── */}
			{allModels.length > 0 && (
				<section className="space-y-2">
					<div className="flex items-baseline justify-between border-b border-border pb-1">
						<h3 className="text-sm font-semibold flex items-center gap-2">
							<Sparkles className="h-3.5 w-3.5" />
							Default Model
						</h3>
						{defaultModel && (
							<code className="text-[11px] text-muted-foreground font-mono">{defaultModel}</code>
						)}
					</div>
					<div className="flex flex-wrap gap-1.5">
						{allModels.slice(0, 20).map(({ model, provider }) => (
							<Button
								key={model}
								variant={model === defaultModel ? "default" : "outline"}
								size="sm"
								className="h-6 text-[10px] gap-1"
								onClick={() => handleSetDefault(model)}
								disabled={setDefaultModel.isPending}
							>
								{model}
								<span className="text-[9px] opacity-60">({provider})</span>
							</Button>
						))}
						{allModels.length > 20 && (
							<span className="text-[10px] text-muted-foreground self-center">
								+{allModels.length - 20} more
							</span>
						)}
					</div>
				</section>
			)}

			{/* ─── Section 1: LLM Providers ─────────────────────────────── */}
			<section className="space-y-2">
				<div className="flex items-baseline justify-between border-b border-border pb-1">
					<h3 className="text-sm font-semibold flex items-center gap-2">
						<Server className="h-3.5 w-3.5" />
						LLM Providers
					</h3>
					<span className="text-[10px] text-muted-foreground">
						Click &quot;Set Key&quot; to configure
					</span>
				</div>
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					{providers.map((provider) => (
						<Card
							key={provider.id}
							className={cn(
								"transition-colors",
								provider.is_active && "border-emerald-500/30 bg-emerald-950/5",
							)}
						>
							<CardHeader className="pb-2">
								<div className="flex items-start justify-between gap-2">
									<div className="flex items-center gap-2">
										{provider.type === "cloud" ? (
											<Cloud className="h-3.5 w-3.5 text-sky-400" />
										) : (
											<HardDrive className="h-3.5 w-3.5 text-amber-400" />
										)}
										<CardTitle className="text-sm font-semibold leading-tight">
											{provider.display_name}
										</CardTitle>
									</div>
									{provider.is_active ? (
										<Badge
											variant="outline"
											className="text-[9px] h-4 px-1.5 border-emerald-500/50 text-emerald-400"
										>
											active
										</Badge>
									) : (
										<Badge variant="outline" className="text-[9px] h-4 px-1.5">
											inactive
										</Badge>
									)}
								</div>
							</CardHeader>
							<CardContent className="space-y-2 pt-0">
								{provider.api_key_set && provider.api_key_preview && (
									<div className="flex items-center gap-1.5 text-[11px]">
										<Key className="h-3 w-3 text-muted-foreground" />
										<code className="font-mono text-amber-300">{provider.api_key_preview}</code>
									</div>
								)}
								{provider.available_models.length > 0 && (
									<div className="text-[10px] text-muted-foreground">
										{provider.available_models.length} model
										{provider.available_models.length === 1 ? "" : "s"} available
									</div>
								)}
								<div className="flex gap-1 pt-1">
									<Button
										variant="outline"
										size="sm"
										className="h-6 text-[10px] gap-1"
										onClick={() => setEditProvider(provider)}
									>
										<Key className="h-2.5 w-2.5" />
										{provider.api_key_set ? "Change Key" : "Set Key"}
									</Button>
									{provider.api_key_set && (
										<Button
											variant="outline"
											size="sm"
											className="h-6 text-[10px] gap-1 text-red-400 hover:text-red-300"
											onClick={() => handleDeleteKey(provider)}
											disabled={deleteKey.isPending}
										>
											<Trash2 className="h-2.5 w-2.5" />
											Remove
										</Button>
									)}
								</div>
							</CardContent>
						</Card>
					))}
				</div>
			</section>

			{/* ─── Section 2: Model Routing per Role ────────────────────── */}
			<section className="space-y-2">
				<div className="flex items-baseline justify-between border-b border-border pb-1">
					<h3 className="text-sm font-semibold flex items-center gap-2">
						<Workflow className="h-3.5 w-3.5" />
						Model Routing
					</h3>
					<span className="text-[10px] text-muted-foreground">
						Per Trading Role — select model override
					</span>
				</div>
				<div className="rounded-lg border border-border overflow-hidden">
					<table className="w-full text-xs">
						<thead className="bg-card/40">
							<tr className="text-left">
								<th className="py-2 px-3 font-semibold">Role</th>
								<th className="py-2 px-3 font-semibold">Model Override</th>
								<th className="py-2 px-3 font-semibold w-20 text-center">Status</th>
							</tr>
						</thead>
						<tbody>
							{mockAgentRoles.map((role) => {
								const currentRouting = routing.find((r) => r.role_id === role.id);
								const currentModel = currentRouting?.model_id ?? defaultModel ?? "";
								return (
									<tr key={role.id} className="border-t border-border hover:bg-card/20">
										<td className="py-2 px-3">
											<div className="font-medium">{role.display_name}</div>
											<code className="text-[10px] text-muted-foreground">{role.id}</code>
										</td>
										<td className="py-2 px-3">
											<select
												className="w-full bg-transparent border border-border rounded px-2 py-1 text-[11px] font-mono focus:outline-none focus:ring-1 focus:ring-ring"
												value={currentModel}
												onChange={async (e) => {
													const newModel = e.target.value;
													const overrides: Record<string, string> = {};
													for (const r of mockAgentRoles) {
														const existing = routing.find((rt) => rt.role_id === r.id);
														if (r.id === role.id) {
															if (newModel && newModel !== (defaultModel ?? "")) {
																overrides[r.id] = newModel;
															}
														} else if (existing && !existing.is_default) {
															overrides[r.id] = existing.model_id;
														}
													}
													try {
														await setRoleOverrides.mutateAsync(overrides);
														toast.success(`${role.display_name} → ${newModel || "default"}`);
													} catch {
														toast.error("Failed to update routing");
													}
												}}
											>
												<option value="">
													(default: {defaultModel ?? "none"})
												</option>
												{allModels.map(({ model }) => (
													<option key={model} value={model}>
														{model}
													</option>
												))}
											</select>
										</td>
										<td className="py-2 px-3 text-center">
											{currentRouting && !currentRouting.is_default ? (
												<Badge
													variant="outline"
													className="text-[9px] h-4 px-1.5 border-amber-500/50 text-amber-400"
												>
													override
												</Badge>
											) : (
												<Badge variant="outline" className="text-[9px] h-4 px-1.5">
													default
												</Badge>
											)}
										</td>
									</tr>
								);
							})}
						</tbody>
					</table>
				</div>
			</section>

			{/* ─── Section 3: Utility Models ────────────────────────────── */}
			<section className="space-y-2">
				<div className="flex items-baseline justify-between border-b border-border pb-1">
					<h3 className="text-sm font-semibold flex items-center gap-2">
						<Sparkles className="h-3.5 w-3.5" />
						Utility Models
					</h3>
					<span className="text-[10px] text-muted-foreground">Embedder, reranker, STT, TTS</span>
				</div>
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					{utility.map((u) => (
						<Card key={u.purpose} className={cn(!u.is_active && "opacity-60")}>
							<CardHeader className="pb-2">
								<div className="flex items-start justify-between gap-2">
									<div className="flex items-center gap-1.5">
										{UTILITY_ICON[u.purpose]}
										<CardTitle className="text-xs font-semibold leading-tight">
											{u.display_name}
										</CardTitle>
									</div>
									{u.is_local ? (
										<Badge variant="outline" className="text-[9px] h-4 px-1.5">
											local
										</Badge>
									) : (
										<Badge
											variant="outline"
											className="text-[9px] h-4 px-1.5 border-sky-500/50 text-sky-400"
										>
											cloud
										</Badge>
									)}
								</div>
							</CardHeader>
							<CardContent className="space-y-1 pt-0">
								<code className="text-[10px] text-muted-foreground font-mono line-clamp-1">
									{u.model_id}
								</code>
								{u.notes && (
									<div className="text-[10px] text-muted-foreground leading-relaxed">{u.notes}</div>
								)}
							</CardContent>
						</Card>
					))}
				</div>
			</section>

			{/* ─── Section 4: ENV Variables ─────────────────────────────── */}
			<section className="space-y-2">
				<div className="flex items-baseline justify-between border-b border-border pb-1">
					<h3 className="text-sm font-semibold flex items-center gap-2">
						<Lock className="h-3.5 w-3.5" />
						Environment Variables
					</h3>
					<div className="flex items-center gap-2">
						<span className="text-[10px] text-muted-foreground">
							{sensitiveCount} sensitive
						</span>
						<div className="relative">
							<Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
							<Input
								placeholder="Filter..."
								value={envFilter}
								onChange={(e) => setEnvFilter(e.target.value)}
								className="pl-6 h-7 w-40 text-[11px]"
							/>
						</div>
					</div>
				</div>
				<div className="rounded-lg border border-border overflow-hidden">
					<table className="w-full text-xs">
						<tbody>
							{filteredEnv.map((env) => (
								<tr
									key={env.key}
									className="border-t border-border first:border-t-0 hover:bg-card/20"
								>
									<td className="py-2 px-3 align-top w-1/3">
										<div className="font-mono text-[11px] font-medium">{env.key}</div>
										{env.description && (
											<div className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">
												{env.description}
											</div>
										)}
									</td>
									<td className="py-2 px-3 align-top">
										<code
											className={
												env.is_sensitive
													? "font-mono text-[11px] text-amber-300"
													: "font-mono text-[11px] text-foreground"
											}
										>
											{env.value}
										</code>
									</td>
									<td className="py-2 px-3 align-top w-24">
										<div className="flex flex-wrap gap-1">
											{env.is_sensitive && (
												<Badge
													variant="outline"
													className="text-[9px] h-4 px-1.5 border-amber-500/50 text-amber-400"
												>
													sensitive
												</Badge>
											)}
											<Badge variant="secondary" className="text-[9px] h-4 px-1.5">
												{env.source}
											</Badge>
										</div>
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</section>

			{/* Edit API Key Modal */}
			<EditApiKeyModal
				provider={editProvider}
				open={!!editProvider}
				onOpenChange={(open) => !open && setEditProvider(null)}
			/>
		</div>
	);
}
