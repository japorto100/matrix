"use client";

// AC34-AC38: Markdown rendering + reasoning collapsible (AC84)
// AC41: Copy-button per assistant message
// AC42: Regenerate-button on last assistant message
// AC44: Feedback buttons (thumbs up/down) on assistant messages
// AC46: Paced turn groups via framer-motion fade-in
// AC49: TTS-button per assistant message
// AC54: Image thumbnails for user messages with attachments
// AC66: onApprove/onDeny wired to AgentChatToolBlock
// AC67: React.memo with custom arePropsEqual
// AC82: Uses UIMessage + message.parts (Phase 22d, ai v6)
// AC103: Token usage badge in message footer
// AC104: Cost-per-token estimate badge

import type { TextUIPart, UIMessage } from "ai";
import { motion } from "framer-motion";
import {
	BrainCircuit,
	Check,
	ChevronDown,
	ChevronRight,
	Copy,
	Pencil,
	RotateCcw,
	ThumbsDown,
	ThumbsUp,
} from "lucide-react";
import { memo, useCallback, useState } from "react";
import type { StagedAttachment } from "../hooks/useAttachments";
import type { MessageUsage } from "../hooks/useChatSession";
import { AgentChatMarkdown } from "./AgentChatMarkdown";
import { AgentChatSources, extractSources } from "./AgentChatSources";
import { AgentChatToolBlock } from "./AgentChatToolBlock";
import { AgentChatTtsButton } from "./AgentChatTtsButton";
import { ImagePreviewModal } from "./ImagePreviewModal";

interface AgentChatMessageProps {
	message: UIMessage;
	onToggleBlock: (toolCallId: string) => void;
	collapsedTools: Set<string>;
	speakingId?: string | null;
	onSpeakStart?: (id: string) => void;
	/** Index within the thread — used for staggered entry delay (AC46) */
	index?: number;
	/** AC103/AC104: token usage for this message (only available after stream completes) */
	usage?: MessageUsage;
	/** AC54: staged image attachments for user messages */
	stagedAttachments?: StagedAttachment[];
	/** AC105: edit user message and resend from that point */
	onEdit?: (messageId: string, newText: string) => void;
	/** AC42: regenerate last assistant response */
	onRegenerate?: () => void;
	/** AC42: true if this is the last message in the thread */
	isLast?: boolean;
	/** AC66: approve a pending tool call */
	onApproveToolCall?: (toolCallId: string) => Promise<void>;
	/** AC66: deny a pending tool call */
	onDenyToolCall?: (toolCallId: string) => Promise<void>;
}

