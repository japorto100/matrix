/**
 * NovelCanvasShape — tldraw Custom Shape mit eingebettetem Novel Editor (exec-09 Phase 3.3)
 *
 * Ermoeglicht Notion-style Block-Editing direkt auf dem Infinite Canvas.
 * Agent kann Text-Bloecke erstellen, User kann sie inline editieren.
 */

"use client";

import { EditorContent, EditorRoot } from "novel";
import { useState } from "react";
import { BaseBoxShapeUtil, HTMLContainer } from "tldraw";

// Shape type — using any to bypass tldraw's strict union type constraint for custom shapes
type NovelShape = any;

export class NovelShapeUtil extends BaseBoxShapeUtil<NovelShape> {
	static override type = "novel" as const;

	getDefaultProps() {
		return {
			w: 400,
			h: 300,
			text: "",
		};
	}

	component(shape: NovelShape) {
		return (
			<HTMLContainer id={shape.id}>
				<NovelEditorInShape
					text={shape.props.text}
					onTextChange={(text: string) => {
						this.editor.updateShape({
							id: shape.id,
							type: "novel",
							props: { ...shape.props, text },
						} as any);
					}}
				/>
			</HTMLContainer>
		);
	}

	indicator(shape: NovelShape) {
		return <rect width={shape.props.w} height={shape.props.h} />;
	}
}

function NovelEditorInShape({
	text,
	onTextChange,
}: {
	text: string;
	onTextChange: (text: string) => void;
}) {
	const [content, setContent] = useState(text);

	return (
		<div
			className="h-full w-full overflow-auto bg-background rounded border p-2"
			onPointerDown={(e) => e.stopPropagation()}
		>
			<EditorRoot>
				<EditorContent
					initialContent={
						content
							? {
									type: "doc",
									content: [{ type: "paragraph", content: [{ type: "text", text: content }] }],
								}
							: undefined
					}
					onUpdate={({ editor }: { editor: any }) => {
						const newText = editor.getText();
						setContent(newText);
						onTextChange(newText);
					}}
					className="prose prose-sm dark:prose-invert max-w-none min-h-[100px]"
				/>
			</EditorRoot>
		</div>
	);
}
