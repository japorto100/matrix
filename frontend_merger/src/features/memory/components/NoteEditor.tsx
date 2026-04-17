"use client";

// NoteEditor — Tiptap rich text editor for AddMemoryModal "Note" tab + QuickNoteCard
// Pattern adopted from D:/matrix/nextjs-chat/src/components/matrix/composer/WysiwygEditor.tsx
// (Matrix mentions removed — Memory notes don't need @-user mentions).
// Same StarterKit + Placeholder + FormattingToolbar API.

import type { Editor } from "@tiptap/core";
import { Placeholder } from "@tiptap/extension-placeholder";
import { EditorContent, useEditor } from "@tiptap/react";
import { StarterKit } from "@tiptap/starter-kit";
import {
	Bold,
	Code,
	Italic,
	List,
	ListOrdered,
	Quote,
	SquareCode,
	Strikethrough,
} from "lucide-react";
import { forwardRef, useEffect, useImperativeHandle } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface NoteEditorRef {
	getHTML: () => string;
	getText: () => string;
	clear: () => void;
	setContent: (text: string) => void;
	focus: () => void;
	isEmpty: () => boolean;
}

interface NoteEditorProps {
	placeholder?: string;
	disabled?: boolean;
	autoFocus?: boolean;
	onUpdate?: (isEmpty: boolean) => void;
	onSubmit?: () => void;
	onEscape?: () => void;
	className?: string;
	minHeight?: string;
	maxHeight?: string;
}

// ─── Formatting Toolbar (1:1 from nextjs-chat WysiwygEditor) ─────────────────

function FormattingToolbar({ editor }: { editor: Editor | null }) {
	if (!editor) return null;

	const buttons = [
		{
			icon: Bold,
			action: () => editor.chain().focus().toggleBold().run(),
			active: editor.isActive("bold"),
			title: "Bold (Ctrl+B)",
		},
		{
			icon: Italic,
			action: () => editor.chain().focus().toggleItalic().run(),
			active: editor.isActive("italic"),
			title: "Italic (Ctrl+I)",
		},
		{
			icon: Strikethrough,
			action: () => editor.chain().focus().toggleStrike().run(),
			active: editor.isActive("strike"),
			title: "Strikethrough",
		},
		{
			icon: Code,
			action: () => editor.chain().focus().toggleCode().run(),
			active: editor.isActive("code"),
			title: "Inline code (Ctrl+E)",
		},
		{
			icon: SquareCode,
			action: () => editor.chain().focus().toggleCodeBlock().run(),
			active: editor.isActive("codeBlock"),
			title: "Code block",
		},
		{
			icon: List,
			action: () => editor.chain().focus().toggleBulletList().run(),
			active: editor.isActive("bulletList"),
			title: "Bullet list",
		},
		{
			icon: ListOrdered,
			action: () => editor.chain().focus().toggleOrderedList().run(),
			active: editor.isActive("orderedList"),
			title: "Ordered list",
		},
		{
			icon: Quote,
			action: () => editor.chain().focus().toggleBlockquote().run(),
			active: editor.isActive("blockquote"),
			title: "Quote",
		},
	];

	return (
		<div className="flex items-center gap-0.5 px-2 py-1 border-b border-border/30">
			{buttons.map(({ icon: Icon, action, active, title }) => (
				<Button
					key={title}
					type="button"
					variant="ghost"
					size="icon"
					className={cn(
						"h-7 w-7 text-muted-foreground hover:text-foreground",
						active && "bg-accent text-accent-foreground",
					)}
					onClick={action}
					title={title}
					tabIndex={-1}
				>
					<Icon className="h-3.5 w-3.5" />
				</Button>
			))}
		</div>
	);
}

// ─── Editor Component ────────────────────────────────────────────────────────

export const NoteEditor = forwardRef<NoteEditorRef, NoteEditorProps>(
	(
		{
			placeholder,
			disabled,
			autoFocus,
			onUpdate,
			onSubmit,
			onEscape,
			className,
			minHeight = "120px",
			maxHeight = "320px",
		},
		ref,
	) => {
		const editor = useEditor({
			immediatelyRender: false,
			extensions: [
				StarterKit.configure({ heading: false }),
				Placeholder.configure({
					placeholder: placeholder ?? "Write a note…",
				}),
			],
			editorProps: {
				attributes: {
					class: cn(
						"outline-none text-sm px-3 py-2",
						"prose prose-sm dark:prose-invert max-w-none",
						"[&_p]:my-0",
					),
					style: `min-height: ${minHeight}; max-height: ${maxHeight}; overflow-y: auto;`,
				},
				handleKeyDown: (_view, event) => {
					if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
						event.preventDefault();
						onSubmit?.();
						return true;
					}
					if (event.key === "Escape") {
						onEscape?.();
						return true;
					}
					return false;
				},
			},
			onUpdate: ({ editor: e }) => {
				onUpdate?.(e.isEmpty);
			},
		});

		useImperativeHandle(ref, () => ({
			getHTML: () => {
				if (!editor) return "";
				const html = editor.getHTML();
				if (html === "<p></p>") return "";
				return html;
			},
			getText: () => editor?.getText() ?? "",
			clear: () => {
				editor?.commands.clearContent(true);
			},
			setContent: (text: string) => {
				editor?.commands.setContent(text);
			},
			focus: () => {
				editor?.commands.focus("end");
			},
			isEmpty: () => editor?.isEmpty ?? true,
		}));

		useEffect(() => {
			if (editor) editor.setEditable(!disabled);
		}, [editor, disabled]);

		useEffect(() => {
			if (autoFocus && editor) editor.commands.focus("end");
		}, [autoFocus, editor]);

		return (
			<div
				className={cn(
					"rounded-xl bg-muted/30 border border-border/50",
					"focus-within:ring-1 focus-within:ring-ring",
					disabled && "opacity-50 cursor-not-allowed",
					className,
				)}
			>
				<FormattingToolbar editor={editor} />
				<EditorContent editor={editor} />
			</div>
		);
	},
);

NoteEditor.displayName = "NoteEditor";
