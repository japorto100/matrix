"use client";

import type { SuggestionProps } from "@tiptap/suggestion";
import { Hash, Megaphone } from "lucide-react";
import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { cn } from "@/lib/utils";

export interface MentionItem {
	id: string;
	label: string;
	avatarUrl?: string;
	/** User ist ein Agent (@agent-*) */
	isAgent?: boolean;
	/** @room — benachrichtigt alle (MSC3952) */
	isRoom?: boolean;
	/** #room Pill — Link zu anderem Raum */
	isRoomPill?: boolean;
}

export interface MentionListRef {
	onKeyDown: (props: { event: KeyboardEvent }) => boolean;
}

/**
 * Mention-Dropdown für Tiptap.
 * Zeigt User/Agent/@room bei @-Trigger, Räume bei #-Trigger.
 */
export const MentionList = forwardRef<MentionListRef, SuggestionProps<MentionItem>>(
	(props, ref) => {
		const [selectedIndex, setSelectedIndex] = useState(0);

		// biome-ignore lint/correctness/useExhaustiveDependencies: props.items als Trigger — Reset bei neuen Vorschlägen
		useEffect(() => {
			setSelectedIndex(0);
		}, [props.items]);

		useImperativeHandle(ref, () => ({
			onKeyDown: ({ event }) => {
				if (event.key === "ArrowUp") {
					setSelectedIndex((i) => (i + props.items.length - 1) % props.items.length);
					return true;
				}
				if (event.key === "ArrowDown") {
					setSelectedIndex((i) => (i + 1) % props.items.length);
					return true;
				}
				if (event.key === "Enter" || event.key === "Tab") {
					const item = props.items[selectedIndex];
					if (item) props.command(item);
					return true;
				}
				return false;
			},
		}));

		if (!props.items.length) {
			return (
				<div className="rounded-lg border bg-popover p-2 text-xs text-muted-foreground shadow-md">
					Keine Ergebnisse
				</div>
			);
		}

		return (
			<div className="rounded-lg border bg-popover shadow-md overflow-hidden max-h-48 overflow-y-auto min-w-[200px]">
				{props.items.map((item, index) => (
					<button
						type="button"
						key={item.id}
						className={cn(
							"flex items-center gap-2 w-full px-3 py-1.5 text-sm text-left transition-colors",
							index === selectedIndex ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
						)}
						onClick={() => props.command(item)}
					>
						<MentionItemIcon item={item} />
						<span className="truncate">{item.label}</span>
						<MentionItemBadge item={item} />
					</button>
				))}
			</div>
		);
	},
);

MentionList.displayName = "MentionList";

// ─── Sub-Components ─────────────────────────────────────────────────────────

function MentionItemIcon({ item }: { item: MentionItem }) {
	// @room
	if (item.isRoom) {
		return (
			<div className="h-5 w-5 rounded-full flex items-center justify-center bg-amber-500/20 text-amber-500 shrink-0">
				<Megaphone className="h-3 w-3" />
			</div>
		);
	}
	// #room pill
	if (item.isRoomPill) {
		return (
			<div className="h-5 w-5 rounded-full flex items-center justify-center bg-blue-500/20 text-blue-500 shrink-0">
				<Hash className="h-3 w-3" />
			</div>
		);
	}
	// User mit Avatar
	if (item.avatarUrl) {
		return (
			// biome-ignore lint/performance/noImgElement: Avatar from mxc URL
			<img src={item.avatarUrl} alt="" className="h-5 w-5 rounded-full object-cover shrink-0" />
		);
	}
	// Agent ohne Avatar
	if (item.isAgent) {
		return (
			<div className="h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-medium shrink-0 bg-primary/20 text-primary">
				AI
			</div>
		);
	}
	// User ohne Avatar
	return (
		<div className="h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-medium shrink-0 bg-violet-600 text-white">
			{item.label.charAt(0).toUpperCase()}
		</div>
	);
}

function MentionItemBadge({ item }: { item: MentionItem }) {
	if (item.isRoom) {
		return (
			<span className="ml-auto text-[10px] px-1 py-0 rounded bg-amber-500/10 text-amber-500 shrink-0">
				Alle benachrichtigen
			</span>
		);
	}
	if (item.isAgent) {
		return (
			<span className="ml-auto text-[10px] px-1 py-0 rounded bg-primary/10 text-primary shrink-0">
				Agent
			</span>
		);
	}
	if (item.isRoomPill) {
		return (
			<span className="ml-auto text-[10px] px-1 py-0 rounded bg-blue-500/10 text-blue-500 shrink-0">
				Raum
			</span>
		);
	}
	return null;
}
