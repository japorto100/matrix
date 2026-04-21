import type { FileAuditPayload } from "@/features/files/lib/action-classes";
import { getGatewayBaseURL } from "@/lib/server/gateway";

interface WriteAuditOptions extends FileAuditPayload {
	documentId?: string;
	status?: "ok" | "failed";
	errorCode?: string;
	expiresAt?: Date;
}

export async function writeFileAudit(opts: WriteAuditOptions): Promise<void> {
	try {
		await fetch(new URL("/api/v1/files/audit", getGatewayBaseURL()), {
			method: "POST",
			cache: "no-store",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
			},
			body: JSON.stringify({
				documentId: opts.documentId ?? null,
				action: opts.action,
				actionClass: opts.actionClass,
				actorUserId: opts.actorUserId ?? null,
				actorRole: opts.actorRole ?? null,
				requestId: opts.requestId,
				target: opts.target,
				status: opts.status ?? "ok",
				errorCode: opts.errorCode ?? null,
				expiresAt: opts.expiresAt?.toISOString() ?? null,
			}),
		});
	} catch {
		console.error("[file-audit] Failed to write audit log", {
			action: opts.action,
			target: opts.target,
			requestId: opts.requestId,
		});
	}
}
