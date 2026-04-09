"use client";

// QuickNoteCard — adopted from
// _ref/supermemory/apps/web/components/quick-note-card.tsx
// Aenderungen:
// - useProject + useQuickNoteDraft (zustand stores aus supermemory) entfernt → simple useState
// - dmSansClassName() entfernt (DM Sans ist global via layout)
// - inline hex colors auf Tailwind Tokens umgestellt
// - hardcoded SVG Command-Icon ersetzt durch lucide Command icon

import { Command, Loader2, Maximize2, Plus } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface QuickNoteCardProps {
	onSave: (content: string) => void;
	onMaximize?: (content: string) => void;
	isSaving?: boolean;
	initialDraft?: string;
}

export function QuickNoteCard({
	onSave,
	onMaximize,
	isSaving = false,
	initialDraft = "",
}: QuickNoteCardProps) {
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const [draft, setDraft] = useState(initialDraft);

	const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
		setDraft(e.target.value);
	}, []);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
				e.preventDefault();
				if (draft.trim() && !isSaving) {
					onSave(draft);
					setDraft("");
				}
			}
		},
		[draft, isSaving, onSave],
	);

	const handleSaveClick = useCallback(() => {
		if (draft.trim() && !isSaving) {
			onSave(draft);
			setDraft("");
		}
	}, [draft, isSaving, onSave]);

	const handleMaximizeClick = useCallback(() => {
		onMaximize?.(draft);
	}, [draft, onMaximize]);

	const canSave = draft.trim().length > 0 && !isSaving;

	return (
		<div className="bg-card rounded-[22px] p-1" style={{ boxShadow: "var(--shadow-card)" }}>
			<div
				id="quick-note-inner"
				className="bg-popover rounded-[18px] p-3 relative"
				style={{ boxShadow: "var(--shadow-inset)" }}
			>
				{onMaximize && (
					<button
						type="button"
						onClick={handleMaximizeClick}
						className="absolute top-3 right-3 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
						aria-label="Expand to full screen"
					>
						<Maximize2 className="size-[14px]" />
					</button>
				)}

				<textarea
					ref={textareaRef}
					value={draft}
					onChange={handleChange}
					onKeyDown={handleKeyDown}
					placeholder="Quick note — what should the agent remember?"
					disabled={isSaving}
					className={cn(
						"w-full h-[120px] bg-transparent resize-none outline-none",
						"text-[12px] leading-normal text-foreground placeholder:text-muted-foreground",
						"pr-5 disabled:opacity-50",
					)}
				/>

				<div
					id="quick-note-action-bar"
					className="bg-card rounded-[8px] px-2 py-1.5 flex items-center justify-center gap-8 w-full"
					style={{
						boxShadow:
							"0 4px 20px 0 rgba(0, 0, 0, 0.25), inset 1px 1px 1px 0 rgba(255, 255, 255, 0.1)",
					}}
				>
					<Button
						type="button"
						onClick={handleSaveClick}
						disabled={!canSave}
						variant="ghost"
						size="sm"
						className="h-auto py-0 px-0 hover:bg-transparent disabled:opacity-50"
					>
						<span className="flex items-center gap-1.5">
							{isSaving ? (
								<Loader2 className="size-2 animate-spin text-foreground" />
							) : (
								<Plus className="size-2 text-foreground" />
							)}
							<span className="text-[10px] font-medium text-foreground">
								{isSaving ? "Saving..." : "Save note"}
							</span>
						</span>

						<span className="ml-1.5 bg-muted/40 border border-border/40 rounded px-1 py-0.5 flex items-center gap-1 h-4">
							<Command className="size-[10px] text-muted-foreground" />
							<span className="text-[10px] font-medium text-muted-foreground">Enter</span>
						</span>
					</Button>
				</div>
			</div>
		</div>
	);
}
