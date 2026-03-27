"use client";

// AC61: Empty-Chat-Screen with suggestion chips
// AC62: Loading skeleton while connecting
// AC103: Passes usageMap to AgentChatMessage for token badge
// AC54: Passes sentAttachments to user AgentChatMessage for image display
// AC66: onApproveToolCall/onDenyToolCall pass-through to AgentChatMessage
// Phase 22d: Uses UIMessage[] from ai SDK

import type { TextUIPart, UIMessage } from "ai";
import { Bot, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { StagedAttachment } from "../hooks/useAttachments";
import type { MessageUsage } from "../hooks/useChatSession";
import { AgentChatMessage } from "./AgentChatMessage";

const SUGGESTION_CHIPS = [
	"Analyse current BTC/USD trend",
	"Geopolitical risks affecting markets today",
	"Explain the Kelly Criterion for position sizing",
	"What are the key support levels for this asset?",
];

interface AgentChatThreadProps {
	messages: UIMessage[];
	isConnecting: boolean;
	isStreaming: boolean;
	collapsedTools: Set<string>;
	onToggleBlock: (toolCallId: string) => void;
	onSuggestion?: (text: string) => void;
	/** AC103: per-message usage for token badge */
	usageMap?: Map<string, MessageUsage>;
	/** AC54: staged attachments per user-message order */
	sentAttachments?: StagedAttachment[][];
	/** AC50: TTS autoplay for sealed assistant messages */
	autoplayTts?: boolean;
	/** AC105: edit a user message and resend */
	onEditMessage?: (messageId: string, newText: string) => void;
	/** AC42: regenerate the last assistant response */
	onRegenerate?: () => void;
	/** AC66: approve a pending tool call */
	onApproveToolCall?: (toolCallId: string) => Promise<void>;
	/** AC66: deny a pending tool call */
	onDenyToolCall?: (toolCallId: string) => Promise<void>;
}

function EmptyChat({ onSuggestion }: { onSuggestion?: (text: string) => void }) {
	return (
		<div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
			<div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
				<Bot className="h-5 w-5 text-muted-foreground" />
			</div>
			<div className="space-y-1">
				<p className="text-sm font-medium text-foreground">Agent ready</p>
				<p className="text-xs text-muted-foreground">
					Streaming via Go Gateway → Python / Anthropic
				</p>
			</div>
			{onSuggestion && (
				<div className="flex flex-wrap justify-center gap-2 max-w-xs">
					{SUGGESTION_CHIPS.map((chip) => (
						<button
							key={chip}
							type="button"
							onClick={() => onSuggestion(chip)}
							className="rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors text-left"
						>
							{chip}
						</button>
					))}
				</div>
			)}
		</div>
	);
}

function MessageSkeleton() {
	return (
		<div className="flex justify-start">
			<div className="max-w-[75%] rounded-lg bg-muted px-3 py-2 space-y-2">
				<div className="h-2.5 w-48 rounded bg-muted-foreground/20 animate-pulse" />
				<div className="h-2.5 w-32 rounded bg-muted-foreground/15 animate-pulse" />
			</div>
		</div>
	);
}

const EMOJI_STRIP_RE =
	/[\u{1F300}-\u{1FAFF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{FE00}-\u{FE0F}]/gu;

export function AgentChatThread({
	messages,
	isConnecting,
	isStreaming,
	collapsedTools,
	onToggleBlock,
	onSuggestion,
	usageMap,
	sentAttachments,
	autoplayTts,
	onEditMessage,
	onRegenerate,
	onApproveToolCall,
	onDenyToolCall,
}: AgentChatThreadProps) {
	const bottomRef = useRef<HTMLDivElement>(null);
	const containerRef = useRef<HTMLDivElement>(null);
	const isAtBottomRef = useRef(true);
	const [speakingId, setSpeakingId] = useState<string | null>(null);

	// AC50: autoplay TTS for sealed assistant messages
	const autoplayAbortRef = useRef<AbortController | null>(null);
	const autoplaySrcRef = useRef<AudioBufferSourceNode | null>(null);
	const lastAutoPlayedIdRef = useRef<string | null>(null);

	// Cleanup autoplay resources on unmount
	useEffect(
		() => () => {
			autoplayAbortRef.current?.abort();
			try {
				autoplaySrcRef.current?.stop();
			} catch {}
		},
		[],
	);

	useEffect(() => {
		if (!autoplayTts || isStreaming) return;
		const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
		if (!lastAssistant || lastAssistant.id === lastAutoPlayedIdRef.current) return;
		const isMsgStreaming = lastAssistant.parts.some(
			(p) => p.type === "text" && (p as TextUIPart & { state?: string }).state === "streaming",
		);
		if (isMsgStreaming) return;
		const text = lastAssistant.parts
			.filter((p): p is TextUIPart => p.type === "text")
			.map((p) => p.text)
			.join("")
			.replace(EMOJI_STRIP_RE, "")
			.trim();
		if (!text) return;

		lastAutoPlayedIdRef.current = lastAssistant.id;
		autoplayAbortRef.current?.abort();
		const ac = new AbortController();
		autoplayAbortRef.current = ac;

		void (async () => {
			try {
				const res = await fetch("/api/audio/synthesize", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ text: text.slice(0, 4096) }),
					signal: ac.signal,
				});
				if (!res.ok || ac.signal.aborted) return;
				const buf = await res.arrayBuffer();
				if (ac.signal.aborted) return;
				const ctx = new AudioContext();
				const audioBuffer = await ctx.decodeAudioData(buf);
				if (ac.signal.aborted) return;
				const source = ctx.createBufferSource();
				source.buffer = audioBuffer;
				source.connect(ctx.destination);
				autoplaySrcRef.current = source;
				source.start(0);
			} catch {
				// silent fail — autoplay is best-effort
			}
		})();
	}, [messages, isStreaming, autoplayTts]);

	const handleScroll = useCallback(() => {
		const el = containerRef.current;
		if (!el) return;
		isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
	}, []);

	useEffect(() => {
		if (isAtBottomRef.current) {
			bottomRef.current?.scrollIntoView({ behavior: "smooth" });
		}
	});

	if (messages.length === 0 && !isConnecting) {
		return <EmptyChat onSuggestion={onSuggestion} />;
	}

	// AC54: map user messages to their sentAttachments by order index
	let userMsgIdx = 0;

	return (
		<div
			ref={containerRef}
			className="flex-1 overflow-y-auto px-3 py-3 space-y-3"
			onScroll={handleScroll}
		>
			{messages.map((msg, i) => {
				const attIdx = msg.role === "user" ? userMsgIdx++ : -1;
				const staged = msg.role === "user" ? sentAttachments?.[attIdx] : undefined;
				const isLast = i === messages.length - 1;
				return (
					<AgentChatMessage
						key={msg.id}
						message={msg}
						index={i}
						collapsedTools={collapsedTools}
						onToggleBlock={onToggleBlock}
						speakingId={speakingId}
						onSpeakStart={setSpeakingId}
						usage={usageMap?.get(msg.id)}
						stagedAttachments={staged}
						onEdit={onEditMessage}
						isLast={isLast}
						onRegenerate={msg.role === "assistant" && isLast ? onRegenerate : undefined}
						onApproveToolCall={onApproveToolCall}
						onDenyToolCall={onDenyToolCall}
					/>
				);
			})}

			{isConnecting && !isStreaming && (
				<div className="flex justify-start">
					<div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
						<Loader2 className="h-3 w-3 animate-spin" />
						Connecting…
					</div>
				</div>
			)}

			{/* AC62: skeleton while first response loads */}
			{isConnecting && messages.length === 0 && <MessageSkeleton />}

			<div ref={bottomRef} />
		</div>
	);
}
