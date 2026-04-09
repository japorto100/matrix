"use client";

// HighlightsCard — adopted from
// _ref/supermemory/apps/web/components/highlights-card.tsx
// Aenderungen:
// - dmSansClassName entfernt (DM Sans via layout)
// - Logo + analytics + supermemory branding entfernt
// - Hardcoded #0B1017, #4BA0FA, etc. → Tailwind tokens (bg-popover, primary, etc.)
// - Brand text "powered by supermemory" → "Memory-derived"

import {
	ChevronLeft,
	ChevronRight,
	Info,
	Link2,
	Loader2,
	MessageSquare,
	Sparkles,
} from "lucide-react";
import { useCallback, useState } from "react";
import { cn } from "@/lib/utils";

export type HighlightFormat = "paragraph" | "bullets" | "quote" | "one_liner";

export interface HighlightItem {
	id: string;
	title: string;
	content: string;
	format: HighlightFormat;
	query: string;
	source_episode_ids: string[];
}

interface HighlightsCardProps {
	items: HighlightItem[];
	onChat?: (seed: string) => void;
	onShowRelated?: (query: string) => void;
	isLoading?: boolean;
}

function renderContent(content: string, format: HighlightFormat) {
	switch (format) {
		case "bullets": {
			const lines = content
				.split("\n")
				.map((line) => line.replace(/^[-•*]\s*/, "").trim())
				.filter(Boolean);
			return (
				<ul className="list-disc pl-[18px] space-y-0">
					{lines.map((line, idx) => (
						<li key={`${idx}-${line.slice(0, 8)}`} className="text-[12px] leading-normal">
							{line}
						</li>
					))}
				</ul>
			);
		}
		case "quote":
			return (
				<p className="text-[12px] leading-normal italic border-l-2 border-primary pl-2">
					"{content}"
				</p>
			);
		case "one_liner":
			return <p className="text-[12px] leading-normal font-medium">{content}</p>;
		default:
			return <p className="text-[12px] leading-normal">{content}</p>;
	}
}

export function HighlightsCard({
	items,
	onChat,
	onShowRelated,
	isLoading = false,
}: HighlightsCardProps) {
	const [activeIndex, setActiveIndex] = useState(0);
	const currentItem = items[activeIndex];

	const handlePrev = useCallback(() => {
		setActiveIndex((prev) => (prev > 0 ? prev - 1 : items.length - 1));
	}, [items.length]);

	const handleNext = useCallback(() => {
		setActiveIndex((prev) => (prev < items.length - 1 ? prev + 1 : 0));
	}, [items.length]);

	const handleChat = useCallback(() => {
		if (!currentItem || !onChat) return;
		onChat(`Tell me more about "${currentItem.title}"`);
	}, [currentItem, onChat]);

	const handleShowRelated = useCallback(() => {
		if (!currentItem || !onShowRelated) return;
		onShowRelated(currentItem.query || currentItem.title);
	}, [currentItem, onShowRelated]);

	if (isLoading) {
		return (
			<div className="bg-popover border border-border/30 rounded-[18px] p-3 flex flex-col gap-3 min-h-[180px] items-center justify-center">
				<Loader2 className="size-5 animate-spin text-primary" />
				<span className="text-[10px] text-muted-foreground">Loading highlights...</span>
			</div>
		);
	}

	if (!currentItem || items.length === 0) {
		return (
			<div className="bg-popover border border-border/30 rounded-[18px] p-3 flex flex-col gap-3 min-h-[180px]">
				<div className="flex items-center gap-1">
					<Sparkles className="size-[14px] text-primary" />
					<span className="text-[10px] text-primary tracking-[-0.3px] font-medium">
						Memory-derived
					</span>
				</div>
				<div className="flex-1 flex items-center justify-center">
					<p className="text-[11px] text-muted-foreground text-center">
						Add memories to see highlights here
					</p>
				</div>
			</div>
		);
	}

	return (
		<div className="bg-popover border border-border/30 rounded-[18px] p-3 flex flex-col gap-3">
			<div id="highlights-header" className="flex items-start justify-between">
				<div className="flex items-center gap-1">
					<Sparkles className="size-[14px] text-primary" />
					<span className="text-[10px] text-primary tracking-[-0.3px] font-medium">
						Memory-derived
					</span>
				</div>
				<Info className="size-[14px] text-muted-foreground" />
			</div>

			<div id="highlights-body" className="flex flex-col gap-1.5">
				<p className="text-[12px] font-semibold text-foreground leading-tight truncate">
					{currentItem.title}
				</p>
				<div className="text-[12px] text-foreground leading-normal line-clamp-5">
					{renderContent(currentItem.content, currentItem.format)}
				</div>
			</div>

			<div className="flex items-center justify-between w-full gap-2">
				<div id="highlights-actions" className="flex gap-2 items-center">
					{onChat && (
						<button
							type="button"
							onClick={handleChat}
							className={cn(
								"bg-card rounded-[8px] px-2 py-1.5 flex items-center gap-1.5 cursor-pointer relative",
								"shadow-md hover:bg-accent/40 transition-colors",
							)}
							aria-label="Chat with agent"
						>
							<MessageSquare className="size-3.5 text-foreground" />
							<span className="text-[11px] text-foreground">Chat</span>
						</button>
					)}
					{onShowRelated && (
						<button
							type="button"
							onClick={handleShowRelated}
							className={cn(
								"bg-card rounded-[8px] px-2 py-1.5 flex items-center gap-1.5 cursor-pointer relative",
								"shadow-md hover:bg-accent/40 transition-colors",
							)}
							aria-label="Show related"
						>
							<Link2 className="size-3.5 text-foreground" />
							<span className="text-[11px] text-foreground">Related</span>
						</button>
					)}
				</div>

				{items.length > 1 && (
					<div id="highlights-pagination" className="flex items-center gap-2">
						<button
							type="button"
							onClick={handlePrev}
							className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
							aria-label="Previous item"
						>
							<ChevronLeft className="size-4" />
						</button>
						<div className="flex items-center gap-1">
							{items.map((item, idx) => (
								<button
									key={item.id}
									type="button"
									onClick={() => setActiveIndex(idx)}
									className={cn(
										"rounded-full transition-all cursor-pointer",
										idx === activeIndex
											? "w-4 h-1.5 bg-primary"
											: "size-1.5 bg-muted-foreground hover:bg-foreground/70",
									)}
									aria-label={`Go to item ${idx + 1}`}
								/>
							))}
						</div>
						<button
							type="button"
							onClick={handleNext}
							className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
							aria-label="Next item"
						>
							<ChevronRight className="size-4" />
						</button>
					</div>
				)}
			</div>
		</div>
	);
}
