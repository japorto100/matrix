"use client";

// DW6 tab wrapper — documents tab
// Dynamic import: PDF viewer uses browser APIs (no SSR)

import { Loader2 } from "lucide-react";
import dynamic from "next/dynamic";

const DocumentViewer = dynamic(
	() => import("./DocumentViewer").then((m) => ({ default: m.DocumentViewer })),
	{
		ssr: false,
		loading: () => (
			<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
				<Loader2 className="h-4 w-4 animate-spin" />
				<span className="text-sm">Loading viewer…</span>
			</div>
		),
	},
);

export function FilesDocumentsTab() {
	return (
		<div className="flex flex-1 min-h-0 overflow-hidden">
			<DocumentViewer />
		</div>
	);
}
