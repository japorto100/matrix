"use client";

// SkillsTab — 3-tier skills (Global / Team / Personal) from exec-10
// Slice 5.3: Skills Management
// K7 (Slice 5): enable/disable toggle wired via usePatchSkill

import { Calendar, ExternalLink, HardDrive, Package, Plus, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/queries/client";
import { useImportSkillFromGithub, usePatchSkill, useSkills } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockSkills } from "../mock-data";
import type { Skill, SkillTier } from "../types";
import {
	extractSkillsGuardVerdict,
	type SkillsGuardDecision,
	SkillsGuardDrawer,
	type SkillsGuardVerdict,
} from "./SkillsGuardDrawer";

const TIER_LABEL: Record<SkillTier, string> = {
	global: "Global",
	team: "Team",
	personal: "Personal",
};

const TIER_DESC: Record<SkillTier, string> = {
	global: "Built-in shared across all agents",
	team: "Adopted from external sources (GitHub, etc.)",
	personal: "Local custom skills (your own)",
};

function SourceIcon({ source }: { source: Skill["source"] }) {
	if (source === "builtin") return <Package className="h-3 w-3" />;
	if (source === "github") return <ExternalLink className="h-3 w-3" />;
	return <HardDrive className="h-3 w-3" />;
}

export function SkillsTab() {
	const [selected, setSelected] = useState<Skill | null>(null);
	const [importOpen, setImportOpen] = useState(false);
	const [githubUrl, setGithubUrl] = useState("");
	const [importName, setImportName] = useState("");
	const [importDescription, setImportDescription] = useState("");
	const patchSkill = usePatchSkill();
	const importSkill = useImportSkillFromGithub();
	// ADR-004: HITL drawer state for dangerous skills-guard verdicts.
	const [guardVerdict, setGuardVerdict] = useState<SkillsGuardVerdict | null>(null);

	// Slice 7 Phase H: real backend with mock fallback
	const query = useSkills();
	const skills = (query.data?.items as Skill[] | undefined) ?? mockSkills;

	const handleToggle = async (skill: Skill, next: boolean) => {
		try {
			await patchSkill.mutateAsync({ id: skill.id, enabled: next });
			toast.success(`${skill.name} → ${next ? "enabled" : "disabled"}`);
		} catch (err) {
			toast.error(`Toggle failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	const handleImport = async () => {
		if (!githubUrl.trim()) return;
		try {
			const result = await importSkill.mutateAsync({
				github_url: githubUrl.trim(),
				name: importName.trim() || undefined,
				description: importDescription.trim() || undefined,
				tier: "team",
			});
			toast.success(`Skill imported: ${result.skill_id}`);
			setImportOpen(false);
			setGithubUrl("");
			setImportName("");
			setImportDescription("");
		} catch (err) {
			// ADR-004: if the backend returned a dangerous verdict with
			// suggested_action=hitl_confirm, route to the skills-guard drawer
			// instead of a plain toast.
			if (err instanceof ApiError) {
				const verdict = extractSkillsGuardVerdict(err.body, githubUrl.trim());
				if (verdict) {
					setGuardVerdict(verdict);
					return;
				}
			}
			toast.error(`Import failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	const handleGuardDecision = (decision: SkillsGuardDecision) => {
		if (!guardVerdict) return;
		if (decision === "deny") {
			toast.info(`Import denied by user: ${guardVerdict.source}`);
			setGuardVerdict(null);
			return;
		}
		// allow_once / allow_session → placeholder until backend accepts a
		// trust_source=human_approved header on the retry (ADR-004 step 5).
		// For now surface the intent so the user sees the decision was
		// acknowledged + audit can correlate via matching timestamps.
		toast.warning(
			`${decision === "allow_once" ? "Allow-once" : "Allow-session"} not yet wired — retry will fail until backend accepts the trust_source=human_approved override. (ADR-004 step 5)`,
		);
		setGuardVerdict(null);
	};

	const grouped = useMemo(() => {
		const g: Record<SkillTier, Skill[]> = { global: [], team: [], personal: [] };
		for (const s of skills) g[s.tier].push(s);
		return g;
	}, [skills]);

	const enabled = skills.filter((s) => s.enabled).length;

	return (
		<div className="px-6 py-4 space-y-6">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Skills Library</h2>
					<p className="text-xs text-muted-foreground">
						{skills.length} skills · {enabled} enabled · 3-tier hierarchy
					</p>
				</div>
				<Button
					variant="outline"
					size="sm"
					className="h-8 gap-1.5 text-xs"
					onClick={() => setImportOpen(true)}
				>
					<Plus className="h-3 w-3" />
					Import from GitHub
				</Button>
			</header>

			{(["global", "team", "personal"] as SkillTier[]).map((tier) => (
				<section key={tier} className="space-y-2">
					<div className="flex items-baseline justify-between border-b border-border pb-1">
						<div className="flex items-baseline gap-2">
							<h3 className="text-sm font-semibold">{TIER_LABEL[tier]}</h3>
							<span className="text-[10px] text-muted-foreground">{TIER_DESC[tier]}</span>
						</div>
						<Badge variant="outline" className="text-[10px]">
							{grouped[tier].length}
						</Badge>
					</div>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
						{grouped[tier].map((skill) => (
							<Card
								key={skill.id}
								className={cn(
									"cursor-pointer hover:border-accent transition-colors",
									!skill.enabled && "opacity-60",
								)}
							>
								<CardHeader className="pb-2">
									<div className="flex items-start justify-between gap-2">
										<div onClick={() => setSelected(skill)} className="flex-1 min-w-0">
											<CardTitle className="text-sm font-mono leading-tight truncate">
												{skill.name}
											</CardTitle>
											<div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground">
												<SourceIcon source={skill.source} />
												<span>{skill.source}</span>
												<span>·</span>
												<Sparkles className="h-2.5 w-2.5" />
												<span>gen {skill.generation}</span>
											</div>
										</div>
										<Switch
											checked={skill.enabled}
											className="shrink-0"
											onClick={(e) => e.stopPropagation()}
											onCheckedChange={(next) => handleToggle(skill, next)}
											disabled={patchSkill.isPending}
										/>
									</div>
								</CardHeader>
								<CardContent className="pt-0" onClick={() => setSelected(skill)}>
									<p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
										{skill.description}
									</p>
									{skill.last_used_at && (
										<div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
											<Calendar className="h-2.5 w-2.5" />
											last used {new Date(skill.last_used_at).toLocaleDateString()}
										</div>
									)}
								</CardContent>
							</Card>
						))}
					</div>
				</section>
			))}

			<Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
				<SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
					{selected && (
						<>
							<SheetHeader>
								<SheetTitle className="font-mono">{selected.name}</SheetTitle>
								<SheetDescription>{selected.description}</SheetDescription>
							</SheetHeader>
							<div className="space-y-4 py-4">
								<div className="flex flex-wrap gap-1.5">
									<Badge variant="secondary" className="text-[10px] capitalize">
										{selected.tier}
									</Badge>
									<Badge variant="secondary" className="text-[10px]">
										generation {selected.generation}
									</Badge>
									<Badge variant="secondary" className="text-[10px] gap-1">
										<SourceIcon source={selected.source} />
										{selected.source}
									</Badge>
									{selected.enabled ? (
										<Badge
											variant="outline"
											className="text-[10px] border-emerald-500/50 text-emerald-400"
										>
											enabled
										</Badge>
									) : (
										<Badge variant="outline" className="text-[10px] border-muted-foreground/50">
											disabled
										</Badge>
									)}
								</div>

								{selected.github_url && (
									<a
										href={selected.github_url}
										target="_blank"
										rel="noopener noreferrer"
										className="flex items-center gap-1.5 text-xs text-sky-400 hover:underline"
									>
										<ExternalLink className="h-3 w-3" />
										{selected.github_url}
									</a>
								)}

								<div>
									<h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
										Body Preview
									</h3>
									<div className="rounded-lg border border-border bg-card/40 p-3 text-xs leading-relaxed font-mono whitespace-pre-wrap">
										{selected.body_preview}
									</div>
								</div>
							</div>
						</>
					)}
				</SheetContent>
			</Sheet>

			<Dialog open={importOpen} onOpenChange={setImportOpen}>
				<DialogContent className="sm:max-w-lg">
					<DialogHeader>
						<DialogTitle>Import Skill from GitHub URL</DialogTitle>
						<DialogDescription>
							Add a team-level skill from a remote GitHub source.
						</DialogDescription>
					</DialogHeader>
					<div className="space-y-3">
						<div className="space-y-1.5">
							<Label htmlFor="skill-github-url">GitHub URL</Label>
							<Input
								id="skill-github-url"
								placeholder="https://github.com/org/repo/blob/main/skills/alpha.md"
								value={githubUrl}
								onChange={(e) => setGithubUrl(e.target.value)}
							/>
						</div>
						<div className="space-y-1.5">
							<Label htmlFor="skill-name">Name (optional)</Label>
							<Input
								id="skill-name"
								placeholder="momentum-breakout-skill"
								value={importName}
								onChange={(e) => setImportName(e.target.value)}
							/>
						</div>
						<div className="space-y-1.5">
							<Label htmlFor="skill-desc">Description (optional)</Label>
							<Textarea
								id="skill-desc"
								className="min-h-[80px]"
								placeholder="Brief summary of what this skill does..."
								value={importDescription}
								onChange={(e) => setImportDescription(e.target.value)}
							/>
						</div>
					</div>
					<DialogFooter>
						<Button variant="outline" onClick={() => setImportOpen(false)}>
							Cancel
						</Button>
						<Button onClick={handleImport} disabled={!githubUrl.trim() || importSkill.isPending}>
							{importSkill.isPending ? "Importing..." : "Import"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			{/* ADR-004: Skills-Guard HITL drawer on dangerous verdict. */}
			<SkillsGuardDrawer
				open={guardVerdict !== null}
				onOpenChange={(next) => {
					if (!next) setGuardVerdict(null);
				}}
				verdict={guardVerdict}
				onDecide={handleGuardDecision}
			/>
		</div>
	);
}
