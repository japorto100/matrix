"use client";

// AC17 — visual badge that marks an action's class on buttons/labels.
// Always render this next to mutating action buttons so the class is visible.

import type { ControlActionClass } from "../lib/action-classes";

interface ControlActionBadgeProps {
	actionClass: ControlActionClass;
}

const BADGE_STYLES: Record<ControlActionClass, string> = {
	"read-only": "bg-muted text-muted-foreground",
	"bounded-write": "bg-amber-500/20 text-amber-400",
	"approval-write": "bg-orange-500/20 text-orange-400",
	forbidden: "bg-red-500/20 text-red-500",
};

const BADGE_LABELS: Record<ControlActionClass, string> = {
	"read-only": "read",
	"bounded-write": "write",
	"approval-write": "approval",
	forbidden: "forbidden",
};

export function ControlActionBadge({ actionClass }: ControlActionBadgeProps) {
	return (
		<span
			className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${BADGE_STYLES[actionClass]}`}
		>
			{BADGE_LABELS[actionClass]}
		</span>
	);
}
