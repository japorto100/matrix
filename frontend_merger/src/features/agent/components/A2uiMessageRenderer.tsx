"use client";

import { A2UIRenderer } from "@copilotkit/a2ui-renderer";
import { AlertTriangle } from "lucide-react";

interface Props {
	surfaceId: string;
	inlineTree?: Record<string, unknown>;
}

/**
 * Wrapper around @copilotkit/a2ui-renderer's A2UIRenderer with a sensible
 * fallback for chat-inline use. When an inlineTree is provided (from the
 * validated render_a2ui_surface tool-result) we pass it via initialTree so
 * the widget paints immediately without waiting for a live A2UI stream.
 */
export function A2uiMessageRenderer({ surfaceId, inlineTree }: Props) {
	return (
		<A2UIRenderer
			surfaceId={surfaceId}
			fallback={
				<div className="flex items-center gap-2 p-2 text-xs text-muted-foreground">
					<AlertTriangle className="h-3.5 w-3.5" />
					<span>Widget wird geladen…</span>
				</div>
			}
			{...(inlineTree ? { initialTree: inlineTree } : {})}
		/>
	);
}
