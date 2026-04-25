"use client";

// ADR-004: Skills-Guard HITL drawer.
// Renders when a skill import/install fails with verdict=dangerous +
// suggested_action=hitl_confirm. Shows the verdict + matched patterns
// and lets the user pick {Allow Once, Allow Session, Deny}. On approve
// the caller retries the import with trust_source=human_approved.
//
// This is deliberately a modal rather than a side-drawer: the user's
// immediate action is to decide about the blocked import, not to keep
// browsing around it. Dialog keeps the decision focused + records the
// audit-event cleanly (one CONSENT_DECISION per dangerous verdict).

import { AlertTriangle, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

export interface SkillsGuardFinding {
	pattern_id?: string;
	severity?: string;
	category?: string;
	file?: string;
	line?: number;
	excerpt?: string;
	reason?: string;
}

export interface SkillsGuardVerdict {
	/** Human-friendly origin (skill name or repo URL). */
	source: string;
	verdict: string; // "dangerous" | "caution" | "safe"
	trustLevel?: string;
	reason?: string;
	findings: SkillsGuardFinding[];
}

export type SkillsGuardDecision = "allow_once" | "allow_session" | "deny";

interface SkillsGuardDrawerProps {
	open: boolean;
	onOpenChange: (next: boolean) => void;
	verdict: SkillsGuardVerdict | null;
	onDecide: (decision: SkillsGuardDecision) => void;
	pending?: boolean;
}

const SEVERITY_COLOR: Record<string, string> = {
	critical: "border-red-500/60 text-red-400 bg-red-500/10",
	high: "border-orange-500/60 text-orange-400 bg-orange-500/10",
	medium: "border-amber-500/50 text-amber-400 bg-amber-500/10",
	low: "border-yellow-500/40 text-yellow-300 bg-yellow-500/5",
};

export function SkillsGuardDrawer({
	open,
	onOpenChange,
	verdict,
	onDecide,
	pending = false,
}: SkillsGuardDrawerProps) {
	if (!verdict) return null;
	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-2xl">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<ShieldAlert className="h-4 w-4 text-red-500" />
						Skills Guard blocked import
					</DialogTitle>
					<DialogDescription className="text-xs">
						<span className="font-mono">{verdict.source}</span> tripped the skills-guard static scan
						with verdict{" "}
						<Badge variant="outline" className="ml-1 text-[10px] border-red-500/50 text-red-400">
							{verdict.verdict}
						</Badge>
						{verdict.trustLevel && (
							<span className="ml-2 text-muted-foreground">
								(trust level: <span className="font-mono">{verdict.trustLevel}</span>)
							</span>
						)}
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-2 text-[11px]">
					{verdict.reason && (
						<div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-red-300">
							<strong className="mr-1">Reason:</strong>
							{verdict.reason}
						</div>
					)}
					<div className="text-muted-foreground">
						Allowing this will re-import the skill with{" "}
						<code className="font-mono">trust_source=human_approved</code> so the guard skips the
						block. This decision is audit-logged (
						<code className="font-mono">CONSENT_DECISION</code>).
					</div>
				</div>

				<div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
					<div className="text-[11px] font-semibold text-muted-foreground">
						Findings ({verdict.findings.length})
					</div>
					{verdict.findings.length === 0 && (
						<div className="text-[10px] text-muted-foreground italic">
							No per-finding details returned.
						</div>
					)}
					{verdict.findings.map((f, idx) => {
						const sev = (f.severity ?? "medium").toLowerCase();
						return (
							<div
								key={`${f.pattern_id ?? "finding"}-${idx}`}
								className={`rounded border px-2 py-1.5 text-[10px] font-mono leading-relaxed ${SEVERITY_COLOR[sev] ?? SEVERITY_COLOR.medium}`}
							>
								<div className="flex items-center justify-between">
									<span>
										<AlertTriangle className="inline h-2.5 w-2.5 mr-1" />
										{f.pattern_id ?? "unknown_pattern"}
										{f.category && (
											<span className="ml-1 text-muted-foreground">· {f.category}</span>
										)}
									</span>
									<Badge variant="outline" className="text-[8px] h-3.5 px-1">
										{sev}
									</Badge>
								</div>
								{f.file && (
									<div className="text-muted-foreground">
										{f.file}
										{typeof f.line === "number" ? `:${f.line}` : ""}
									</div>
								)}
								{f.excerpt && (
									<div className="truncate text-muted-foreground/80">
										<span className="opacity-60">↳</span> {f.excerpt}
									</div>
								)}
								{f.reason && <div className="text-muted-foreground/70 mt-0.5">{f.reason}</div>}
							</div>
						);
					})}
				</div>

				<DialogFooter className="flex-wrap gap-2">
					<Button variant="ghost" size="sm" onClick={() => onDecide("deny")} disabled={pending}>
						Deny
					</Button>
					<Button
						variant="outline"
						size="sm"
						onClick={() => onDecide("allow_session")}
						disabled={pending}
					>
						Allow this session
					</Button>
					<Button
						variant="default"
						size="sm"
						onClick={() => onDecide("allow_once")}
						disabled={pending}
						className="bg-red-600 hover:bg-red-700 text-white"
					>
						Allow once (import)
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

/**
 * Utility: inspect an ApiError body and, if it's the skills-guard HITL
 * shape, extract the verdict. Returns null otherwise.
 */
export function extractSkillsGuardVerdict(
	body: unknown,
	source: string,
): SkillsGuardVerdict | null {
	if (!body || typeof body !== "object") return null;
	const root = body as Record<string, unknown>;
	const obj =
		root.detail && typeof root.detail === "object"
			? (root.detail as Record<string, unknown>)
			: root;
	if (obj.suggested_action !== "hitl_confirm") return null;

	// Shape from /skills/import (multi-rejection):
	//   {success:false, rejected: [{name, verdict, findings, reason}], suggested_action}
	if (Array.isArray(obj.rejected) && obj.rejected.length > 0) {
		const first = obj.rejected.find(
			(r): r is Record<string, unknown> =>
				typeof r === "object" &&
				r !== null &&
				(r as Record<string, unknown>).verdict === "dangerous",
		);
		if (first) {
			return {
				source: typeof first.name === "string" ? first.name : source,
				verdict: String(first.verdict ?? "dangerous"),
				trustLevel: typeof first.trust_level === "string" ? first.trust_level : undefined,
				reason: typeof first.reason === "string" ? first.reason : undefined,
				findings: Array.isArray(first.findings) ? (first.findings as SkillsGuardFinding[]) : [],
			};
		}
	}

	// Shape from /skills/install (single skill):
	//   {success:false, skill_name, verdict, findings, suggested_action}
	if (obj.verdict === "dangerous") {
		return {
			source: typeof obj.skill_name === "string" ? obj.skill_name : source,
			verdict: "dangerous",
			trustLevel: typeof obj.trust_level === "string" ? obj.trust_level : undefined,
			reason: typeof obj.message === "string" ? obj.message : undefined,
			findings: Array.isArray(obj.findings) ? (obj.findings as SkillsGuardFinding[]) : [],
		};
	}

	return null;
}
