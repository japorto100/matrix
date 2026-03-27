"use client";

// AC85: Tool-Call 4-state UI (Phase 22d)
// Uses DynamicToolUIPart states from ai v6:
//   input-streaming | input-available | output-available | output-error | output-denied
//   approval-requested | approval-responded
// AC66: Approve/Deny buttons when state === "approval-requested"
// AC67: React.memo

import type { DynamicToolUIPart } from "ai";
import { Check, ChevronDown, ChevronRight, Loader2, ShieldAlert, Wrench, X } from "lucide-react";
import { memo, useState } from "react";

interface AgentChatToolBlockProps {
	toolName: string;
	toolCallId: string;
	state: DynamicToolUIPart["state"];
	input?: unknown;
	output?: unknown;
	isCollapsed: boolean;
	onToggle: (toolCallId: string) => void;
	/** AC66: approval callbacks */
	onApprove?: (toolCallId: string) => Promise<void>;
	onDeny?: (toolCallId: string) => Promise<void>;
}

const STATE_LABELS: Record<DynamicToolUIPart["state"], string> = {
	"input-streaming": "streaming",
	"input-available": "calling",
	"approval-requested": "approval?",
	"approval-responded": "approved",
	"output-available": "done",
	"output-error": "error",
	"output-denied": "denied",
};

const STATE_CLASSES: Record<DynamicToolUIPart["state"], string> = {
	"input-streaming": "bg-amber-500/20 text-amber-400",
	"input-available": "bg-blue-500/20 text-blue-400",
	"approval-requested": "bg-yellow-500/20 text-yellow-400",
	"approval-responded": "bg-sky-500/20 text-sky-400",
	"output-available": "bg-emerald-500/20 text-emerald-400",
	"output-error": "bg-red-500/20 text-red-400",
	"output-denied": "bg-orange-500/20 text-orange-400",
};

function AgentChatToolBlockInner({
	toolName,
	toolCallId,
	state,
	input,
	output,
	isCollapsed,
	onToggle,
	onApprove,
	onDeny,
}: AgentChatToolBlockProps) {
	const [approving, setApproving] = useState(false);

	async function handleApprove() {
		setApproving(true);
		await onApprove?.(toolCallId);
		setApproving(false);
	}

	async function handleDeny() {
		await onDeny?.(toolCallId);
	}

	return (
		<div className="mt-1 rounded border border-border/50 bg-muted/30 text-xs font-mono">
			<button
				type="button"
				className="flex w-full items-center gap-1.5 px-2 py-1 text-left text-muted-foreground hover:text-foreground transition-colors"
				onClick={() => onToggle(toolCallId)}
			>
				{isCollapsed ? (
					<ChevronRight className="h-3 w-3 shrink-0" />
				) : (
					<ChevronDown className="h-3 w-3 shrink-0" />
				)}
				{state === "input-available" ? (
					<Loader2 className="h-3 w-3 shrink-0 animate-spin" />
				) : (
					<Wrench className="h-3 w-3 shrink-0" />
				)}
				<span className="font-semibold truncate">{toolName}</span>
				<span
					className={`ml-auto shrink-0 rounded px-1 text-[9px] font-bold uppercase tracking-wider ${STATE_CLASSES[state]}`}
				>
					{STATE_LABELS[state]}
				</span>
			</button>

			{!isCollapsed && (
				<div className="border-t border-border/40 px-2 py-1.5 text-[10px] text-muted-foreground space-y-1.5">
					{/* AC66: approval card */}
					{state === "approval-requested" && (
						<div className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-2 space-y-2">
							<div className="flex items-center gap-1.5 text-yellow-400 font-semibold text-[10px]">
								<ShieldAlert className="h-3 w-3 shrink-0" />
								Agent requests permission to run this tool
							</div>
							{input !== undefined && (
								<pre className="whitespace-pre-wrap break-all text-muted-foreground/70 text-[9px]">
									{JSON.stringify(input, null, 2)}
								</pre>
							)}
							<div className="flex gap-1.5 pt-0.5">
								<button
									type="button"
									disabled={approving}
									onClick={() => void handleApprove()}
									className="flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
								>
									<Check className="h-2.5 w-2.5" />
									Approve
								</button>
								<button
									type="button"
									onClick={() => void handleDeny()}
									className="flex items-center gap-1 rounded bg-red-500/20 px-2 py-0.5 text-[10px] text-red-400 hover:bg-red-500/30 transition-colors"
								>
									<X className="h-2.5 w-2.5" />
									Deny
								</button>
							</div>
						</div>
					)}
					{state !== "approval-requested" && input !== undefined && (
						<div>
							<div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-0.5">
								Input
							</div>
							<pre className="whitespace-pre-wrap break-all">{JSON.stringify(input, null, 2)}</pre>
						</div>
					)}
					{(state === "output-available" || state === "output-error") && output !== undefined && (
						<div>
							<div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-0.5">
								{state === "output-error" ? "Error" : "Output"}
							</div>
							<pre className="whitespace-pre-wrap break-all">{JSON.stringify(output, null, 2)}</pre>
						</div>
					)}
				</div>
			)}
		</div>
	);
}

export const AgentChatToolBlock = memo(AgentChatToolBlockInner, (prev, next) => {
	if (prev.toolCallId !== next.toolCallId) return false;
	if (prev.state !== next.state) return false;
	if (prev.isCollapsed !== next.isCollapsed) return false;
	return true;
});
