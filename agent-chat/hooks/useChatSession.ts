"use client";

// Agent Chat Session Hook — Phase 22d / 22f
// Uses @ai-sdk/react v3 useChat with DefaultChatTransport.
// prepareSendMessagesRequest maps SDK message array → our BFF { message, threadId, model, attachments, reasoningEffort } contract.
// Exposes stable interface consumed by AgentChatPanel + sub-components.
// AC107: model override per request (Toolbar → BFF → Go → Python).
// AC103/AC106: per-message usage + finishReason tracking via onFinish.
//   Usage tokens come from message.metadata (forwarded by Go Gateway as messageMetadata).
// AC56: multimodal attachments forwarded in request body.
// AC101: nuqs useQueryState for chat ID URL persistence.
// AC104: cost-per-token estimate per message.
// AC108: reasoningEffort state forwarded in request body.
// AC64: contextPressure derived from latest promptTokens / model max context.

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useQueryState } from "nuqs";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ReasoningEffort } from "../components/AgentChatToolbar";
import type { RequestAttachment, StagedAttachment } from "./useAttachments";

let idCounter = 0;
function localId(prefix = "chat"): string {
	return `${prefix}-${Date.now()}-${(idCounter++).toString(36)}`;
}

export interface MessageUsage {
	promptTokens: number;
	completionTokens: number;
	finishReason: string;
	/** AC104: estimated cost in USD */
	costUsd?: number;
}

// AC104: cost table (USD per token, approximate)
const COST_PER_TOKEN: Record<string, { input: number; output: number }> = {
	"claude-sonnet-4-6": { input: 3 / 1_000_000, output: 15 / 1_000_000 },
	"claude-opus-4-6": { input: 15 / 1_000_000, output: 75 / 1_000_000 },
	"claude-haiku-4-5": { input: 0.8 / 1_000_000, output: 4 / 1_000_000 },
};

// AC64: model max context window (tokens)
const MODEL_MAX_CONTEXT: Record<string, number> = {
	"claude-sonnet-4-6": 200_000,
	"claude-opus-4-6": 200_000,
	"claude-haiku-4-5": 200_000,
};
const DEFAULT_MAX_CONTEXT = 200_000;

export interface UseChatSessionReturn {
	messages: UIMessage[];
	isStreaming: boolean;
	isConnecting: boolean;
	error: string | null;
	threadId: string | undefined;
	send: (
		text: string,
		attachments?: RequestAttachment[],
		staged?: StagedAttachment[],
	) => Promise<void>;
	abort: () => void;
	retry: () => void;
	toggleToolCollapse: (toolCallId: string) => void;
	clearError: () => void;
	lastUserContent: string | undefined;
	collapsedTools: Set<string>;
	/** AC107: currently selected model id */
	selectedModel: string;
	setModel: (model: string) => void;
	/** AC103/AC106: usage + finishReason + cost per message id */
	usageMap: Map<string, MessageUsage>;
	/** AC54: staged attachments per user-message order (index = nth user message) */
	sentAttachments: StagedAttachment[][];
	/** AC64: context fill ratio 0-1 */
	contextPressure: number;
	/** AC108: reasoning effort */
	reasoningEffort: ReasoningEffort;
	setReasoningEffort: (effort: ReasoningEffort) => void;
	/** AC50: TTS autoplay for new assistant messages */
	autoplayTts: boolean;
	toggleAutoplayTts: () => void;
	/** AC105: edit a user message and resend from that point */
	editAndResend: (messageId: string, newText: string) => Promise<void>;
	/** AC66: approve a pending tool call */
	approveToolCall: (toolCallId: string) => Promise<void>;
	/** AC66: deny a pending tool call */
	denyToolCall: (toolCallId: string) => Promise<void>;
}