function CopyButton({ text }: { text: string }) {
	const [copied, setCopied] = useState(false);
	const handleCopy = useCallback(() => {
		void navigator.clipboard.writeText(text).then(() => {
			setCopied(true);
			setTimeout(() => setCopied(false), 1500);
		});
	}, [text]);
	return (
		<button
			type="button"
			onClick={handleCopy}
			className="flex items-center gap-1 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
			title="Copy message"
		>
			{copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
		</button>
	);
}

function ReasoningBlock({ text }: { text: string }) {
	const [open, setOpen] = useState(false);
	return (
		<div className="mt-1 rounded border border-border/50 bg-muted/20 text-xs">
			<button
				type="button"
				className="flex w-full items-center gap-1.5 px-2 py-1 text-left text-muted-foreground hover:text-foreground transition-colors"
				onClick={() => setOpen((v) => !v)}
			>
				{open ? (
					<ChevronDown className="h-3 w-3 shrink-0" />
				) : (
					<ChevronRight className="h-3 w-3 shrink-0" />
				)}
				<BrainCircuit className="h-3 w-3 shrink-0" />
				<span className="font-semibold">Thinking</span>
			</button>
			{open && (
				<div className="border-t border-border/40 px-2 py-1.5 text-[11px] text-muted-foreground/80 italic whitespace-pre-wrap">
					{text}
				</div>
			)}
		</div>
	);
}

// AC104: format cost as $X.XXXXXX
function formatCost(usd: number): string {
	if (usd < 0.000001) return "<$0.000001";
	return `$${usd.toFixed(6)}`;
}

function AgentChatMessageInner({
	message,
	onToggleBlock,
	collapsedTools,
	speakingId,
	onSpeakStart,
	index = 0,
	usage,
	stagedAttachments,
	onEdit,
	onRegenerate,
	isLast = false,
	onApproveToolCall,
	onDenyToolCall,
}: AgentChatMessageProps) {
	const isUser = message.role === "user";
	const [previewAtt, setPreviewAtt] = useState<StagedAttachment | null>(null);
	// AC105: inline edit state
	const [isEditing, setIsEditing] = useState(false);
	const [editText, setEditText] = useState("");
	// AC44: feedback state
	const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

	// Collect full text from all text parts (for copy/TTS)
	const fullText = message.parts
		.filter((p): p is TextUIPart => p.type === "text")
		.map((p) => p.text)
		.join("");

	// In-progress streaming detection: text part has state 'streaming'
	const isStreaming = message.parts.some(
		(p) => p.type === "text" && (p as TextUIPart & { state?: string }).state === "streaming",
	);

	// AC46: stagger delay capped at 150ms
	const delay = Math.min(index * 0.04, 0.15);

	return (
		<>
			<motion.div
				initial={{ opacity: 0, y: 6 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.18, ease: "easeOut", delay }}
				className={`flex ${isUser ? "justify-end" : "justify-start"}`}
			>
				<div
					className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
						isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
					}`}
				>
					{/* AC54: image thumbnails for user messages */}
					{isUser && stagedAttachments && stagedAttachments.length > 0 && (
						<div className="flex flex-wrap gap-1.5 mb-2">
							{stagedAttachments.map((att) => (
								<button
									key={att.id}
									type="button"
									onClick={() => setPreviewAtt(att)}
									className="h-16 w-16 rounded border border-primary-foreground/20 overflow-hidden hover:opacity-80 transition-opacity"
									title={att.name}
								>
									{/* biome-ignore lint/performance/noImgElement: previewUrl is a blob: URL from URL.createObjectURL — Next.js <Image> cannot optimize blob: URLs */}
									<img src={att.previewUrl} alt={att.name} className="h-full w-full object-cover" />
								</button>
							))}
						</div>
					)}

					{message.parts.map((part, i) => {
						const key = `${message.id}-part-${i}`;

						if (part.type === "text") {
							return (
								<div key={key}>
									{isUser ? (
										<div className="whitespace-pre-wrap break-words leading-relaxed">
											{part.text}
										</div>
									) : (
										<>
											{part.text ? <AgentChatMarkdown content={part.text} /> : null}
											{!part.text && isStreaming && (
												<span className="inline-flex gap-0.5 ml-0.5 align-middle">
													<span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:0ms]" />
													<span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:150ms]" />
													<span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:300ms]" />
												</span>
											)}
										</>
									)}
								</div>
							);
						}

						// AC84: Extended thinking via reasoning parts
						if (part.type === "reasoning") {
							return <ReasoningBlock key={key} text={part.text} />;
						}

						// AC85: Dynamic tool calls
						if (part.type === "dynamic-tool") {
							const outputValue =
								part.state === "output-available"
									? part.output
									: part.state === "output-error"
										? part.errorText
										: undefined;
							return (
								<AgentChatToolBlock
									key={key}
									toolName={part.toolName}
									toolCallId={part.toolCallId}
									state={part.state}
									input={part.input}
									output={outputValue}
									isCollapsed={collapsedTools.has(part.toolCallId)}
									onToggle={onToggleBlock}
									onApprove={onApproveToolCall}
									onDeny={onDenyToolCall}
								/>
							);
						}

						return null;
					})}

					{/* AC57/58: Sources panel for assistant messages */}
					{!isUser && <AgentChatSources sources={extractSources(message)} />}

					{/* AC105: inline edit form */}
					{isUser && isEditing && (
						<div className="mt-2 space-y-1.5">
							<textarea
								value={editText}
								onChange={(e) => setEditText(e.target.value)}
								rows={3}
								className="w-full resize-none rounded border border-primary-foreground/25 bg-primary-foreground/10 px-2 py-1 text-xs text-primary-foreground focus:outline-none"
							/>
							<div className="flex gap-1 justify-end">
								<button
									type="button"
									onClick={() => setIsEditing(false)}
									className="rounded px-2 py-0.5 text-[10px] text-primary-foreground/60 hover:text-primary-foreground transition-colors"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={() => {
										if (editText.trim()) {
											onEdit?.(message.id, editText.trim());
											setIsEditing(false);
										}
									}}
									className="rounded bg-primary-foreground/20 px-2 py-0.5 text-[10px] text-primary-foreground hover:bg-primary-foreground/30 transition-colors"
								>
									Resend
								</button>
							</div>
						</div>
					)}

					<div
						className={`mt-1.5 flex items-center justify-between gap-2 ${
							isUser ? "text-primary-foreground/60" : "text-muted-foreground/60"
						}`}
					>
						<span className="text-[10px]">{new Date().toLocaleTimeString()}</span>
						{/* AC105: edit button for user messages */}
						{isUser && onEdit && !isEditing && (
							<button
								type="button"
								onClick={() => {
									setEditText(fullText);
									setIsEditing(true);
								}}
								className="flex items-center gap-1 text-[10px] text-primary-foreground/40 hover:text-primary-foreground/70 transition-colors"
								title="Edit and resend"
							>
								<Pencil className="h-3 w-3" />
							</button>
						)}
						{!isUser && !isStreaming && fullText && (
							<div className="flex items-center gap-1.5">
								{/* AC103/AC104: token usage + cost badge */}
								{usage && (
									<span
										className="text-[9px] font-mono text-muted-foreground/40 tabular-nums"
										title={`finish: ${usage.finishReason}${usage.costUsd !== undefined ? ` · cost: ${formatCost(usage.costUsd)}` : ""}`}
									>
										{usage.promptTokens}↑ {usage.completionTokens}↓
										{usage.costUsd !== undefined && (
											<span className="ml-1 text-muted-foreground/30">
												{formatCost(usage.costUsd)}
											</span>
										)}
									</span>
								)}
								<AgentChatTtsButton
									text={fullText}
									shouldStop={speakingId !== null && speakingId !== message.id}
									onSpeakStart={() => onSpeakStart?.(message.id)}
								/>
								<CopyButton text={fullText} />
								{/* AC44: feedback buttons */}
								<button
									type="button"
									onClick={() => setFeedback(feedback === "up" ? null : "up")}
									className={`transition-colors ${feedback === "up" ? "text-emerald-500" : "text-muted-foreground/40 hover:text-muted-foreground/70"}`}
									title="Good response"
								>
									<ThumbsUp className="h-3 w-3" />
								</button>
								<button
									type="button"
									onClick={() => setFeedback(feedback === "down" ? null : "down")}
									className={`transition-colors ${feedback === "down" ? "text-red-400" : "text-muted-foreground/40 hover:text-muted-foreground/70"}`}
									title="Bad response"
								>
									<ThumbsDown className="h-3 w-3" />
								</button>
								{/* AC42: regenerate on last assistant message */}
								{isLast && onRegenerate && (
									<button
										type="button"
										onClick={onRegenerate}
										className="text-muted-foreground/40 hover:text-muted-foreground/70 transition-colors"
										title="Regenerate response"
									>
										<RotateCcw className="h-3 w-3" />
									</button>
								)}
							</div>
						)}
					</div>
				</div>
			</motion.div>

			{/* AC55: fullscreen preview for attached images */}
			<ImagePreviewModal attachment={previewAtt} onClose={() => setPreviewAtt(null)} />
		</>
	);
}

// AC67: memo — only re-render if parts count, text content, tool collapse, usage, or attachments change
export const AgentChatMessage = memo(AgentChatMessageInner, (prev, next) => {
	if (prev.message.id !== next.message.id) return false;
	if (prev.message.parts.length !== next.message.parts.length) return false;
	const prevText = prev.message.parts
		.filter((p) => p.type === "text")
		.map((p) => p.text)
		.join("");
	const nextText = next.message.parts
		.filter((p) => p.type === "text")
		.map((p) => p.text)
		.join("");
	if (prevText !== nextText) return false;
	if (prev.collapsedTools !== next.collapsedTools) return false;
	const prevRelevant = prev.speakingId === prev.message.id || prev.speakingId === null;
	const nextRelevant = next.speakingId === next.message.id || next.speakingId === null;
	if (prevRelevant !== nextRelevant) return false;
	if (prev.usage !== next.usage) return false;
	if (prev.stagedAttachments !== next.stagedAttachments) return false;
	if (prev.isLast !== next.isLast) return false;
	return true;
});
