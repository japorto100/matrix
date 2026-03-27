"use client";

// AC71: Agent toolbar — model selector (static list) + context reset + thread options
// AC107: Controlled model selector — selectedModel + onModelChange from parent.
// AC108: Reasoning-Effort toggle — low/medium/high passed through BFF → Go → Python.
// Static model list (no backend required); dynamic model-list needs /api/agent/models endpoint.

import {
	BrainCircuit,
	ChevronDown,
	Columns2,
	PanelRight,
	PlusCircle,
	RotateCcw,
	Square,
	Volume2,
	VolumeX,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useGlobalChat } from "@/features/agent-chat/context/GlobalChatContext";

export const AGENT_MODELS = [
	{ id: "claude-sonnet-4-6", label: "Sonnet 4.6" },
	{ id: "claude-opus-4-6", label: "Opus 4.6" },
	{ id: "claude-haiku-4-5", label: "Haiku 4.5" },
] as const;

export type AgentModelId = (typeof AGENT_MODELS)[number]["id"];

export type ReasoningEffort = "low" | "medium" | "high";

const EFFORT_LABELS: Record<ReasoningEffort, string> = {
	low: "L",
	medium: "M",
	high: "H",
};
const EFFORT_COLORS: Record<ReasoningEffort, string> = {
	low: "text-muted-foreground/60",
	medium: "text-amber-500",
	high: "text-primary",
};

interface AgentChatToolbarProps {
	onNewThread?: () => void;
	onContextReset?: () => void;
	/** AC107: controlled model selector — pass from useChatSession */
	selectedModel?: string;
	onModelChange?: (model: string) => void;
	/** AC108: reasoning effort toggle */
	reasoningEffort?: ReasoningEffort;
	onReasoningEffortChange?: (effort: ReasoningEffort) => void;
	/** AC50: TTS autoplay toggle */
	autoplayTts?: boolean;
	onAutoplayToggle?: () => void;
}

export function AgentChatToolbar({
	onNewThread,
	onContextReset,
	selectedModel = "claude-sonnet-4-6",
	onModelChange,
	reasoningEffort = "medium",
	onReasoningEffortChange,
	autoplayTts = false,
	onAutoplayToggle,
}: AgentChatToolbarProps) {
	const [pickerOpen, setPickerOpen] = useState(false);
	const { mode, toggleMode } = useGlobalChat();
	const activeReasoningEffort: ReasoningEffort = reasoningEffort ?? "medium";

	const currentLabel = AGENT_MODELS.find((m) => m.id === selectedModel)?.label ?? selectedModel;

	function cycleEffort() {
		const order: ReasoningEffort[] = ["low", "medium", "high"];
		const next =
			order[(order.indexOf(activeReasoningEffort) + 1) % order.length] ?? activeReasoningEffort;
		onReasoningEffortChange?.(next);
	}

	return (
		<div className="relative flex items-center gap-1 px-2 py-1 border-b border-border/40 bg-background shrink-0">
			{/* Model selector */}
			<div className="relative">
				<button
					type="button"
					onClick={() => setPickerOpen((v) => !v)}
					className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
				>
					<span className="font-mono">{currentLabel}</span>
					<ChevronDown className="h-2.5 w-2.5" />
				</button>
				{pickerOpen && (
					<div className="absolute top-full left-0 z-50 mt-1 min-w-[140px] rounded-md border border-border bg-popover shadow-md">
						{AGENT_MODELS.map((m) => (
							<button
								key={m.id}
								type="button"
								onClick={() => {
									onModelChange?.(m.id);
									setPickerOpen(false);
								}}
								className={`flex w-full items-center px-3 py-1.5 text-[11px] hover:bg-muted/60 transition-colors ${
									m.id === selectedModel ? "text-foreground font-medium" : "text-muted-foreground"
								}`}
							>
								{m.label}
							</button>
						))}
					</div>
				)}
			</div>

			{/* AC108: Reasoning-effort cycle button */}
			<button
				type="button"
				onClick={cycleEffort}
				className={`flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] hover:bg-muted/60 transition-colors ${EFFORT_COLORS[activeReasoningEffort]}`}
				title={`Reasoning effort: ${activeReasoningEffort} (click to cycle)`}
			>
				<BrainCircuit className="h-2.5 w-2.5" />
				<span className="font-mono">{EFFORT_LABELS[activeReasoningEffort]}</span>
			</button>

			<div className="ml-auto flex items-center gap-0.5">
				{/* AC50: TTS autoplay toggle */}
				{onAutoplayToggle && (
					<button
						type="button"
						onClick={onAutoplayToggle}
						className={`flex items-center rounded px-1.5 py-0.5 text-[10px] hover:bg-muted/60 transition-colors ${autoplayTts ? "text-primary" : "text-muted-foreground/50"}`}
						title={autoplayTts ? "Autoplay TTS: on (click to disable)" : "Autoplay TTS: off"}
					>
						{autoplayTts ? (
							<Volume2 className="h-2.5 w-2.5" />
						) : (
							<VolumeX className="h-2.5 w-2.5" />
						)}
					</button>
				)}
				{/* AC89/AC93: Mode cycle: sheet → split → rail → sheet */}
				<Button
					variant="ghost"
					size="icon"
					className="h-6 w-6 text-muted-foreground/60 hover:text-muted-foreground"
					onClick={toggleMode}
					title={
						mode === "sheet"
							? "Switch to split view (420px)"
							: mode === "split"
								? "Switch to rail (240px)"
								: "Switch to overlay"
					}
				>
					{mode === "sheet" ? (
						<Columns2 className="h-3 w-3" />
					) : mode === "split" ? (
						<PanelRight className="h-3 w-3" />
					) : (
						<Square className="h-3 w-3" />
					)}
				</Button>
				{onContextReset && (
					<Button
						variant="ghost"
						size="icon"
						className="h-6 w-6 text-muted-foreground/60 hover:text-muted-foreground"
						onClick={onContextReset}
						title="Reset context"
					>
						<RotateCcw className="h-3 w-3" />
					</Button>
				)}
				{onNewThread && (
					<Button
						variant="ghost"
						size="icon"
						className="h-6 w-6 text-muted-foreground/60 hover:text-muted-foreground"
						onClick={onNewThread}
						title="New thread"
					>
						<PlusCircle className="h-3 w-3" />
					</Button>
				)}
			</div>
		</div>
	);
}
