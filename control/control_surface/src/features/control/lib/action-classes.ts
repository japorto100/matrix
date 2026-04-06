// AC15 — Control action-class classification
// Conforms to AGENT_SECURITY.md action-class schema.

export type ControlActionClass = "read-only" | "bounded-write" | "approval-write" | "forbidden";

export type ControlAction =
	| "view"
	| "pause-session"
	| "resume-session"
	| "kill-session"
	| "purge-memory"
	| "reset-kg"
	| "disable-skill"
	| "enable-skill"
	| "run-eval"
	| "direct-code-exec"
	| "raw-db-access";

export const CONTROL_ACTION_CLASSES: Record<ControlAction, ControlActionClass> = {
	view: "read-only",
	"pause-session": "bounded-write",
	"resume-session": "bounded-write",
	"disable-skill": "bounded-write",
	"enable-skill": "bounded-write",
	"run-eval": "bounded-write",
	"kill-session": "approval-write",
	"purge-memory": "approval-write",
	"reset-kg": "approval-write",
	"direct-code-exec": "forbidden",
	"raw-db-access": "forbidden",
} as const;

// Minimum role required per action class (AC16)
export const ACTION_CLASS_MIN_ROLE: Record<ControlActionClass, string> = {
	"read-only": "viewer",
	"bounded-write": "trader",
	"approval-write": "admin",
	forbidden: "superadmin", // effectively unreachable
} as const;

export function getControlActionClass(action: ControlAction): ControlActionClass {
	return CONTROL_ACTION_CLASSES[action];
}

export function isAllowed(action: ControlAction, userRole: string): boolean {
	const cls = getControlActionClass(action);
	const minRole = ACTION_CLASS_MIN_ROLE[cls];
	const ROLE_ORDER = ["viewer", "trader", "admin", "superadmin"];
	return ROLE_ORDER.indexOf(userRole) >= ROLE_ORDER.indexOf(minRole);
}
