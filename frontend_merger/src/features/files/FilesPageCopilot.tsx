"use client";

/**
 * FilesPageCopilot — CopilotKit action/readable registration for the /files
 * surface. Env-gated so the CopilotKit hooks only fire when the runtime is
 * mounted (same pattern as GlobalCopilotContext).
 *
 * Exposes:
 *   - readable "recent-files" → up to 10 most recent files
 *   - action "saveAttachmentToStorage" → persists a chat attachment to blob
 *     storage via /api/files/save-attachment (stub 501 until go-appservice
 *     implements the route)
 */

import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { useQuery } from "@tanstack/react-query";

interface FileRecord {
	id: string;
	name: string;
	type: string;
	status: string;
	created_at: string;
}

interface FilesListResponse {
	recent_uploads: FileRecord[];
}

function FilesCopilotInner() {
	const filesQuery = useQuery<FilesListResponse, Error>({
		queryKey: ["files-list"],
		queryFn: async () => {
			const res = await fetch("/api/files", { cache: "no-store" });
			if (!res.ok) throw new Error("STORAGE_UNAVAILABLE");
			return res.json() as Promise<FilesListResponse>;
		},
		staleTime: 30_000,
	});

	const recentFiles = (filesQuery.data?.recent_uploads ?? []).slice(0, 10).map((f) => ({
		id: f.id,
		name: f.name,
		type: f.type,
		status: f.status,
		createdAt: f.created_at,
	}));

	useCopilotReadable({
		description: "Up to 10 most recent files in the user's storage",
		value: recentFiles,
	});

	useCopilotAction({
		name: "saveAttachmentToStorage",
		description:
			"Persist a chat-attached file from chat-state to blob storage so it shows up in /files",
		parameters: [
			{
				name: "attachmentId",
				type: "string",
				description: "The attachment id from the current chat session",
				required: true,
			},
		],
		handler: async ({ attachmentId }: { attachmentId: string }) => {
			const res = await fetch("/api/files/save-attachment", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ attachmentId }),
			});
			if (!res.ok) {
				const text = await res.text();
				return { saved: false, error: text };
			}
			const file = (await res.json()) as { id: string; name: string };
			void filesQuery.refetch();
			return { saved: true, fileId: file.id, name: file.name };
		},
	});

	return null;
}

export function FilesPageCopilot() {
	const enabled = process.env.NEXT_PUBLIC_COPILOTKIT_ENABLED === "true";
	if (!enabled) return null;
	return <FilesCopilotInner />;
}
