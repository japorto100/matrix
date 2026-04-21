"use client";

/**
 * FileCard — reusable file-row with a right-click "Add to Chat" context-menu.
 * Used in FilesOverviewTab's recent-uploads list. Matches the existing
 * row-markup (FileText icon + name + type + status + date) so the tab layout
 * stays visually identical.
 */

import { FileText } from "lucide-react";
import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useGlobalChat } from "@/features/agent/stores/globalChatStore";

interface FileCardProps {
	file: {
		id: string;
		name: string;
		type: string;
		status: string;
		created_at: string;
	};
	renderStatus?: (status: string) => React.ReactNode;
}

export function FileCard({ file, renderStatus }: FileCardProps) {
	const openChat = useGlobalChat((s) => s.openChat);

	return (
		<ContextMenu>
			<ContextMenuTrigger asChild>
				<div
					data-testid="file-card"
					data-file-id={file.id}
					className="flex items-center justify-between gap-2 py-1.5"
				>
					<div className="flex min-w-0 items-center gap-2">
						<FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
						<span className="truncate font-medium text-xs">{file.name}</span>
						<span className="shrink-0 font-mono text-[10px] text-muted-foreground uppercase">
							{file.type}
						</span>
					</div>
					<div className="flex shrink-0 items-center gap-2">
						{renderStatus?.(file.status)}
						<span className="shrink-0 font-mono text-[10px] text-muted-foreground/60">
							{new Date(file.created_at).toLocaleDateString()}
						</span>
					</div>
				</div>
			</ContextMenuTrigger>
			<ContextMenuContent>
				<ContextMenuItem onClick={() => openChat(`file-context:${file.id}:${file.name}`)}>
					Add to Chat
				</ContextMenuItem>
			</ContextMenuContent>
		</ContextMenu>
	);
}
