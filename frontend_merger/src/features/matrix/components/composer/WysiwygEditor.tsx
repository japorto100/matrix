"use client";

import type { MemberInfo } from "@matrix/lib/hooks/useRoomMembers";
import type { RoomInfo } from "@matrix/lib/types";
import type { Editor } from "@tiptap/core";
import { Mention } from "@tiptap/extension-mention";
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
import { createRoomPillSuggestion, createUserMentionSuggestion } from "./mentionSuggestion";

export interface WysiwygEditorRef {
	/** HTML-Content des Editors */
	getHTML: () => string;
	/** Plain-Text-Content (Fallback body) */
	getText: () => string;
	/** Alle erwähnten User-IDs für m.mentions.user_ids (ohne @room) */
	getMentionedUserIds: () => string[];
	/** Ob @room Mention gesetzt ist (m.mentions.room = true) */
	hasRoomMention: () => boolean;
	/** Editor leeren */
	clear: () => void;
	/** Content setzen (z.B. für Edit-Modus) */
	setContent: (text: string) => void;
	/** Fokus setzen */
	focus: () => void;
	/** Prüft ob Content leer ist */
	isEmpty: () => boolean;
}

interface Props {
	/** Raum-Mitglieder für @-Mention-Autocomplete */
	members: MemberInfo[];
	/** Alle gejointen Räume für #-Room-Pills */
	rooms: RoomInfo[];
	/** Aktueller Raum (wird aus #-Vorschlägen gefiltert) */
	roomId: string;
	/** Eigene User-ID */
	myUserId: string;
	/** Placeholder-Text */
	placeholder?: string;
	/** Disabled-State */
	disabled?: boolean;
	/** Callback bei Content-Änderung */
	onUpdate?: (isEmpty: boolean) => void;
	/** Enter ohne Shift → Senden */
	onSubmit?: () => void;
	/** Escape → Cancel */
	onEscape?: () => void;
	/** CSS-Klasse für den Editor-Container */
	className?: string;
}

// ─── Formatting Toolbar ──────────────────────────────────────────────────────

function FormattingToolbar({ editor }: { editor: Editor | null }) {
	if (!editor) return null;

	const buttons = [
		{
			icon: Bold,
			action: () => editor.chain().focus().toggleBold().run(),
			active: editor.isActive("bold"),
			title: "Fett (Ctrl+B)",
		},
		{
			icon: Italic,
			action: () => editor.chain().focus().toggleItalic().run(),
			active: editor.isActive("italic"),
			title: "Kursiv (Ctrl+I)",
		},
		{
			icon: Strikethrough,
			action: () => editor.chain().focus().toggleStrike().run(),
			active: editor.isActive("strike"),
			title: "Durchgestrichen (Ctrl+Shift+S)",
		},
		{
			icon: Code,
			action: () => editor.chain().focus().toggleCode().run(),
			active: editor.isActive("code"),
			title: "Inline Code (Ctrl+E)",
		},
		{
			icon: SquareCode,
			action: () => editor.chain().focus().toggleCodeBlock().run(),
			active: editor.isActive("codeBlock"),
			title: "Code-Block",
		},
		{
			icon: List,
			action: () => editor.chain().focus().toggleBulletList().run(),
			active: editor.isActive("bulletList"),
			title: "Liste",
		},
		{
			icon: ListOrdered,
			action: () => editor.chain().focus().toggleOrderedList().run(),
			active: editor.isActive("orderedList"),
			title: "Nummerierte Liste",
		},
		{
			icon: Quote,
			action: () => editor.chain().focus().toggleBlockquote().run(),
			active: editor.isActive("blockquote"),
			title: "Zitat (Ctrl+Shift+B)",
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

export const WysiwygEditor = forwardRef<WysiwygEditorRef, Props>(
	(
		{
			members,
			rooms,
			roomId,
			myUserId,
			placeholder,
			disabled,
			onUpdate,
			onSubmit,
			onEscape,
			className,
		},
		ref,
	) => {
		// @ User/Agent Mention Extension
		const UserMention = Mention.configure({
			HTMLAttributes: { class: "mention" },
			suggestion: createUserMentionSuggestion({
				getMembers: () => members,
				myUserId,
			}),
			renderHTML({ options, node }) {
				const id = node.attrs.id as string;
				const label = node.attrs.label ?? id;
				if (id === "@room") {
					// @room → kein Permalink, nur visueller Pill
					return [
						"span",
						{
							...options.HTMLAttributes,
							class: "mention mention-room",
							"data-mention-type": "room",
						},
						"@room",
					];
				}
				// User/Agent Pill → Matrix Permalink
				return [
					"a",
					{
						...options.HTMLAttributes,
						href: `https://matrix.to/#/${id}`,
						class: "mention",
						"data-mention-type": "user",
						"data-user-id": id,
					},
					`@${label}`,
				];
			},
		});

		// # Room Pill Extension (separater Name damit Tiptap beide registriert)
		const RoomPill = Mention.extend({ name: "roomPill" }).configure({
			HTMLAttributes: { class: "mention mention-room-pill" },
			suggestion: createRoomPillSuggestion({
				getRooms: () => rooms,
				currentRoomId: roomId,
			}),
			renderHTML({ options, node }) {
				const id = node.attrs.id as string;
				const label = node.attrs.label ?? id;
				return [
					"a",
					{
						...options.HTMLAttributes,
						href: `https://matrix.to/#/${id}`,
						class: "mention mention-room-pill",
						"data-mention-type": "room-pill",
					},
					`#${label}`,
				];
			},
		});

		const editor = useEditor({
			immediatelyRender: false,
			extensions: [
				StarterKit.configure({ heading: false }),
				Placeholder.configure({ placeholder: placeholder ?? "Nachricht schreiben..." }),
				UserMention,
				RoomPill,
			],
			editorProps: {
				attributes: {
					class: cn(
						"min-h-[40px] max-h-[160px] overflow-y-auto outline-none text-sm px-3 py-2",
						"prose prose-sm dark:prose-invert max-w-none",
						"[&_.mention]:text-primary [&_.mention]:font-medium [&_.mention]:cursor-default",
						"[&_.mention-room]:text-amber-500",
						"[&_.mention-room-pill]:text-blue-400",
						"[&_p]:my-0",
					),
				},
				handleKeyDown: (_view, event) => {
					if (event.key === "Enter" && !event.shiftKey) {
						// Nicht senden wenn Mention-Dropdown offen ist
						const mentionPopup = document.querySelector("[data-tippy-root]");
						if (mentionPopup) return false;
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

		// Ref-API für den Parent (MessageComposer)
		useImperativeHandle(ref, () => ({
			getHTML: () => {
				if (!editor) return "";
				const html = editor.getHTML();
				if (html === "<p></p>") return "";
				return html;
			},
			getText: () => {
				if (!editor) return "";
				return editor.getText();
			},
			getMentionedUserIds: () => {
				if (!editor) return [];
				const ids: string[] = [];
				editor.state.doc.descendants((node) => {
					// mention = User/Agent, aber NICHT @room
					if (node.type.name === "mention" && node.attrs.id && node.attrs.id !== "@room") {
						ids.push(node.attrs.id as string);
					}
				});
				return [...new Set(ids)];
			},
			hasRoomMention: () => {
				if (!editor) return false;
				let found = false;
				editor.state.doc.descendants((node) => {
					if (node.type.name === "mention" && node.attrs.id === "@room") {
						found = true;
					}
				});
				return found;
			},
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

WysiwygEditor.displayName = "WysiwygEditor";
