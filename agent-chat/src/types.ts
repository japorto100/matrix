// Agent Chat UI — centralized type definitions
// All domain types live here. Components/hooks import from this file.

// ── Config ──────────────────────────────────────────────────────────────────

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

// ── Models & Reasoning ──────────────────────────────────────────────────────

export type ReasoningEffort = "low" | "medium" | "high";

// ── Chat Session ────────────────────────────────────────────────────────────

export interface MessageUsage {
	promptTokens: number;
	completionTokens: number;
	finishReason: string;
	costUsd?: number;
}

// ── Attachments ─────────────────────────────────────────────────────────────

export interface RequestAttachment {
	base64: string;
	mime_type: string;
	name: string;
}

export interface StagedAttachment {
	id: string;
	file: File;
	previewUrl: string;
	base64?: string;
}

// ── Voice ───────────────────────────────────────────────────────────────────

export type VoiceStatus = "idle" | "connecting" | "active" | "disconnecting";

// ── Global Chat ─────────────────────────────────────────────────────────────

export type ChatMode = "sheet" | "split" | "rail";

// ── Status Types ────────────────────────────────────────────────────────────

export type RailStatus = "idle" | "live" | "degraded" | "reconnecting";

export type StreamStatus = "connected" | "reconnecting" | "degraded";

// ── Sources ─────────────────────────────────────────────────────────────────

export interface SourceItem {
	url: string;
	title?: string;
	description?: string;
	favicon?: string;
}
