// Agent Chat UI — type definitions (Phase 22d)
// ChatBlock/ChatMessage/SseEvent types removed — replaced by UIMessage from ai SDK.

export interface AgentChatConfig {
	/** Go Gateway SSE endpoint for streaming agent responses */
	streamEndpoint: string;
	/** Agent identifier — maps to Python memory-service session */
	agentId?: string;
	/** Show tool-call events in the thread */
	showToolCalls?: boolean;
}

export interface ChatThread {
	id: string;
	title?: string;
	createdAt: number;
	updatedAt: number;
}
