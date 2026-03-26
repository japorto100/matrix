"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { Loader2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
// ScrollArea bewusst nicht verwendet: useVirtualizer braucht direkten DOM-ref
// auf dem Scroll-Container — Radix ScrollArea bricht die Scroll-Erkennung
import type { ResolvedMessage } from "@/lib/matrix/types";
import { Message } from "./Message";

interface Props {
	messages: ResolvedMessage[];
	isLoading: boolean;
	canLoadMore: boolean;
	onLoadMore: () => Promise<void>;
	onReact?: (eventId: string, emoji: string) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
	client?: MatrixClient | null;
	roomId?: string | null;
	onThreadOpen?: (eventId: string) => void;
}

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

	const virtualizer = useVirtualizer({
		count: messages.length,
		getScrollElement: () => parentRef.current,
		estimateSize: () => 72,
		overscan: 10,
	});

	// Auto-scroll ans Ende bei neuen Nachrichten
	useEffect(() => {
		if (messages.length > lastLengthRef.current) {
			bottomRef.current?.scrollIntoView({ behavior: "smooth" });
		}
		lastLengthRef.current = messages.length;
	}, [messages.length]);

	const items = virtualizer.getVirtualItems();

	return (
		<div className="flex-1 flex flex-col overflow-hidden">
			{/* Ältere laden */}
			{canLoadMore && (
				<div className="flex justify-center py-2 border-b">
					<Button
						variant="ghost"
						size="sm"
						onClick={onLoadMore}
						disabled={isLoading}
						className="text-xs"
					>
						{isLoading ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : null}
						Ältere Nachrichten laden
					</Button>
				</div>
			)}

			{/* Virtualisierte Liste */}
			<div ref={parentRef} className="flex-1 overflow-y-auto">
				<div
					style={{
						height: `${virtualizer.getTotalSize()}px`,
						width: "100%",
						position: "relative",
					}}
				>
					{items.map((virtualItem) => {
						const msg = messages[virtualItem.index];
						if (!msg) return null;
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
									message={msg}
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
				<div ref={bottomRef} />
			</div>
		</div>
	);
}
