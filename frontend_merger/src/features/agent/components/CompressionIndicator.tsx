"use client";

// exec-06 §4c Phase 5 — Compression Indicator
// Status-dot in chat-header showing current context-window fill stage.
// Green: normal (<80%), Yellow: compaction (80-85%), Red: emergency (>95%).
// Click to expand for threshold details + current usage. Enterprise
// auditability: every compression is user-visible, not seamless-magic.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface CompressionStatus {
	thread_id?: string | null;
	model?: string | null;
	window?: number;
	thresholds?: { pre_save: number; compaction: number; emergency: number };
	stage?: "normal" | "pre_save" | "compaction" | "emergency" | string;
	engine?: string;
}

interface CompressionIndicatorProps {
	/** Current selected model id — drives the context-window lookup. */
	model?: string;
	/** Latest total-tokens for the current turn (from message-metadata). */
	totalTokens?: number;
	/** Optional thread id — passed through to the endpoint for future stateful flows. */
	threadId?: string;
}

type Stage = "normal" | "pre_save" | "compaction" | "emergency";

function stageFromPct(
	pct: number,
	thresholds: { pre_save: number; compaction: number; emergency: number },
): Stage {
	if (pct >= thresholds.emergency) return "emergency";
	if (pct >= thresholds.compaction) return "compaction";
	if (pct >= thresholds.pre_save) return "pre_save";
	return "normal";
}

// Context-pipeline taxonomy (see exec-context.md §11, exec-memory.md §3h):
// - compaction (mechanical, no LLM, tool-result truncation, idempotent, NO archive)
// - compression (LLM summary, lossy, MemPalace verbatim-archive fires BEFORE)
// - clear (user action, separate concept; not represented here)
const STAGE_META: Record<
	Stage,
	{ color: string; label: string; title: string; detail: string; archivedBeforeAction: boolean }
> = {
	normal: {
		color: "bg-emerald-500",
		label: "normal",
		title: "Context usage normal — plenty of room.",
		detail: "No context-pressure actions fire in this range.",
		archivedBeforeAction: false,
	},
	pre_save: {
		color: "bg-lime-500",
		label: "pre-save",
		title: "Pre-save checkpoint — archive hook eligible.",
		detail:
			"Usage ≥80%. Archive providers (MemPalace verbatim, Hindsight facts) may trigger persistence here before any destructive compression op.",
		archivedBeforeAction: false,
	},
	compaction: {
		color: "bg-amber-500",
		label: "compaction",
		title: "Compaction active — mechanical prune (no LLM).",
		detail:
			"Usage ≥85%. Tool-results get truncated idempotently. No LLM cost, no history loss — semantic message content preserved. No archive needed because nothing is destroyed.",
		archivedBeforeAction: false,
	},
	emergency: {
		color: "bg-red-500",
		label: "emergency · compression",
		title: "Emergency LLM compression — rolling summary replaces old turns.",
		detail:
			"Usage ≥95%. An LLM generates a summary that replaces the oldest messages — lossy. MemPalace archives verbatim BEFORE the summary is produced (pre_compression hook, 500 ms timeout). Raw pre-compression history is retrievable from the archive.",
		archivedBeforeAction: true,
	},
};

export function CompressionIndicator({ model, totalTokens, threadId }: CompressionIndicatorProps) {
	const [status, setStatus] = useState<CompressionStatus | null>(null);
	const [open, setOpen] = useState(false);

	const load = useCallback(async () => {
		const params = new URLSearchParams();
		if (threadId) params.set("thread_id", threadId);
		if (model) params.set("model", model);
		const url = `/api/agent/compression-status${params.size > 0 ? `?${params.toString()}` : ""}`;
		try {
			const res = await fetch(url, { headers: { accept: "application/json" } });
			if (!res.ok) return;
			const data: CompressionStatus = await res.json();
			setStatus(data);
		} catch {
			// Fail-soft — indicator just doesn't render until we have data.
		}
	}, [model, threadId]);

	useEffect(() => {
		void load();
	}, [load]);

	const thresholds = status?.thresholds ?? { pre_save: 0.8, compaction: 0.85, emergency: 0.95 };
	const window = status?.window ?? 200_000;
	const pct = useMemo(() => {
		if (!totalTokens || !window || window <= 0) return 0;
		return Math.max(0, Math.min(1, totalTokens / window));
	}, [totalTokens, window]);
	const stage: Stage = pct > 0 ? stageFromPct(pct, thresholds) : "normal";
	const meta = STAGE_META[stage];

	if (!status) return null;

	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<button
					type="button"
					className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] text-muted-foreground hover:bg-muted/50 transition-colors"
					title={meta.title}
					aria-label={`Context compression: ${meta.label}`}
				>
					<span className={cn("h-1.5 w-1.5 rounded-full", meta.color)} aria-hidden="true" />
					<span className="tabular-nums">{Math.round(pct * 100)}%</span>
				</button>
			</PopoverTrigger>
			<PopoverContent align="end" className="w-72 text-[11px] space-y-2 p-3">
				<div className="flex items-center justify-between border-b pb-1.5">
					<span className="font-semibold">Context window</span>
					<span className="tabular-nums text-muted-foreground">
						{totalTokens?.toLocaleString() ?? 0} / {window.toLocaleString()}
					</span>
				</div>
				<div className="space-y-1">
					<div className="flex items-center gap-1.5">
						<span className={cn("h-1.5 w-1.5 rounded-full", meta.color)} aria-hidden="true" />
						<span className="font-medium">{meta.label}</span>
						<span className="ml-auto tabular-nums font-mono">{(pct * 100).toFixed(1)}%</span>
					</div>
					<p className="text-muted-foreground leading-relaxed">{meta.title}</p>
					<p className="text-muted-foreground/80 leading-relaxed">{meta.detail}</p>
				</div>
				{meta.archivedBeforeAction && (
					<div className="rounded-md border border-red-500/30 bg-red-500/5 p-2 text-[10px] leading-relaxed">
						<div className="font-medium text-red-600 dark:text-red-400">Archive fired</div>
						<p className="text-muted-foreground/80 mt-0.5">
							Verbatim pre-compression messages persisted to MemPalace and Hindsight. The raw
							conversation is retrievable via the memory recall path even though the in-context view
							is summarized.
						</p>
					</div>
				)}
				<div className="border-t pt-1.5 space-y-0.5 text-muted-foreground">
					<div className="flex justify-between">
						<span>pre-save (archive window opens)</span>
						<span className="tabular-nums">{(thresholds.pre_save * 100).toFixed(0)}%</span>
					</div>
					<div className="flex justify-between">
						<span>compaction (mechanical prune)</span>
						<span className="tabular-nums">{(thresholds.compaction * 100).toFixed(0)}%</span>
					</div>
					<div className="flex justify-between">
						<span>emergency (LLM compression)</span>
						<span className="tabular-nums">{(thresholds.emergency * 100).toFixed(0)}%</span>
					</div>
				</div>
				<div className="border-t pt-1.5 text-[9px] text-muted-foreground/60 leading-relaxed">
					<strong>compaction ≠ compression.</strong> Compaction is mechanical and idempotent
					(tool-result truncation, no archive needed). Compression (only at emergency) summarises
					old turns via LLM and requires the MemPalace archive hook to fire first for reversibility.
				</div>
				{status.engine && (
					<div className="border-t pt-1.5 text-[9px] text-muted-foreground/70 font-mono">
						engine: {status.engine}
					</div>
				)}
			</PopoverContent>
		</Popover>
	);
}
