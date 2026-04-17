"use client";

// AC71: Agent toolbar — model selector + context reset + thread options
// AC107: Controlled model selector — selectedModel + onModelChange from parent.
// AC108: Reasoning-Effort toggle — low/medium/high passed through BFF → Go → Python.
// exec-16: Dynamic model list from /api/agent/models (grouped cloud/local).

import {
	BrainCircuit,
	ChevronDown,
	Columns2,
	Mic,
	MicOff,
	PanelRight,
	PlusCircle,
	RotateCcw,
	Square,
	Volume2,
	VolumeX,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useAvailableModels } from "../hooks/useAvailableModels";
import { useGlobalChat } from "../stores/globalChatStore";

/** Reasoning effort — string passthrough, LiteLLM validates per provider. */
export type ReasoningEffort = string;

/** Default cycle order. Provider may support more (e.g. "none", "xhigh", "max"). */
const DEFAULT_EFFORT_ORDER = ["low", "medium", "high"];

const EFFORT_LABELS: Record<string, string> = {
	none: "—",
	minimal: "Min",
	low: "L",
	medium: "M",
	high: "H",
	xhigh: "XH",
	max: "Max",
};

const EFFORT_COLORS: Record<string, string> = {
	none: "text-muted-foreground/30",
	minimal: "text-muted-foreground/40",
	low: "text-muted-foreground/60",
	medium: "text-amber-500",
	high: "text-primary",
	xhigh: "text-primary",
	max: "text-red-400",
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
	/** Available reasoning levels for the current model (from ModelInfo) */
	reasoningLevels?: string[];
	/** AC50: TTS autoplay toggle */
	autoplayTts?: boolean;
	onAutoplayToggle?: () => void;
	/** Voice mode: Text ↔ Voice (LiveKit WebRTC) */
	voiceActive?: boolean;
	onVoiceToggle?: () => void;
}

export function AgentChatToolbar({
	onNewThread,
	onContextReset,
	selectedModel = "",
	onModelChange,
	reasoningEffort = "medium",
	onReasoningEffortChange,
	reasoningLevels,
	autoplayTts = false,
	onAutoplayToggle,
	voiceActive = false,
	onVoiceToggle,
}: AgentChatToolbarProps) {
	const [pickerOpen, setPickerOpen] = useState(false);
	const { mode, toggleMode } = useGlobalChat();
	const { cloudModels, localModels } = useAvailableModels();
	const activeReasoningEffort: ReasoningEffort = reasoningEffort ?? "medium";
	const effortOrder = reasoningLevels?.length ? reasoningLevels : DEFAULT_EFFORT_ORDER;

	// Short label: strip provider prefix, show last part
	const shortLabel = (id: string) => {
		const parts = id.split("/");
		return parts[parts.length - 1] ?? id;
	};
	const currentLabel = shortLabel(selectedModel);

	function cycleEffort() {
		const idx = effortOrder.indexOf(activeReasoningEffort);
		const next = effortOrder[(idx + 1) % effortOrder.length] ?? activeReasoningEffort;
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
					<div className="absolute top-full left-0 z-50 mt-1 min-w-[180px] max-h-[320px] overflow-y-auto rounded-md border border-border bg-popover shadow-md">
						{cloudModels.length > 0 && (
							<>
								<div className="px-3 py-1 text-[9px] font-semibold text-muted-foreground/60 uppercase tracking-wider">
									Cloud
								</div>
								{cloudModels.map((m) => (
									<button
										key={m.id}
										type="button"
										onClick={() => {
											onModelChange?.(m.id);
											setPickerOpen(false);
										}}
										className={`flex w-full items-center px-3 py-1.5 text-[11px] hover:bg-muted/60 transition-colors ${
											m.id === selectedModel
												? "text-foreground font-medium"
												: "text-muted-foreground"
										}`}
									>
										{shortLabel(m.id)}
									</button>
								))}
							</>
						)}
						{localModels.length > 0 && (
							<>
								<div className="px-3 py-1 text-[9px] font-semibold text-muted-foreground/60 uppercase tracking-wider border-t border-border mt-1 pt-1">
									Local
								</div>
								{localModels.map((m) => (
									<button
										key={m.id}
										type="button"
										onClick={() => {
											onModelChange?.(m.id);
											setPickerOpen(false);
										}}
										className={`flex w-full items-center px-3 py-1.5 text-[11px] hover:bg-muted/60 transition-colors ${
											m.id === selectedModel
												? "text-foreground font-medium"
												: "text-muted-foreground"
										}`}
									>
										{shortLabel(m.id)}
									</button>
								))}
							</>
						)}
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
				{/* Voice mode toggle: Text ↔ Voice (LiveKit WebRTC) */}
				{onVoiceToggle && (
					<button
						type="button"
						onClick={onVoiceToggle}
						className={`flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] hover:bg-muted/60 transition-colors ${voiceActive ? "text-green-500" : "text-muted-foreground/50"}`}
						title={
							voiceActive ? "Voice aktiv — klicken zum Beenden" : "Voice Chat starten (WebRTC)"
						}
					>
						{voiceActive ? <Mic className="h-2.5 w-2.5" /> : <MicOff className="h-2.5 w-2.5" />}
						<span className="font-mono">{voiceActive ? "Voice" : "Text"}</span>
					</button>
				)}
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
