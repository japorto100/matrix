"use client";

import { isA2uiPacket, toRendererMessage } from "@agent/lib/a2ui-packets";
import { useA2UIActions } from "@copilotkit/a2ui-renderer";
import { useCallback } from "react";

/**
 * Plan-v2 Phase-2 #34 — SSE → A2UI renderer bridge.
 *
 * Returns an `onDataPart` callback that useChat (from @ai-sdk/react v6)
 * invokes for every packet it doesn't parse as a first-class message /
 * tool / reasoning delta — i.e. everything our backend emits with a
 * `data-*` prefix. Ansatz-X packets carry `data-a2ui-*` types, so we
 * filter them here and forward to the @copilotkit/a2ui-renderer store
 * via processMessages.
 *
 * The store is provided at the app root by `A2uiRootProvider` (see
 * features/agent/providers/AgentProviders.tsx), so surfaces pushed
 * here become visible to BOTH the chat-inline canvas (surfaceId like
 * `chat-<msgId>`) AND the standalone landing-page canvas
 * (`A2uiCanvas surfaceId="main"`). No duplicate subscription needed
 * on the canvas side — the store is the single source of truth.
 *
 * Wiring (in useChatSession):
 *
 *     const onA2uiDataPart = useA2uiSseSubscriber();
 *     useChat({
 *       ...,
 *       onData: (dataPart) => onA2uiDataPart(dataPart),
 *     });
 *
 * Non-a2ui data parts are ignored (returned false) so other data-part
 * consumers can coexist. Malformed a2ui payloads are swallowed with a
 * dev-mode console warn — we never want one broken widget to tank the
 * whole chat turn.
 */
export function useA2uiSseSubscriber() {
	const { processMessages } = useA2UIActions();

	return useCallback(
		(dataPart: unknown): boolean => {
			if (!isA2uiPacket(dataPart)) return false;
			try {
				const rendererMsg = toRendererMessage(dataPart);
				// @copilotkit/a2ui-renderer types processMessages as
				// Array<Record<string, unknown>>. Our message is a proper
				// subset; cast is safe.
				processMessages([rendererMsg as unknown as Record<string, unknown>]);
				return true;
			} catch (err) {
				if (process.env.NODE_ENV !== "production") {
					console.warn("[useA2uiSseSubscriber] processMessages failed:", err, dataPart);
				}
				return true; // we owned the packet, don't let useChat log it as unknown
			}
		},
		[processMessages],
	);
}
