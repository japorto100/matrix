"use client";

// AC94: Context-Chip — zeigt injizierten Kontext als dismissible Badge
// AC77: close button via useGlobalChat

import { ExternalLink, Settings, X } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useGlobalChat } from "@/features/agent-chat/context/GlobalChatContext";

export function AgentChatHeader() {
	const { chatContext, clearChatContext, closeChat } = useGlobalChat();

	return (
		<div className="flex flex-col border-b border-border shrink-0">
			<div className="flex items-center justify-between px-3 py-2">
				<span className="text-xs font-semibold text-foreground">Agent Chat</span>
				<div className="flex items-center gap-1">
					<Link href="/control" tabIndex={-1}>
						<Button
							variant="ghost"
							size="sm"
							className="h-7 gap-1 px-2 text-[10px] text-muted-foreground hover:text-foreground"
							title="Open Control surface (AC.V10)"
						>
							<ExternalLink className="h-3 w-3" />
							Control
						</Button>
					</Link>
					<Link href="/control/security" tabIndex={-1}>
						<Button
							variant="ghost"
							size="icon"
							className="h-7 w-7 text-muted-foreground hover:text-foreground"
							title="Security / agent settings"
						>
							<Settings className="h-3.5 w-3.5" />
						</Button>
					</Link>
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7 text-muted-foreground hover:text-foreground"
						onClick={closeChat}
						title="Close chat (⌘L)"
					>
						<X className="h-3.5 w-3.5" />
					</Button>
				</div>
			</div>

			{/* AC94: Context chip */}
			{chatContext && (
				<div className="flex items-center gap-1.5 px-3 pb-2">
					<Badge
						variant="outline"
						className="h-5 gap-1 text-[10px] font-mono bg-emerald-500/5 border-emerald-500/30 text-emerald-400 max-w-full truncate pr-1"
					>
						<span className="truncate">{chatContext}</span>
						<button
							type="button"
							onClick={clearChatContext}
							className="ml-0.5 hover:text-foreground transition-colors shrink-0"
							aria-label="Clear context"
						>
							<X className="h-2.5 w-2.5" />
						</button>
					</Badge>
				</div>
			)}
		</div>
	);
}
