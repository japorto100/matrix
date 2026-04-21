// DW17 — File action-class classification
// Conforms to AGENT_SECURITY.md action-class schema.

export type ActionClass = "read-only" | "bounded-write" | "approval-write" | "forbidden";

export type FileAction = "upload" | "delete" | "reindex" | "download";

// Action → class mapping (authoritative for UI + BFF)
export const FILE_ACTION_CLASSES: Record<FileAction, ActionClass> = {
	download: "read-only",
	upload: "bounded-write",
	delete: "bounded-write",
	reindex: "approval-write",
} as const;

// Audit log fields required for each action class
export interface FileAuditPayload {
	action: FileAction;
	actionClass: ActionClass;
	requestId: string;
	target: string; // storageKey or fileId
	actorUserId?: string;
	actorRole?: string;
}

export function getActionClass(action: FileAction): ActionClass {
	return FILE_ACTION_CLASSES[action];
}

// Returns true when the action requires an explicit approval confirm step
export function requiresApproval(action: FileAction): boolean {
	return FILE_ACTION_CLASSES[action] === "approval-write";
}
