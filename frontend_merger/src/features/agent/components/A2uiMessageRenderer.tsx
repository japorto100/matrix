"use client";

import { A2UIRenderer, useA2UIActions } from "@copilotkit/a2ui-renderer";
import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

interface Props {
	surfaceId: string;
	inlineTree?: Record<string, unknown>;
}

/**
 * Wrapper around @copilotkit/a2ui-renderer's A2UIRenderer. When an inlineTree
 * is provided (from the validated render_a2ui_surface tool-result), we inject
 * it into the A2UI store via useA2UIActions().processMessages so the surface
 * paints immediately.
 *
 * Note: A2UIRenderer does NOT accept a tree prop in v0.9 — the MessageProcessor
 * is the only entry point. Passing {initialTree} as a prop is silently dropped.
 */
export function A2uiMessageRenderer({ surfaceId, inlineTree }: Props) {
	const { processMessages } = useA2UIActions();

	useEffect(() => {
		if (!inlineTree) return;
		try {
			processMessages([
				{
					version: "v0.9",
					createSurface: {
						surfaceId,
						tree: inlineTree,
					},
				},
			]);
		} catch (err) {
			console.warn("[A2uiMessageRenderer] processMessages failed:", err);
		}
	}, [surfaceId, inlineTree, processMessages]);

	return (
		<A2UIRenderer
			surfaceId={surfaceId}
			fallback={
				<div className="flex items-center gap-2 p-2 text-xs text-muted-foreground">
					<AlertTriangle className="h-3.5 w-3.5" />
					<span>Widget wird geladen…</span>
				</div>
			}
		/>
	);
}
