"use client";

import { BrainCircuit, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

/** Collapsible reasoning/thinking block for assistant messages with extended thinking. */
export function ReasoningBlock({ text }: { text: string }) {
	const [open, setOpen] = useState(false);
	return (
		<div className="mt-1 rounded border border-border/50 bg-muted/20 text-xs">
			<button
				type="button"
				className="flex w-full items-center gap-1.5 px-2 py-1 text-left text-muted-foreground hover:text-foreground transition-colors"
				onClick={() => setOpen((v) => !v)}
			>
				{open ? (
					<ChevronDown className="h-3 w-3 shrink-0" />
				) : (
					<ChevronRight className="h-3 w-3 shrink-0" />
				)}
				<BrainCircuit className="h-3 w-3 shrink-0" />
				<span className="font-semibold">Thinking</span>
			</button>
			{open && (
				<div className="border-t border-border/40 px-2 py-1.5 text-[11px] text-muted-foreground/80 italic whitespace-pre-wrap">
					{text}
				</div>
			)}
		</div>
	);
}
