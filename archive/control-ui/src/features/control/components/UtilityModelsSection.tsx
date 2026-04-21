"use client";

// Utility Models Section — Embedder, Reranker, STT, TTS, Summarizer
// Configurable model selection per utility purpose.

import { Box, Sparkles, TestTube, Workflow } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { UtilityModel, UtilityPurpose } from "../types";

const PURPOSE_ICON: Record<UtilityPurpose, React.ReactNode> = {
	embedder_text: <Box className="h-3.5 w-3.5" />,
	embedder_visual: <Sparkles className="h-3.5 w-3.5" />,
	reranker: <Workflow className="h-3.5 w-3.5" />,
	summarizer: <Workflow className="h-3.5 w-3.5" />,
	stt: <TestTube className="h-3.5 w-3.5" />,
	tts: <TestTube className="h-3.5 w-3.5" />,
};

const PURPOSE_LABEL: Record<UtilityPurpose, string> = {
	embedder_text: "Text Embedding",
	embedder_visual: "Visual Embedding",
	reranker: "Reranker",
	summarizer: "Summarizer",
	stt: "Speech-to-Text",
	tts: "Text-to-Speech",
};

const PURPOSE_DESCRIPTION: Record<UtilityPurpose, string> = {
	embedder_text: "Converts text to vector representations for semantic search",
	embedder_visual: "Document/image understanding via ColPali or similar",
	reranker: "Re-scores search results for relevance",
	summarizer: "Context summarization for memory management",
	stt: "Audio transcription (Whisper, local or cloud)",
	tts: "Voice synthesis (OpenAI TTS, Kokoro, Piper)",
};

export function UtilityModelsSection({ utilities }: { utilities: UtilityModel[] }) {
	return (
		<div className="space-y-4">
			<header>
				<h2 className="text-base font-semibold">Utility & Inference Models</h2>
				<p className="text-xs text-muted-foreground">
					Embedder, reranker, summarizer, STT, TTS — internal models not directly user-facing
				</p>
			</header>

			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				{utilities.map((u) => (
					<UtilityCard key={u.purpose} utility={u} />
				))}
			</div>
		</div>
	);
}

function UtilityCard({ utility }: { utility: UtilityModel }) {
	const [_editing, _setEditing] = useState(false);
	const [_modelId, _setModelId] = useState(utility.model_id);

	return (
		<Card className={cn(!utility.is_active && "opacity-60")}>
			<CardHeader className="pb-2">
				<div className="flex items-start justify-between gap-2">
					<div className="flex items-center gap-1.5">
						{PURPOSE_ICON[utility.purpose]}
						<CardTitle className="text-xs font-semibold leading-tight">
							{PURPOSE_LABEL[utility.purpose] ?? utility.display_name}
						</CardTitle>
					</div>
					<div className="flex gap-1">
						{utility.is_local ? (
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
						{utility.is_active ? (
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
				</div>
			</CardHeader>
			<CardContent className="space-y-2 pt-0">
				<p className="text-[10px] text-muted-foreground leading-relaxed">
					{PURPOSE_DESCRIPTION[utility.purpose]}
				</p>
				<code className="text-[10px] text-muted-foreground font-mono line-clamp-1 block">
					{utility.model_id || "not configured"}
				</code>
				{utility.notes && (
					<div className="text-[10px] text-muted-foreground/70 leading-relaxed">
						{utility.notes}
					</div>
				)}
			</CardContent>
		</Card>
	);
}
