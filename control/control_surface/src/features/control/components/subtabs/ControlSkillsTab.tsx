"use client";

// AC10 — Skills Tab: registered skill registry (read-only v1).

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, Puzzle } from "lucide-react";
import { getErrorMessage } from "@/lib/utils";

interface Skill {
	id: string;
	name: string;
	description: string;
	enabled: boolean;
	version: string;
	lastUsedAt: string | null;
}

interface SkillsData {
	skills: Skill[];
	degraded?: boolean;
	degraded_reasons?: string[];
}

export function ControlSkillsTab() {
	const { data, isLoading, error } = useQuery<SkillsData>({
		queryKey: ["control", "skills"],
		queryFn: async () => {
			const res = await fetch("/api/control/skills", { cache: "no-store" });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.json() as Promise<SkillsData>;
		},
		staleTime: 30_000,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground text-sm">
				<Loader2 className="h-4 w-4 animate-spin" />
				Loading skills…
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 text-destructive text-sm">
				<AlertCircle className="h-4 w-4" />
				{getErrorMessage(error)}
			</div>
		);
	}

	const skills = data?.skills ?? [];

	return (
		<div className="p-4 space-y-3">
			<div className="flex items-center justify-between">
				<h2 className="text-sm font-semibold text-foreground">Skills</h2>
				<div className="flex items-center gap-2">
					{data?.degraded && (
						<span className="text-[10px] font-mono text-amber-500">
							{data.degraded_reasons?.join(", ")}
						</span>
					)}
					<span className="text-xs text-muted-foreground">{skills.length} registered</span>
				</div>
			</div>

			{skills.length === 0 ? (
				<div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
					<Puzzle className="h-8 w-8 opacity-20" />
					<span className="text-sm">No skills registered</span>
				</div>
			) : (
				<div className="space-y-1.5">
					{skills.map((s) => (
						<div
							key={s.id}
							className="rounded-lg border border-border bg-card px-3 py-2.5 flex items-start gap-3"
						>
							<Puzzle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-muted-foreground" />
							<div className="flex-1 min-w-0">
								<div className="flex items-center gap-2">
									<span className="text-xs font-semibold text-foreground">{s.name}</span>
									<span className="text-[9px] font-mono text-muted-foreground/60">
										v{s.version}
									</span>
									<span
										className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
											s.enabled
												? "bg-emerald-500/20 text-emerald-400"
												: "bg-muted text-muted-foreground"
										}`}
									>
										{s.enabled ? "on" : "off"}
									</span>
								</div>
								<p className="text-[10px] text-muted-foreground/70 truncate mt-0.5">
									{s.description}
								</p>
							</div>
							{s.lastUsedAt && (
								<span className="text-[10px] text-muted-foreground/40 shrink-0">
									{new Date(s.lastUsedAt).toLocaleTimeString()}
								</span>
							)}
						</div>
					))}
				</div>
			)}
		</div>
	);
}
