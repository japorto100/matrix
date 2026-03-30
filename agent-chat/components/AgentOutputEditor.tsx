"use client";

/**
 * Agent Output Editor — Novel (Tiptap + AI Autocomplete + Slash-Commands).
 *
 * Wird für lange Agent-Outputs (Reports, Analysen, Zusammenfassungen) verwendet.
 * Der User kann Agent-Output direkt editieren, kopieren, oder weiterverarbeiten.
 *
 * Features:
 * - Notion-style Block-Editor (Headings, Lists, Code, Quotes, Tables)
 * - Slash-Commands (/table, /code, /heading, /quote)
 * - AI Autocomplete (Tab zum Akzeptieren)
 * - Export als Markdown/HTML
 *
 * Nicht für den Chat-Composer — dort bleibt das einfache Input-Feld.
 */

import { Editor } from "novel";
import { useState } from "react";

interface Props {
	/** Initialer Content (Markdown vom Agent) */
	content: string;
	/** Callback wenn Content geändert wird */
	onChange?: (markdown: string) => void;
	/** Readonly-Modus (Agent streamt noch) */
	readOnly?: boolean;
}

export function AgentOutputEditor({ content, onChange, readOnly }: Props) {
	const [editorContent, setEditorContent] = useState(content);

	return (
		<div className="rounded-lg border border-border/50 bg-card overflow-hidden">
			<div className="flex items-center justify-between px-3 py-1.5 border-b border-border/30 bg-muted/30">
				<span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
					Agent Output — Editierbar
				</span>
				<button
					type="button"
					onClick={() => navigator.clipboard.writeText(editorContent)}
					className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
				>
					Kopieren
				</button>
			</div>
			<Editor
				defaultValue={content}
				onUpdate={(editor) => {
					if (editor) {
						const md = editor.storage.markdown?.getMarkdown?.() ?? editor.getText();
						setEditorContent(md);
						onChange?.(md);
					}
				}}
				disableLocalStorage
				className="min-h-[200px] max-h-[500px] overflow-y-auto prose prose-sm dark:prose-invert max-w-none p-4"
			/>
		</div>
	);
}
