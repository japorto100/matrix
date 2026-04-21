"use client";

import { X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { Button } from "@/components/ui/button";
import { useThreadTimeline } from "@/lib/matrix/hooks/useThreadTimeline";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { MessageComposer } from "../MessageComposer";
import { Timeline } from "../Timeline";

interface Props {
	client: MatrixClient;
	roomId: string;
	threadRootId: string;
	threadRootMessage: ResolvedMessage | null;
	onClose: () => void;
}

export function ThreadPanel({ client, roomId, threadRootId, threadRootMessage, onClose }: Props) {
	const { messages, isLoading, canLoadMore, loadMore } = useThreadTimeline(
		client,
		roomId,
		threadRootId,
	);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border/50 bg-background overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
				<div className="flex flex-col min-w-0">
					<span className="text-sm font-semibold">Thread</span>
					{threadRootMessage && (
						<span className="text-xs text-muted-foreground truncate mt-0.5">
							{threadRootMessage.senderDisplayName}: {threadRootMessage.body}
						</span>
					)}
				</div>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			{/* Thread Timeline */}
			<Timeline
				messages={messages}
				isLoading={isLoading}
				canLoadMore={canLoadMore}
				onLoadMore={loadMore}
			/>

			{/* Composer im Thread-Kontext */}
			<MessageComposer client={client} roomId={roomId} threadId={threadRootId} />
		</div>
	);
}
