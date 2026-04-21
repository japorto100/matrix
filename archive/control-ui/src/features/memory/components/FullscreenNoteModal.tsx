"use client";

// FullscreenNoteModal — adopted from
// _ref/supermemory/apps/web/components/fullscreen-note-modal.tsx
// Aenderungen:
// - Logo + supermemory branding entfernt
// - useAuth + useProject + useQuickNoteDraft (zustand) entfernt
// - TextEditor (supermemory's text-editor/) → unsere NoteEditor (Tiptap)
// - Hardcoded hex colors → Tailwind tokens
// - Hardcoded SVG Command icon → lucide Command icon

import { Command, Loader2, Minimize2, Plus } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { NoteEditor, type NoteEditorRef } from "./NoteEditor";

interface FullscreenNoteModalProps {
	isOpen: boolean;
	onClose: () => void;
	initialContent?: string;
	onSave: (content: string) => void;
	isSaving?: boolean;
	title?: string;
}

export function FullscreenNoteModal({
	isOpen,
	onClose,
	initialContent = "",
	onSave,
	isSaving = false,
	title = "New Note",
}: FullscreenNoteModalProps) {
	const editorRef = useRef<NoteEditorRef>(null);
	const [isEmpty, setIsEmpty] = useState(true);

	useEffect(() => {
		if (isOpen && editorRef.current && initialContent) {
			editorRef.current.setContent(initialContent);
			setIsEmpty(false);
		}
	}, [isOpen, initialContent]);

	const handleSave = useCallback(() => {
		const content = editorRef.current?.getHTML() ?? "";
		if (content && !isSaving) {
			onSave(content);
		}
	}, [isSaving, onSave]);

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen) {
				e.preventDefault();
				onClose();
			}
		};

		if (isOpen) {
			document.addEventListener("keydown", handleKeyDown);
		}

		return () => {
			document.removeEventListener("keydown", handleKeyDown);
		};
	}, [isOpen, onClose]);

	const canSave = !isEmpty && !isSaving;

	return (
		<Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
			<DialogContent
				className={cn(
					"border-none bg-popover flex flex-col p-0 gap-0",
					"w-screen! h-screen! max-w-none! max-h-none! rounded-none",
					"[&>button[type='button']]:hidden",
				)}
			>
				<DialogTitle className="sr-only">{title}</DialogTitle>

				<header className="flex justify-between items-center p-3 md:p-4 border-b border-border/30">
					<div className="flex items-center gap-2">
						<div className="flex flex-col items-start justify-center">
							<p className="text-muted-foreground text-[11px] leading-tight">Matrix · Control</p>
							<p className="text-foreground font-bold text-xl leading-none -mt-1">{title}</p>
						</div>
					</div>

					<div
						id="fullscreen-close-controls"
						className="bg-card rounded-[8px] px-3 py-2.5 flex items-center gap-2.5"
						style={{
							boxShadow:
								"0 4px 20px 0 rgba(0, 0, 0, 0.25), inset 1px 1px 1px 0 rgba(255, 255, 255, 0.1)",
						}}
					>
						<span className="bg-muted/40 border border-border/40 rounded px-1 py-0.5 flex items-center justify-center h-4">
							<span className="text-[10px] font-medium text-muted-foreground">ESC</span>
						</span>
						<button
							type="button"
							onClick={onClose}
							className="text-foreground hover:text-foreground/80 transition-colors cursor-pointer"
							aria-label="Close full screen"
						>
							<Minimize2 className="size-6" />
						</button>
					</div>
				</header>

				<main className="flex-1 flex flex-col items-center px-4 md:px-[15%] pt-8 md:pt-12 pb-24 overflow-auto">
					<div className="w-full max-w-[864px] space-y-4">
						<NoteEditor
							ref={editorRef}
							autoFocus
							placeholder="Start writing your note..."
							onUpdate={setIsEmpty}
							onSubmit={handleSave}
							onEscape={onClose}
							minHeight="400px"
							maxHeight="60vh"
						/>
					</div>
				</main>

				<div id="fullscreen-save-bar" className="fixed bottom-8 left-1/2 -translate-x-1/2">
					<Button
						type="button"
						onClick={handleSave}
						disabled={!canSave}
						className={cn(
							"bg-card rounded-[8px] px-4 py-2.5 flex items-center justify-center gap-1.5",
							"shadow-lg hover:bg-accent/40 disabled:opacity-50",
						)}
					>
						{isSaving ? (
							<Loader2 className="size-4 animate-spin text-foreground" />
						) : (
							<Plus className="size-4 text-foreground" />
						)}
						<span className="text-[14px] font-medium text-foreground">
							{isSaving ? "Saving..." : "Save note"}
						</span>

						<span className="bg-muted/40 border border-border/40 rounded px-1 py-0.5 flex items-center gap-1 h-4 ml-1">
							<Command className="size-[10px] text-muted-foreground" />
							<span className="text-[10px] font-medium text-muted-foreground">Enter</span>
						</span>
					</Button>
				</div>
			</DialogContent>
		</Dialog>
	);
}
