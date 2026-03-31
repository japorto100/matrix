"use client";

/**
 * Agent Output Editor — Novel (Tiptap + AI Autocomplete + Slash-Commands).
 *
 * Wird für lange Agent-Outputs (Reports, Analysen, Zusammenfassungen) verwendet.
 * Nicht für den Chat-Composer — dort bleibt das einfache Input-Feld.
 */

import { EditorContent, EditorRoot } from "novel";
import { useState } from "react";

interface Props {
	content: string;
	onChange?: (markdown: string) => void;
	readOnly?: boolean;
}

export function AgentOutputEditor({ content, onChange }: Props) {
	const [editorContent, setEditorContent] = useState(content);

	return (
		<div className="rounded-lg border border-border/50 bg-card overflow-hidden">
			<div className="flex items-center justify-between px-3 py-1.5 border-b border-border/30 bg-muted/30">
				<span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
					Agent Output
				</span>
				<button
					type="button"
					onClick={() => navigator.clipboard.writeText(editorContent)}
					className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
				>
					Kopieren
				</button>
			</div>
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
						const md = editor?.storage?.markdown?.getMarkdown?.() ?? editor?.getText?.() ?? "";
						setEditorContent(md);
						onChange?.(md);
					}}
					className="min-h-[200px] max-h-[500px] overflow-y-auto prose prose-sm dark:prose-invert max-w-none p-4"
				/>
			</EditorRoot>
		</div>
	);
}
