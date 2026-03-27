"use client";

// Agent Chat Panel — Phase 22d / 22f
// Thin orchestrator: wires useChat session hook + sub-components.
// Architecture: AgentChatPanel → /api/agent/chat (BFF) → Go Gateway → Python/Anthropic

import { useRef } from "react";
import { AgentChatComposer, type AgentChatComposerRef } from "./components/AgentChatComposer";
import { AgentChatErrorBanner } from "./components/AgentChatErrorBanner";
import { AgentChatEventRail } from "./components/AgentChatEventRail";
import { AgentChatHeader } from "./components/AgentChatHeader";
import { AgentChatReconnectBanner } from "./components/AgentChatReconnectBanner";
import { AgentChatThread } from "./components/AgentChatThread";
import { AgentChatToolbar } from "./components/AgentChatToolbar";
import { useChatSession } from "./hooks/useChatSession";
import type { AgentChatConfig } from "./types";

interface AgentChatPanelProps {
	config?: Partial<AgentChatConfig>;
	/** AC68: called by parent (GlobalChatOverlay) after panel opens to focus composer */
	onMounted?: (focusFn: () => void) => void;
}

export function AgentChatPanel({ config: _config, onMounted }: AgentChatPanelProps) {
	const composerRef = useRef<AgentChatComposerRef>(null);

	// AC68: expose focus to parent on first render
	const handleComposerRef = (el: AgentChatComposerRef | null) => {
		(composerRef as React.MutableRefObject<AgentChatComposerRef | null>).current = el;
		if (el && onMounted) onMounted(() => el.focus());
	};

	const {
		messages,
		isStreaming,
		isConnecting,
		error,
		threadId,
		send,
		abort,
		retry,
		toggleToolCollapse,
		clearError,
		lastUserContent,
		collapsedTools,
		selectedModel,
		setModel,
		usageMap,
		sentAttachments,
		contextPressure,
		reasoningEffort,
		setReasoningEffort,
		autoplayTts,
		toggleAutoplayTts,
		editAndResend,
		approveToolCall,
		denyToolCall,
	} = useChatSession();

	const railStatus = isConnecting ? "reconnecting" : isStreaming ? "live" : "idle";

	return (
		<div className="flex h-full flex-col bg-background overflow-hidden">
			<AgentChatHeader />

			{/* AC71/AC107/AC108: Model selector + reasoning effort + thread controls */}
			<AgentChatToolbar
				selectedModel={selectedModel}
				onModelChange={setModel}
				reasoningEffort={reasoningEffort}
				onReasoningEffortChange={setReasoningEffort}
				autoplayTts={autoplayTts}
				onAutoplayToggle={toggleAutoplayTts}
			/>

			{/* AC70/AC64: Stream status rail + context pressure bar */}
			<AgentChatEventRail
				status={railStatus}
				isStreaming={isStreaming}
				contextPressure={contextPressure}
			/>

			{/* AC54/AC103: Thread with usage badges + attachment display */}
			<AgentChatThread
				messages={messages}
				isConnecting={isConnecting}
				isStreaming={isStreaming}
				collapsedTools={collapsedTools}
				onToggleBlock={toggleToolCollapse}
				onSuggestion={(text) => void send(text)}
				usageMap={usageMap}
				sentAttachments={sentAttachments}
				autoplayTts={autoplayTts}
				onEditMessage={editAndResend}
				onRegenerate={retry}
				onApproveToolCall={approveToolCall}
				onDenyToolCall={denyToolCall}
			/>

			{/* AC72: Reconnect/degraded banner (separate from error) */}
			<AgentChatReconnectBanner status={isConnecting ? "reconnecting" : "live"} />

			{error && <AgentChatErrorBanner message={error} onDismiss={clearError} />}

			{/* AC51c/AC53/AC56: Composer with attach + drag+drop + clipboard paste */}
			<AgentChatComposer
				ref={handleComposerRef}
				isStreaming={isStreaming}
				threadId={threadId}
				onSend={send}
				onAbort={abort}
				onRetry={retry}
				hasError={!!error}
				savedInput={lastUserContent}
			/>
		</div>
	);
}
