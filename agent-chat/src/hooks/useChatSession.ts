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
import { useAtom, useAtomValue, useSetAtom } from "jotai";
import { useQueryState } from "nuqs";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReasoningEffort } from "../components/AgentChatToolbar";
import { collapsedToolsAtom, toggleToolCollapseAtom, usageMapAtom } from "../context/atoms";
import type { RequestAttachment, StagedAttachment } from "./useAttachments";
import { useAvailableModels } from "./useAvailableModels";
import { computeCost, useModelInfo } from "./useModelInfo";

let idCounter = 0;
function localId(prefix = "chat"): string {
	return `${prefix}-${Date.now()}-${(idCounter++).toString(36)}`;
}

export interface MessageUsage {
	promptTokens: number;
	completionTokens: number;
	reasoningTokens?: number;
	finishReason: string;
	/** AC104: estimated cost in USD (dynamic from ModelInfo pricing) */
	costUsd?: number;
}

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
	/** Model capabilities (reasoning, pricing, context) — dynamic from backend */
	supportsReasoning: boolean;
	reasoningLevels: string[] | null;
	/** AC50: TTS autoplay for new assistant messages */
	autoplayTts: boolean;
	toggleAutoplayTts: () => void;
	/** AC105: edit a user message and resend from that point */
	editAndResend: (messageId: string, newText: string) => Promise<void>;
	/** AC66: approve a pending tool call */
	approveToolCall: (toolCallId: string) => Promise<void>;
	/** AC66: deny a pending tool call */
	denyToolCall: (toolCallId: string) => Promise<void>;
	/** exec-09: set browser tools from WebMCP bridge */
	setBrowserTools: (
		tools: Array<{ name: string; description: string; input_schema: Record<string, unknown> }>,
	) => void;
}

export function useChatSession(): UseChatSessionReturn {
	// AC101: URL-persistent chat ID via nuqs
	const [urlChatId, setUrlChatId] = useQueryState("t");
	const chatIdRef = useRef(urlChatId || localId("chat"));
	const threadIdRef = useRef<string | undefined>(undefined);
	// Jotai Atoms — feingranularer State (kein Re-Render der ganzen Liste)
	const collapsedTools = useAtomValue(collapsedToolsAtom);
	const toggleToolCollapse = useSetAtom(toggleToolCollapseAtom);
	const [usageMap, setUsageMap] = useAtom(usageMapAtom);

	// Model + reasoning defaults loaded from backend (no hardcoded values)
	const { models: availableModels, defaultModel: backendDefaultModel } = useAvailableModels();
	const initialModel = backendDefaultModel || availableModels[0]?.id || "openrouter/free";
	const [selectedModel, setSelectedModel] = useState("");
	const selectedModelRef = useRef("");
	const modelInfo = useModelInfo(selectedModel || initialModel);

	// Sync initial model from backend on first load
	const initializedRef = useRef(false);
	useEffect(() => {
		if (!initializedRef.current && initialModel && !selectedModel) {
			setSelectedModel(initialModel);
			selectedModelRef.current = initialModel;
			initializedRef.current = true;
		}
	}, [initialModel, selectedModel]);

	// AC56: pending attachments ref (populated before sendMessage, read in prepareSendMessagesRequest)
	const pendingAttachmentsRef = useRef<RequestAttachment[] | undefined>(undefined);
	const pendingReasoningEffortRef = useRef<ReasoningEffort>("");

	// AC54: track sent staged attachments indexed by user message order
	const sentAttachmentsRef = useRef<StagedAttachment[][]>([]);
	const [sentAttachmentsVersion, setSentAttachmentsVersion] = useState(0);

	// AC108: reasoning effort — default from backend, no hardcoded "medium"
	const [reasoningEffort, setReasoningEffortState] = useState<ReasoningEffort>("");
	const reasoningEffortRef = useRef<ReasoningEffort>("");

	// exec-09 Phase 4: Browser-Tools via WebMCP (dynamisch je nach Page)
	const browserToolsRef = useRef<
		Array<{ name: string; description: string; input_schema: Record<string, unknown> }>
	>([]);

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
					if (selectedModelRef.current) {
						body.model = selectedModelRef.current;
					}
					if (pendingAttachmentsRef.current?.length) {
						body.attachments = pendingAttachmentsRef.current;
					}
					const effort = pendingReasoningEffortRef.current;
					if (effort) {
						body.reasoningEffort = effort;
					}
					// exec-09: Browser-Tools via WebMCP mitschicken
					if (browserToolsRef.current.length > 0) {
						body.browserTools = browserToolsRef.current;
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
					const reasoningTokens =
						typeof meta?.reasoningTokens === "number" ? meta.reasoningTokens : undefined;
					// ACR-G7: update threadId from server so follow-up requests use the same thread
					if (typeof meta?.threadId === "string" && meta.threadId) {
						threadIdRef.current = meta.threadId;
					}
					// Dynamic cost from ModelInfo (no more hardcoded COST_PER_TOKEN)
					const costUsd = computeCost(modelInfo, promptTokens, completionTokens);
					setUsageMap((prev) => {
						const next = new Map(prev);
						next.set(message.id, {
							promptTokens,
							completionTokens,
							reasoningTokens,
							finishReason: finishReason ?? "stop",
							costUsd,
						});
						return next;
					});
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

	const isStreaming = status === "streaming";
	const isConnecting = status === "submitted";

	const lastUserMsg = messages.filter((m) => m.role === "user").at(-1);
	const lastUserContent = lastUserMsg?.parts
		.filter((p): p is { type: "text"; text: string } => p.type === "text")
		.map((p) => p.text)
		.join("");

	void sentAttachmentsVersion;

	// Prune reasoning from older messages (display optimization).
	// Keeps reasoning only on the last assistant message to reduce visual clutter
	// and rendering cost in long threads. Inspired by AI SDK pruneMessages.
	const prunedMessages = useMemo(() => {
		if (messages.length <= 2) return messages;
		let lastAssistantIdx = -1;
		for (let i = messages.length - 1; i >= 0; i--) {
			if (messages[i].role === "assistant") {
				lastAssistantIdx = i;
				break;
			}
		}
		return messages.map((msg, idx) => {
			if (msg.role !== "assistant" || idx === lastAssistantIdx) return msg;
			const hasReasoning = msg.parts.some((p) => p.type === "reasoning");
			if (!hasReasoning) return msg;
			return {
				...msg,
				parts: msg.parts.filter((p) => p.type !== "reasoning"),
			} as UIMessage;
		});
	}, [messages]);

	// AC64: context pressure from latest assistant usage promptTokens (dynamic from ModelInfo)
	const latestAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
	const latestUsage = latestAssistantMsg ? usageMap.get(latestAssistantMsg.id) : undefined;
	const contextPressure = latestUsage
		? Math.min(latestUsage.promptTokens / (modelInfo.context_length || 200_000), 1)
		: 0;

	return {
		messages: prunedMessages,
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
		supportsReasoning: modelInfo.supports_reasoning,
		reasoningLevels: modelInfo.reasoning_levels,
		autoplayTts,
		toggleAutoplayTts,
		editAndResend,
		approveToolCall,
		denyToolCall,
		setBrowserTools: useCallback(
			(
				tools: Array<{ name: string; description: string; input_schema: Record<string, unknown> }>,
			) => {
				browserToolsRef.current = tools;
			},
			[],
		),
	};
}
