"use client";

// Agent Chat Panel — Phase 22d / 22f + exec-09 (MCP, Generative UI, Canvas)
// Thin orchestrator: wires useChat session hook + sub-components + protocol providers.
// Architecture: AgentChatPanel → /api/agent/chat (BFF) → Go Gateway → Python/Anthropic

import { useCallback, useEffect, useRef, useState } from "react";
import { AgentCanvas, type AgentCanvasRef, canvasToContext } from "./components/AgentCanvas";
import { AgentChatComposer, type AgentChatComposerRef } from "./components/AgentChatComposer";
import { AgentChatErrorBanner } from "./components/AgentChatErrorBanner";
import { AgentChatEventRail } from "./components/AgentChatEventRail";
import { AgentChatHeader } from "./components/AgentChatHeader";
import { AgentChatReconnectBanner } from "./components/AgentChatReconnectBanner";
import { AgentChatThread } from "./components/AgentChatThread";
import { AgentChatToolbar } from "./components/AgentChatToolbar";
import { FrontendToolsBridge } from "./hooks/FrontendToolsBridge";
import { useChatSession } from "./hooks/useChatSession";
import { useMcpTools } from "./hooks/useMcpTools";
import { useWebMcpBridge } from "./hooks/useWebMcpBridge";
import { useWebMcpTools } from "./hooks/useWebMcpTools";
import { AgentProviders } from "./providers/AgentProviders";
import type { AgentChatConfig } from "./types";

interface AgentChatPanelProps {
	config?: Partial<AgentChatConfig>;
	/** AC68: called by parent (GlobalChatOverlay) after panel opens to focus composer */
	onMounted?: (focusFn: () => void) => void;
}