export function useChatSession(): UseChatSessionReturn {
	// AC101: URL-persistent chat ID via nuqs
	const [urlChatId, setUrlChatId] = useQueryState("t");
	const chatIdRef = useRef(urlChatId || localId("chat"));
	const threadIdRef = useRef<string | undefined>(undefined);
	const [collapsedTools, setCollapsedTools] = useState<Set<string>>(new Set());
	const [selectedModel, setSelectedModel] = useState("claude-sonnet-4-6");
	const selectedModelRef = useRef(selectedModel);

	// Usage tracking
	const usageMapRef = useRef<Map<string, MessageUsage>>(new Map());
	const [usageVersion, setUsageVersion] = useState(0);

	// AC56: pending attachments ref (populated before sendMessage, read in prepareSendMessagesRequest)
	const pendingAttachmentsRef = useRef<RequestAttachment[] | undefined>(undefined);
	const pendingReasoningEffortRef = useRef<ReasoningEffort>("medium");

	// AC54: track sent staged attachments indexed by user message order
	const sentAttachmentsRef = useRef<StagedAttachment[][]>([]);
	const [sentAttachmentsVersion, setSentAttachmentsVersion] = useState(0);

	// AC108: reasoning effort
	const [reasoningEffort, setReasoningEffortState] = useState<ReasoningEffort>("medium");
	const reasoningEffortRef = useRef<ReasoningEffort>("medium");

	// Sync chatId to URL on mount if not already there
	// biome-ignore lint/correctness/useExhaustiveDependencies: intentional mount-only effect
	useEffect(() => {
		if (!urlChatId) {
			void setUrlChatId(chatIdRef.current);
		}
	}, []);

	const setModel = useCallback((model: string) => {
		setSelectedModel(model);
		selectedModelRef.current = model;
	}, []);

	const setReasoningEffort = useCallback((effort: ReasoningEffort) => {
		setReasoningEffortState(effort);
		reasoningEffortRef.current = effort;
		pendingReasoningEffortRef.current = effort;
	}, []);

	// AC50: autoplay TTS toggle
	const [autoplayTts, setAutoplayTts] = useState(false);
	const toggleAutoplayTts = useCallback(() => setAutoplayTts((v) => !v), []);

	const { messages, status, error, sendMessage, regenerate, stop, clearError, setMessages } =
		useChat({
			id: chatIdRef.current,
			transport: new DefaultChatTransport({
				api: "/api/agent/chat",
				prepareSendMessagesRequest: ({ messages: msgs }) => {
					const lastUser = msgs.filter((m) => m.role === "user").at(-1);
					const text =
						lastUser?.parts
							.filter((p): p is { type: "text"; text: string } => p.type === "text")
							.map((p) => p.text)
							.join("") ?? "";
					const body: Record<string, unknown> = {
						message: text,
						threadId: threadIdRef.current,
					};
					if (selectedModelRef.current !== "claude-sonnet-4-6") {
						body.model = selectedModelRef.current;
					}
					if (pendingAttachmentsRef.current?.length) {
						body.attachments = pendingAttachmentsRef.current;
					}
					const effort = pendingReasoningEffortRef.current;
					if (effort !== "medium") {
						body.reasoningEffort = effort;
					}
					return { body };
				},
			}),
			onFinish: ({ message, finishReason }) => {
				if (message.role === "assistant") {
					// Usage tokens forwarded by Python via message-metadata SSE event (ACR-G5).
					// threadId forwarded the same way (ACR-G7).
					const meta = message.metadata as Record<string, unknown> | undefined;
					const promptTokens = typeof meta?.promptTokens === "number" ? meta.promptTokens : 0;
					const completionTokens =
						typeof meta?.completionTokens === "number" ? meta.completionTokens : 0;
					// ACR-G7: update threadId from server so follow-up requests use the same thread
					if (typeof meta?.threadId === "string" && meta.threadId) {
						threadIdRef.current = meta.threadId;
					}
					const costs = COST_PER_TOKEN[selectedModelRef.current];
					const costUsd =
						costs && (promptTokens || completionTokens)
							? promptTokens * costs.input + completionTokens * costs.output
							: undefined;
					usageMapRef.current.set(message.id, {
						promptTokens,
						completionTokens,
						finishReason: finishReason ?? "stop",
						costUsd,
					});
					setUsageVersion((v) => v + 1);
				}
			},
		});

	const send = useCallback(
		async (text: string, attachments?: RequestAttachment[], staged?: StagedAttachment[]) => {
			if (!text.trim() || status === "streaming" || status === "submitted") return;
			pendingAttachmentsRef.current = attachments;
			pendingReasoningEffortRef.current = reasoningEffortRef.current;
			// AC54: record staged attachments for display
			sentAttachmentsRef.current = [...sentAttachmentsRef.current, staged ?? []];
			setSentAttachmentsVersion((v) => v + 1);
			await sendMessage({ text });
			pendingAttachmentsRef.current = undefined;
		},
		[status, sendMessage],
	);

	const abort = useCallback(() => {
		stop();
	}, [stop]);

	const retry = useCallback(async () => {
		await regenerate();
	}, [regenerate]);

	// AC105: edit a previous user message, trim history, and resend
	const editAndResend = useCallback(
		async (messageId: string, newText: string) => {
			if (!newText.trim() || status === "streaming" || status === "submitted") return;
			const idx = messages.findIndex((m) => m.id === messageId);
			if (idx === -1) return;
			setMessages(messages.slice(0, idx));
			pendingAttachmentsRef.current = undefined;
			pendingReasoningEffortRef.current = reasoningEffortRef.current;
			sentAttachmentsRef.current = sentAttachmentsRef.current.slice(0, Math.ceil(idx / 2));
			setSentAttachmentsVersion((v) => v + 1);
			await sendMessage({ text: newText });
		},
		[messages, status, setMessages, sendMessage],
	);

	// AC66: approve / deny a pending tool call (BFF → Go Gateway)
	const approveToolCall = useCallback(async (toolCallId: string) => {
		await fetch("/api/agent/approve", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ toolCallId, decision: "approve", threadId: threadIdRef.current }),
		});
	}, []);

	const denyToolCall = useCallback(async (toolCallId: string) => {
		await fetch("/api/agent/approve", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ toolCallId, decision: "deny", threadId: threadIdRef.current }),
		});
	}, []);

	const toggleToolCollapse = useCallback((toolCallId: string) => {
		setCollapsedTools((prev) => {
			const next = new Set(prev);
			if (next.has(toolCallId)) next.delete(toolCallId);
			else next.add(toolCallId);
			return next;
		});
	}, []);

	const isStreaming = status === "streaming";
	const isConnecting = status === "submitted";

	const lastUserMsg = messages.filter((m) => m.role === "user").at(-1);
	const lastUserContent = lastUserMsg?.parts
		.filter((p): p is { type: "text"; text: string } => p.type === "text")
		.map((p) => p.text)
		.join("");

	const usageMap = usageMapRef.current;
	void usageVersion; // consumed to keep lint happy
	void sentAttachmentsVersion;

	// AC64: context pressure from latest assistant usage promptTokens
	const latestAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
	const latestUsage = latestAssistantMsg
		? usageMapRef.current.get(latestAssistantMsg.id)
		: undefined;
	const maxCtx = MODEL_MAX_CONTEXT[selectedModel] ?? DEFAULT_MAX_CONTEXT;
	const contextPressure = latestUsage ? Math.min(latestUsage.promptTokens / maxCtx, 1) : 0;

	return {
		messages,
		isStreaming,
		isConnecting,
		error: error?.message ?? null,
		threadId: threadIdRef.current,
		send,
		abort,
		retry,
		toggleToolCollapse,
		clearError,
		lastUserContent: lastUserContent || undefined,
		collapsedTools,
		selectedModel,
		setModel,
		usageMap,
		sentAttachments: sentAttachmentsRef.current,
		contextPressure,
		reasoningEffort,
		setReasoningEffort,
		autoplayTts,
		toggleAutoplayTts,
		editAndResend,
		approveToolCall,
		denyToolCall,
	};
}
