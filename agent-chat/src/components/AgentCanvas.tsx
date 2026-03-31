/**
 * AgentCanvas — Infinite Canvas mit tldraw SDK 4.0 (exec-09 Phase 3)
 *
 * Split-View: Agent Chat links, Canvas rechts (oder Tab-Umschaltung).
 * Agent kann Shapes/Text/Widgets auf dem Canvas platzieren via Tool-Results.
 * User kann Canvas-Inhalte arrangieren, verbinden, annotieren.
 */

"use client";

import { createShapeId, type Editor, type TLShapeId, Tldraw } from "tldraw";
import "tldraw/tldraw.css";
import { forwardRef, useCallback, useImperativeHandle, useMemo, useRef } from "react";
import { NovelShapeUtil } from "./canvas/NovelCanvasShape";

export interface AgentCanvasRef {
	/** Wendet ein Canvas-Tool-Result an (von canvas_create/update/delete_shape) */
	applyToolResult: (result: Record<string, unknown>) => void;
}

interface AgentCanvasProps {
	onCanvasChange?: (shapes: object[]) => void;
}

export const AgentCanvas = forwardRef<AgentCanvasRef, AgentCanvasProps>(function AgentCanvas(
	{ onCanvasChange },
	ref,
) {
	const editorRef = useRef<Editor | null>(null);

	useImperativeHandle(ref, () => ({
		applyToolResult(result: Record<string, unknown>) {
			const editor = editorRef.current;
			if (!editor) return;

			const action = result.action as string;

			if (action === "create") {
				const shapeId = createShapeId(result.shape_id as string);
				const shapeType = (result.shape_type as string) ?? "geo";
				const type = shapeType === "novel" ? "novel" : shapeType === "text" ? "text" : "geo";
				editor.createShape({
					id: shapeId,
					type: type as any,
					x: (result.x as number) ?? 0,
					y: (result.y as number) ?? 0,
					props: {
						w: (result.width as number) ?? (type === "novel" ? 400 : 200),
						h: (result.height as number) ?? (type === "novel" ? 300 : 100),
						text: (result.text as string) ?? "",
					},
				} as any);
			} else if (action === "update") {
				const shapeId = result.shape_id as TLShapeId;
				const shape = editor.getShape(shapeId);
				if (!shape) return;
				const updates: Record<string, unknown> = {};
				if (result.x != null) updates.x = result.x;
				if (result.y != null) updates.y = result.y;
				const propUpdates: Record<string, unknown> = {};
				if (result.text != null) propUpdates.text = result.text;
				editor.updateShape({
					id: shapeId,
					type: shape.type,
					...updates,
					...(Object.keys(propUpdates).length ? { props: propUpdates } : {}),
				});
			} else if (action === "delete") {
				const shapeId = result.shape_id as TLShapeId;
				editor.deleteShape(shapeId);
			}
		},
	}));

	const handleMount = useCallback(
		(editor: Editor) => {
			editorRef.current = editor;
			editor.store.listen(() => {
				if (onCanvasChange) {
					const shapes = editor.getCurrentPageShapes();
					onCanvasChange(shapes.map((s) => ({ id: s.id, type: s.type, props: s.props })));
				}
			});
		},
		[onCanvasChange],
	);

	// Custom shapes: Novel Editor block auf dem Canvas
	const shapeUtils = useMemo(() => [NovelShapeUtil], []);

	return (
		<div className="h-full w-full">
			<Tldraw onMount={handleMount} shapeUtils={shapeUtils} />
		</div>
	);
});

export function canvasToContext(shapes: object[]): string {
	if (!shapes.length) return "";
	return `\n[Canvas: ${shapes.length} shapes]\n${JSON.stringify(shapes, null, 2)}`;
}