function AgentChatPanelInner({ config: _config, onMounted }: AgentChatPanelProps) {
	const composerRef = useRef<AgentChatComposerRef>(null);
	const canvasRef = useRef<AgentCanvasRef>(null);
	const [showCanvas, setShowCanvas] = useState(false);
	const canvasShapesRef = useRef<object[]>([]);

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
		contextDiagnostics,
		reasoningEffort,
		setReasoningEffort,
		autoplayTts,
		toggleAutoplayTts,
		editAndResend,
		approveToolCall,
		denyToolCall,
		setBrowserTools,
	} = useChatSession();

	// exec-09: MCP Tools (standardisierte Tool-Discovery + Calling)
	const { mcpTools, mcpStatus } = useMcpTools();

	// exec-09 Phase 4: WebMCP Bridge (Browser-Tools → Backend-Agent)
	const {
		toolDefinitions: browserToolDefs,
		executeBrowserTool,
		isAvailable: webMcpAvailable,
	} = useWebMcpBridge();

	// Browser-Tools an Chat-Session weiterleiten (werden im Request mitgeschickt)
	useEffect(() => {
		setBrowserTools(browserToolDefs);
	}, [browserToolDefs, setBrowserTools]);

	// exec-09 Phase 4: WebMCP Tools via navigator.modelContext registrieren
	useWebMcpTools({
		onSymbolChange: (symbol) => console.log("[WebMCP] Symbol changed:", symbol),
		onTimeframeChange: (tf) => console.log("[WebMCP] Timeframe changed:", tf),
		getChartState: () => ({ symbol: "EUR/USD", timeframe: "4H" }),
	});

	// exec-09: Tool-Results verarbeiten (Canvas + Browser-Tools)
	const appliedToolsRef = useRef(new Set<string>());
	useEffect(() => {
		for (const msg of messages) {
			if (msg.role !== "assistant") continue;
			for (const part of msg.parts) {
				if (part.type !== "tool-invocation") continue;
				const p = part as {
					toolInvocation?: {
						toolCallId: string;
						toolName: string;
						state: string;
						result?: unknown;
					};
				};
				const inv = p.toolInvocation;
				if (!inv || inv.state !== "result") continue;
				if (appliedToolsRef.current.has(inv.toolCallId)) continue;

				const result = inv.result as Record<string, unknown> | undefined;
				if (!result) continue;

				// Canvas-Tool-Results → Canvas-Ref
				if (inv.toolName.startsWith("canvas_") && canvasRef.current && showCanvas) {
					appliedToolsRef.current.add(inv.toolCallId);
					canvasRef.current.applyToolResult(result);
				}

				// Browser-Tool-Results → WebMCP Bridge ausfuehren
				if (result.action === "browser_execute" && result.tool_name) {
					appliedToolsRef.current.add(inv.toolCallId);
					void executeBrowserTool(
						result.tool_name as string,
						(result.tool_input as Record<string, unknown>) ?? {},
					)
						.then((browserResult) => {
							console.log("[WebMCP] Browser tool executed:", result.tool_name, browserResult);
						})
						.catch((err) => {
							console.error("[WebMCP] Browser tool failed:", result.tool_name, err);
						});
				}
			}
		}
	}, [messages, showCanvas, executeBrowserTool]);

	// exec-09: Canvas state als Agent-Context mitsenden
	const handleCanvasChange = useCallback((shapes: object[]) => {
		canvasShapesRef.current = shapes;
	}, []);

	const sendWithContext = useCallback(
		async (
			text: string,
			attachments?: Parameters<typeof send>[1],
			staged?: Parameters<typeof send>[2],
		) => {
			const parts: string[] = [text];
			// Canvas-Kontext anhaengen wenn Canvas offen + Shapes vorhanden
			if (showCanvas && canvasShapesRef.current.length > 0) {
				parts.push(canvasToContext(canvasShapesRef.current));
			}
			// WebMCP Browser-Tools als Kontext anhaengen (Agent weiss welche Page-Tools verfuegbar sind)
			if (browserToolDefs.length > 0) {
				parts.push(`\n[Browser Tools: ${browserToolDefs.map((t) => t.name).join(", ")}]`);
			}
			await send(parts.join("\n"), attachments, staged);
		},
		[send, showCanvas, browserToolDefs],
	);

	const railStatus = isConnecting ? "reconnecting" : isStreaming ? "live" : "idle";

	return (
		<div className="flex h-full overflow-hidden">
			{/* Chat Panel */}
			<div
				className={`flex flex-col bg-background overflow-hidden ${showCanvas ? "w-1/2" : "w-full"}`}
			>
				<AgentChatHeader />

				<AgentChatToolbar
					selectedModel={selectedModel}
					onModelChange={setModel}
					reasoningEffort={reasoningEffort}
					onReasoningEffortChange={setReasoningEffort}
					autoplayTts={autoplayTts}
					onAutoplayToggle={toggleAutoplayTts}
				/>

				<AgentChatEventRail
					status={railStatus}
					isStreaming={isStreaming}
					provider={contextDiagnostics.provider}
					contextPressure={contextPressure}
					degradationFlags={contextDiagnostics.degradationFlags}
					sourceLayerCounts={contextDiagnostics.sourceLayerCounts}
				/>

				<AgentChatThread
					messages={messages}
					isConnecting={isConnecting}
					isStreaming={isStreaming}
					collapsedTools={collapsedTools}
					onToggleBlock={toggleToolCollapse}
					onSuggestion={(text) => void sendWithContext(text)}
					usageMap={usageMap}
					sentAttachments={sentAttachments}
					autoplayTts={autoplayTts}
					onEditMessage={editAndResend}
					onRegenerate={retry}
					onApproveToolCall={approveToolCall}
					onDenyToolCall={denyToolCall}
				/>

				<AgentChatReconnectBanner status={isConnecting ? "reconnecting" : "live"} />

				{error && <AgentChatErrorBanner message={error} onDismiss={clearError} />}

				<AgentChatComposer
					ref={handleComposerRef}
					isStreaming={isStreaming}
					threadId={threadId}
					onSend={sendWithContext}
					onAbort={abort}
					onRetry={retry}
					hasError={!!error}
					savedInput={lastUserContent}
				/>

				{/* exec-09: MCP + Canvas Status Bar */}
				<div className="flex items-center gap-2 px-3 py-1 text-[10px] text-muted-foreground border-t">
					<span>
						MCP: {mcpStatus} ({mcpTools.length} tools) | WebMCP:{" "}
						{webMcpAvailable ? `${browserToolDefs.length} browser tools` : "off"}
					</span>
					<span className="ml-auto">
						<button
							type="button"
							onClick={() => setShowCanvas((v) => !v)}
							className="hover:text-foreground transition-colors"
						>
							{showCanvas ? "Close Canvas" : "Open Canvas"}
						</button>
					</span>
				</div>
			</div>

			{/* exec-09 Phase 3: Infinite Canvas (tldraw) */}
			{showCanvas && (
				<div className="w-1/2 border-l">
					<AgentCanvas ref={canvasRef} onCanvasChange={handleCanvasChange} />
				</div>
			)}

			{/* exec-09: CopilotKit Frontend-Tools (env-gated — registers AG-UI actions) */}
			<FrontendToolsBridge
				onSymbolChange={(symbol) => console.log("[AG-UI] Symbol changed:", symbol)}
				onTimeframeChange={(tf) => console.log("[AG-UI] Timeframe changed:", tf)}
				onPanelOpen={(panel) => console.log("[AG-UI] Panel opened:", panel)}
				onNavigate={(path) => console.log("[AG-UI] Navigate to:", path)}
			/>
		</div>
	);
}

// Export mit Providers gewrappt
export function AgentChatPanel(props: AgentChatPanelProps) {
	return (
		<AgentProviders>
			<AgentChatPanelInner {...props} />
		</AgentProviders>
	);
}
