"use client";

// AC16 + AC19 — wraps action UI with role enforcement.
// - forbidden: renders nothing (hard-block, AC19)
// - not allowed for role: renders locked/disabled tooltip state
// - allowed: renders children

import { Lock } from "lucide-react";
import type { ReactNode } from "react";
import { useControlRole } from "../hooks/useControlRole";
import type { ControlAction } from "../lib/action-classes";
import { getControlActionClass, isAllowed } from "../lib/action-classes";
import { ControlActionBadge } from "./ControlActionBadge";

interface ControlActionGuardProps {
	action: ControlAction;
	children: ReactNode;
	// If true, shows a locked placeholder instead of hiding entirely when forbidden/role-denied
	showLocked?: boolean;
}

export function ControlActionGuard({
	action,
	children,
	showLocked = false,
}: ControlActionGuardProps) {
	const role = useControlRole();
	const cls = getControlActionClass(action);

	// AC19: forbidden actions are always blocked — render nothing (or locked placeholder)
	if (cls === "forbidden") {
		if (!showLocked) return null;
		return (
			<span className="inline-flex items-center gap-1 opacity-40 cursor-not-allowed select-none">
				<Lock className="h-3 w-3" />
				<ControlActionBadge actionClass="forbidden" />
			</span>
		);
	}

	// AC16: role below minimum — show locked state
	if (!isAllowed(action, role)) {
		if (!showLocked) return null;
		return (
			<span
				className="inline-flex items-center gap-1 opacity-40 cursor-not-allowed select-none"
				title={`Requires ${cls === "approval-write" ? "admin" : "trader"} role`}
			>
				<Lock className="h-3 w-3 text-muted-foreground" />
				<ControlActionBadge actionClass={cls} />
			</span>
		);
	}

	return <>{children}</>;
}
