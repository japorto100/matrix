import type { ControlAction, ControlActionClass } from "@/features/control/lib/action-classes";
import { getGatewayBaseURL } from "@/lib/server/gateway";

interface WriteControlAuditOptions {
	action: ControlAction;
	actionClass: ControlActionClass;
	requestId: string;
	target: string;
	actorUserId?: string;
	actorRole?: string;
	status?: "ok" | "failed";
	errorCode?: string;
	expiresAt?: Date;
}

export async function writeControlAudit(opts: WriteControlAuditOptions): Promise<void> {
	try {
		await fetch(new URL("/api/v1/control/audit", getGatewayBaseURL()), {
			method: "POST",
			cache: "no-store",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
			},
			body: JSON.stringify({
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
		console.error("[control-audit] Failed to write audit log", {
			action: opts.action,
			target: opts.target,
			requestId: opts.requestId,
		});
	}
}
