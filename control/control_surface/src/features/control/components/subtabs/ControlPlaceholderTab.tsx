"use client";

// Placeholder tab — shown for subtabs not yet implemented in Phase 22b.

interface ControlPlaceholderTabProps {
	label: string;
	planned?: string;
}

export function ControlPlaceholderTab({ label, planned }: ControlPlaceholderTabProps) {
	return (
		<div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center text-muted-foreground">
			<span className="text-sm font-semibold">{label}</span>
			{planned && <span className="text-xs opacity-60">{planned}</span>}
		</div>
	);
}
