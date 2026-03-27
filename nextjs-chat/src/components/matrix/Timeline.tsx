"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { format, isToday, isYesterday } from "date-fns";
import { de } from "date-fns/locale";
import { ChevronDown, Loader2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { Message } from "./Message";

interface Props {
	messages: ResolvedMessage[];
	isLoading: boolean;
	canLoadMore: boolean;
	onLoadMore: () => Promise<void>;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
	client?: MatrixClient | null;
	roomId?: string | null;
	onThreadOpen?: (eventId: string) => void;
}

// Datum-Label für Separator
function dateLabel(ts: number): string {
	const d = new Date(ts);
	if (isToday(d)) return "Heute";
	if (isYesterday(d)) return "Gestern";
	return format(d, "EEEE, d. MMMM yyyy", { locale: de });
}

function dateKey(ts: number): string {
	return new Date(ts).toDateString();
}

type TimelineItem =
	| { type: "date-separator"; key: string; label: string }
	| { type: "message"; key: string; msg: ResolvedMessage; isGrouped: boolean };

export function Timeline({
	messages,
	isLoading,
	canLoadMore,
	onLoadMore,
	onReact,
	onReply,
	onEdit,
	onRedact,
	onForward,
	client,
	roomId,
	onThreadOpen,
}: Props) {
	const parentRef = useRef<HTMLDivElement>(null);
	const bottomRef = useRef<HTMLDivElement>(null);
	const lastLengthRef = useRef(messages.length);

	// Build items with date separators and grouping
	const items: TimelineItem[] = useMemo(() => {
		const result: TimelineItem[] = [];
		let lastDate = "";
		let lastSender = "";

		for (const msg of messages) {
			const dk = dateKey(msg.timestamp);
			if (dk !== lastDate) {
				result.push({ type: "date-separator", key: `date-${dk}`, label: dateLabel(msg.timestamp) });
				lastDate = dk;
				lastSender = "";
			}

			// Gruppierung: gleicher Sender innerhalb 2 Minuten → kein Avatar/Name
			const prevItem = result.length > 0 ? result[result.length - 1] : undefined;
			const isGrouped =
				msg.sender === lastSender &&
				prevItem?.type === "message" &&
				msg.timestamp - prevItem.msg.timestamp < 120_000;

			result.push({ type: "message", key: msg.eventId, msg, isGrouped });
			lastSender = msg.sender;
		}
		return result;
	}, [messages]);

	const virtualizer = useVirtualizer({
		count: items.length,
		getScrollElement: () => parentRef.current,
		estimateSize: (index) => (items[index]?.type === "date-separator" ? 40 : 64),
		overscan: 10,
	});

	// Scroll-Position tracken für FAB
	const [showScrollFab, setShowScrollFab] = useState(false);
	const handleScroll = useCallback(() => {
		const el = parentRef.current;
		if (!el) return;
		const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
		setShowScrollFab(distFromBottom > 200);
	}, []);

	const scrollToBottom = useCallback(() => {
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, []);

	// Raumwechsel → nach unten scrollen (mehrfach weil Medien async laden)
	useEffect(() => {
		lastLengthRef.current = 0;
		const scroll = () => {
			bottomRef.current?.scrollIntoView({ behavior: "instant" });
			setShowScrollFab(false);
		};
		setTimeout(scroll, 50);
		setTimeout(scroll, 300);
		setTimeout(scroll, 800);
	}, [roomId]);

	// Auto-scroll bei neuen Nachrichten
	useEffect(() => {
		if (messages.length > lastLengthRef.current) {
			setTimeout(() => {
				bottomRef.current?.scrollIntoView({ behavior: "smooth" });
				setShowScrollFab(false);
			}, 50);
		}
		lastLengthRef.current = messages.length;
	}, [messages.length]);

	const virtualItems = virtualizer.getVirtualItems();

	return (
		<div className="flex-1 flex flex-col overflow-hidden relative">
			{/* Ältere laden */}
			{canLoadMore && (
				<div className="flex justify-center py-3">
					<button
						type="button"
						onClick={onLoadMore}
						disabled={isLoading}
						className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50"
					>
						{isLoading && <Loader2 className="h-3 w-3 animate-spin" />}
						{isLoading ? "Laden..." : "Ältere Nachrichten"}
					</button>
				</div>
			)}

			{/* Virtualisierte Liste */}
			<div
				ref={parentRef}
				className="flex-1 overflow-y-auto scrollbar-hide"
				onScroll={handleScroll}
			>
				<div
					style={{
						height: `${virtualizer.getTotalSize()}px`,
						width: "100%",
						position: "relative",
					}}
				>
					{virtualItems.map((virtualItem) => {
						const item = items[virtualItem.index];
						if (!item) return null;

						if (item.type === "date-separator") {
							return (
								<div
									key={virtualItem.key}
									data-index={virtualItem.index}
									ref={virtualizer.measureElement}
									style={{
										position: "absolute",
										top: 0,
										left: 0,
										width: "100%",
										transform: `translateY(${virtualItem.start}px)`,
									}}
								>
									<div className="flex items-center justify-center py-3">
										<span className="px-3 py-0.5 text-[11px] font-medium text-muted-foreground bg-muted/50 rounded-full">
											{item.label}
										</span>
									</div>
								</div>
							);
						}

						return (
							<div
								key={virtualItem.key}
								data-index={virtualItem.index}
								ref={virtualizer.measureElement}
								style={{
									position: "absolute",
									top: 0,
									left: 0,
									width: "100%",
									transform: `translateY(${virtualItem.start}px)`,
								}}
							>
								<Message
									message={item.msg}
									isGrouped={item.isGrouped}
									onReact={onReact}
									onReply={onReply}
									onEdit={onEdit}
									onRedact={onRedact}
									onForward={onForward}
									client={client}
									roomId={roomId}
									onThreadOpen={onThreadOpen}
								/>
							</div>
						);
					})}
				</div>
				<div ref={bottomRef} className="h-4" />
			</div>

			{/* Scroll-to-bottom FAB */}
			{showScrollFab && (
				<button
					type="button"
					onClick={scrollToBottom}
					className="absolute bottom-4 left-1/2 -translate-x-1/2 h-9 w-9 rounded-full bg-card border border-border/50 shadow-lg flex items-center justify-center hover:bg-accent transition-colors z-10"
					title="Nach unten scrollen"
				>
					<ChevronDown className="h-4 w-4" />
				</button>
			)}
		</div>
	);
}
