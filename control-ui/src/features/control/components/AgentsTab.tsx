"use client";

// AgentsTab — list of trading roles + click for editor sheet
// Slice 5.1 + Phase H: useQuery with mock fallback
// K5 (Slice 5): Edit mode with usePatchAgent + useResetAgentField

import { CheckCircle2, Lock, MemoryStick, Pencil, Undo2, Wrench, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useAgents, usePatchAgent, useResetAgentField } from "@/lib/queries/hooks";
import { mockAgentRoles } from "../mock-data";
import type { AgentRole, MemoryAccess } from "../types";

export function AgentsTab() {
	const [selected, setSelected] = useState<AgentRole | null>(null);
	const [editing, setEditing] = useState(false);
	const [draftPrompt, setDraftPrompt] = useState("");
	const [draftMemoryAccess, setDraftMemoryAccess] = useState<MemoryAccess>("read");
	const [draftApprovalRequired, setDraftApprovalRequired] = useState(false);
	const patchAgent = usePatchAgent();
	const resetField = useResetAgentField();

	const { data, isError } = useAgents();
	const roles = (data?.items as AgentRole[] | undefined) ?? mockAgentRoles;

	// Reset draft state when a new role is selected or sheet closes
	useEffect(() => {
		if (selected) {
			setDraftPrompt(selected.system_prompt);
			setDraftMemoryAccess(selected.memory_access);
			setDraftApprovalRequired(selected.approval_required);
			setEditing(false);
		}
	}, [selected]);

	const handleSave = async () => {
		if (!selected) return;
		const patch: Record<string, unknown> = {};
		if (draftPrompt !== selected.system_prompt) patch.system_prompt = draftPrompt;
		if (draftMemoryAccess !== selected.memory_access) patch.memory_access = draftMemoryAccess;
		if (draftApprovalRequired !== selected.approval_required)
			patch.approval_required = draftApprovalRequired;
		if (Object.keys(patch).length === 0) {
			toast.info("No changes to save");
			setEditing(false);
			return;
		}
		try {
			await patchAgent.mutateAsync({ id: selected.id, patch });
			toast.success(`Saved overrides for ${selected.display_name}`);
			setEditing(false);
			setSelected(null);
		} catch (err) {
			toast.error(`Save failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	const handleResetField = async (field: string) => {
		if (!selected) return;
		try {
			await resetField.mutateAsync({ id: selected.id, field });
			toast.success(`Reset ${field} to default`);
			setSelected(null);
		} catch (err) {
			toast.error(`Reset failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Trading Roles</h2>
					<p className="text-xs text-muted-foreground">
						{roles.length} roles · {roles.filter((r) => !r.is_default).length} with overrides
						{isError && (
							<span className="ml-2 text-amber-400">· backend offline (showing mock data)</span>
						)}
					</p>
				</div>
			</header>

			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				{roles.map((role) => (
					<Card
						key={role.id}
						className="cursor-pointer hover:border-accent transition-colors"
						onClick={() => setSelected(role)}
					>
						<CardHeader className="pb-2">
							<div className="flex items-start justify-between gap-2">
								<CardTitle className="text-sm font-semibold leading-tight">
									{role.display_name}
								</CardTitle>
								{!role.is_default && (
									<Badge
										variant="outline"
										className="text-[10px] h-5 border-amber-500/50 text-amber-400"
									>
										overridden
									</Badge>
								)}
							</div>
							<code className="text-[10px] text-muted-foreground">{role.id}</code>
						</CardHeader>
						<CardContent className="space-y-2 pt-0">
							<p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
								{role.system_prompt}
							</p>
							<div className="flex flex-wrap gap-1.5 pt-1">
								<Badge variant="secondary" className="text-[10px] h-5 gap-1">
									<Wrench className="h-2.5 w-2.5" />
									{role.allowed_tools[0] === "*"
										? "all tools"
										: `${role.allowed_tools.length} tools`}
								</Badge>
								<Badge variant="secondary" className="text-[10px] h-5 gap-1">
									<MemoryStick className="h-2.5 w-2.5" />
									{role.memory_access}
								</Badge>
								{role.approval_required && (
									<Badge variant="secondary" className="text-[10px] h-5 gap-1">
										<Lock className="h-2.5 w-2.5" />
										approval
									</Badge>
								)}
							</div>
						</CardContent>
					</Card>
				))}
			</div>

			<Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
				<SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
					{selected && (
						<>
							<SheetHeader>
								<div className="flex items-start justify-between gap-2">
									<div>
										<SheetTitle>{selected.display_name}</SheetTitle>
										<SheetDescription className="font-mono text-xs">{selected.id}</SheetDescription>
									</div>
									{!selected.is_default && (
										<Badge
											variant="outline"
											className="text-[10px] border-amber-500/50 text-amber-400"
										>
											has overrides
										</Badge>
									)}
								</div>
							</SheetHeader>

							<div className="space-y-6 py-4">
								<section>
									<div className="flex items-center justify-between mb-2">
										<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
											System Prompt
										</h3>
										{!editing ? (
											<Button
												variant="ghost"
												size="sm"
												className="h-6 text-xs gap-1"
												onClick={() => setEditing(true)}
											>
												<Pencil className="h-3 w-3" />
												Edit
											</Button>
										) : (
											<Button
												variant="ghost"
												size="sm"
												className="h-6 text-xs gap-1"
												onClick={() => {
													setDraftPrompt(selected.system_prompt);
													setDraftMemoryAccess(selected.memory_access);
													setDraftApprovalRequired(selected.approval_required);
													setEditing(false);
												}}
											>
												<X className="h-3 w-3" />
												Cancel
											</Button>
										)}
									</div>
									{editing ? (
										<Textarea
											value={draftPrompt}
											onChange={(e) => setDraftPrompt(e.target.value)}
											rows={10}
											className="text-xs font-mono leading-relaxed"
										/>
									) : (
										<div className="rounded-lg border border-border bg-card/40 p-3 text-xs leading-relaxed font-mono whitespace-pre-wrap">
											{selected.system_prompt}
										</div>
									)}
								</section>

								<section>
									<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
										Allowed Tools
									</h3>
									<div className="flex flex-wrap gap-1.5">
										{selected.allowed_tools.map((tool) => (
											<Badge key={tool} variant="outline" className="text-[10px] font-mono">
												{tool}
											</Badge>
										))}
									</div>
									<p className="text-[10px] text-muted-foreground/70 mt-2">
										Tool selection editor is Phase 2 (multi-select with Command primitive).
									</p>
								</section>

								<section className="grid grid-cols-2 gap-4">
									<div>
										<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
											Memory Access
										</h3>
										{editing ? (
											<RadioGroup
												value={draftMemoryAccess}
												onValueChange={(v) => setDraftMemoryAccess(v as MemoryAccess)}
												className="flex flex-col gap-1.5"
											>
												{(["read", "read_write", "none"] as MemoryAccess[]).map((lvl) => (
													<div key={lvl} className="flex items-center gap-2">
														<RadioGroupItem value={lvl} id={`mem-${lvl}`} />
														<Label
															htmlFor={`mem-${lvl}`}
															className="text-xs font-mono cursor-pointer"
														>
															{lvl}
														</Label>
													</div>
												))}
											</RadioGroup>
										) : (
											<Badge variant="secondary" className="capitalize">
												{selected.memory_access}
											</Badge>
										)}
									</div>
									<div>
										<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
											Approval Required
										</h3>
										{editing ? (
											<div className="flex items-center gap-2">
												<Switch
													checked={draftApprovalRequired}
													onCheckedChange={setDraftApprovalRequired}
												/>
												<span className="text-xs font-mono text-muted-foreground">
													{draftApprovalRequired ? "required" : "disabled"}
												</span>
											</div>
										) : (
											<div className="flex items-center gap-1.5 text-sm">
												{selected.approval_required ? (
													<>
														<Lock className="h-3.5 w-3.5 text-amber-400" />
														<span>Yes</span>
													</>
												) : (
													<>
														<CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
														<span>No</span>
													</>
												)}
											</div>
										)}
									</div>
								</section>

								{editing && (
									<section className="flex items-center gap-2 pt-2 border-t border-border">
										<Button onClick={handleSave} disabled={patchAgent.isPending} size="sm">
											{patchAgent.isPending ? "Saving..." : "Save Overrides"}
										</Button>
										{!selected.is_default && (
											<>
												<Button
													variant="ghost"
													size="sm"
													className="gap-1.5"
													onClick={() => handleResetField("system_prompt")}
													disabled={resetField.isPending}
												>
													<Undo2 className="h-3 w-3" />
													Reset Prompt
												</Button>
												<Button
													variant="ghost"
													size="sm"
													className="gap-1.5"
													onClick={() => handleResetField("memory_access")}
													disabled={resetField.isPending}
												>
													<Undo2 className="h-3 w-3" />
													Reset Memory
												</Button>
											</>
										)}
									</section>
								)}

								{selected.updated_at && (
									<section>
										<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
											Override History
										</h3>
										<p className="text-xs text-muted-foreground">
											Last updated by{" "}
											<code className="text-foreground">{selected.updated_by ?? "?"}</code> at{" "}
											{new Date(selected.updated_at).toLocaleString()}
										</p>
									</section>
								)}
							</div>
						</>
					)}
				</SheetContent>
			</Sheet>
		</div>
	);
}
