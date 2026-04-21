"use client";

/**
 * assistant-ui Evaluation — Paralleler Thread neben unserem Eigenbau.
 *
 * Nutzt @assistant-ui/react Primitives mit ai SDK v6 Adapter.
 * Zum Vergleichen: beide Threads zeigen die gleichen Messages,
 * aber assistant-ui liefert Accessibility, Keyboard Support, Streaming gratis.
 *
 * Aktivierung: Feature Flag oder Toggle in der UI.
 * Entscheidung nach Vergleich: migrieren oder eigenen Code behalten.
 */

import type { useChat } from "@ai-sdk/react";
import {
	ActionBarPrimitive,
	AssistantRuntimeProvider,
	BranchPickerPrimitive,
	ComposerPrimitive,
	MessagePrimitive,
	ThreadPrimitive,
} from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";

interface Props {
	/** useChat Return aus useChatSession (ai SDK v6) */
	chat: ReturnType<typeof useChat>;
}

/**
 * assistant-ui Thread — drop-in Vergleich zu AgentChatThread.
 * Unstyled Primitives — Styling kommt über className Props (Tailwind).
 */
export function AssistantUIThread({ chat }: Props) {
	const runtime = useChatRuntime(chat);

	return (
		<AssistantRuntimeProvider runtime={runtime}>
			<div className="flex flex-col h-full">
				{/* Message List */}
				<ThreadPrimitive.Viewport className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
					<ThreadPrimitive.Messages
						components={{
							UserMessage: () => (
								<MessagePrimitive.Root className="flex justify-end">
									<div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-3 py-2 text-sm">
										<MessagePrimitive.Content />
									</div>
								</MessagePrimitive.Root>
							),
							AssistantMessage: () => (
								<MessagePrimitive.Root className="flex justify-start">
									<div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-muted px-3 py-2 text-sm">
										<MessagePrimitive.Content />
										<ActionBarPrimitive.Root className="flex gap-1 mt-1">
											<ActionBarPrimitive.Copy className="text-[10px] text-muted-foreground hover:text-foreground">
												Copy
											</ActionBarPrimitive.Copy>
											<ActionBarPrimitive.Reload className="text-[10px] text-muted-foreground hover:text-foreground">
												Retry
											</ActionBarPrimitive.Reload>
										</ActionBarPrimitive.Root>
										<BranchPickerPrimitive.Root className="flex gap-1 mt-1">
											<BranchPickerPrimitive.Previous className="text-[10px]">
												←
											</BranchPickerPrimitive.Previous>
											<BranchPickerPrimitive.Count />
											<BranchPickerPrimitive.Next className="text-[10px]">
												→
											</BranchPickerPrimitive.Next>
										</BranchPickerPrimitive.Root>
									</div>
								</MessagePrimitive.Root>
							),
						}}
					/>
				</ThreadPrimitive.Viewport>

				{/* Composer */}
				<div className="border-t border-border/40 p-3">
					<ComposerPrimitive.Root className="flex gap-2">
						<ComposerPrimitive.Input
							className="flex-1 rounded-xl bg-muted/30 border border-border/50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
							placeholder="Nachricht schreiben..."
						/>
						<ComposerPrimitive.Send className="rounded-full bg-primary text-primary-foreground h-10 w-10 flex items-center justify-center">
							↑
						</ComposerPrimitive.Send>
					</ComposerPrimitive.Root>
				</div>
			</div>
		</AssistantRuntimeProvider>
	);
}
