"use client";

// Placeholder tab shown for features not yet implemented.
// Renders a visible degradation message (DW4 / DW.V8).

import { Construction } from "lucide-react";

interface FilesPlaceholderTabProps {
	label: string;
	planned?: string;
}

export function FilesPlaceholderTab({ label, planned }: FilesPlaceholderTabProps) {
	return (
		<div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
			<Construction className="h-8 w-8 text-muted-foreground/40" />
			<p className="text-sm font-medium text-muted-foreground">{label}</p>
			{planned && <p className="text-xs text-muted-foreground/60 font-mono">{planned}</p>}
		</div>
	);
}
