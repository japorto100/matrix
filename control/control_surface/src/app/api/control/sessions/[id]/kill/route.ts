// POST /api/control/sessions/[id]/kill — approval-write (AC18)
// x-confirm-token required (403 without); proxies to Go Gateway.
// Writes ControlAuditLog on every outcome (AC20).

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { CONTROL_ACTION_CLASSES } from "@/features/control/lib/action-classes";
import { writeControlAudit } from "@/lib/server/control-audit";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id")?.trim() ?? randomUUID();
	const confirmToken = request.headers.get("x-confirm-token");
	const actorUserId = request.headers.get("x-actor-user-id")?.trim() ?? undefined;
	const userRole = request.headers.get("x-user-role")?.trim() ?? undefined;

	// Approval gate — AC18
	if (!confirmToken) {
		return NextResponse.json(
			{ code: "APPROVAL_REQUIRED", message: "x-confirm-token header missing", requestId },
			{ status: 403, headers: { "X-Request-ID": requestId } },
		);
	}

	// 30s nonce window for approval-write
	const expiresAt = new Date(Date.now() + 30_000);

	try {
		const res = await fetch(
			`${getGatewayBaseURL()}/api/v1/control/sessions/${encodeURIComponent(id)}/kill`,
			{
				method: "POST",
				headers: {
					"X-Request-ID": requestId,
					"X-Confirm-Token": confirmToken,
					...(userRole ? { "X-User-Role": userRole } : {}),
				},
				cache: "no-store",
				signal: AbortSignal.timeout(5000),
			},
		);

		if (!res.ok) {
			const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
			const errorCode = (body.code as string) ?? "KILL_FAILED";

			void writeControlAudit({
				action: "kill-session",
				actionClass: CONTROL_ACTION_CLASSES["kill-session"],
				requestId,
				target: id,
				actorUserId,
				actorRole: userRole,
				status: "failed",
				errorCode,
				expiresAt,
			});

			return NextResponse.json(
				{ code: errorCode, requestId },
				{ status: res.status, headers: { "X-Request-ID": requestId } },
			);
		}

		void writeControlAudit({
			action: "kill-session",
			actionClass: CONTROL_ACTION_CLASSES["kill-session"],
			requestId,
			target: id,
			actorUserId,
			actorRole: userRole,
			status: "ok",
			expiresAt,
		});

		return new NextResponse(null, { status: 204, headers: { "X-Request-ID": requestId } });
	} catch (err) {
		void writeControlAudit({
			action: "kill-session",
			actionClass: CONTROL_ACTION_CLASSES["kill-session"],
			requestId,
			target: id,
			actorUserId,
			actorRole: userRole,
			status: "failed",
			errorCode: "GATEWAY_UNAVAILABLE",
			expiresAt,
		});

		return NextResponse.json(
			{ code: "GATEWAY_UNAVAILABLE", message: getErrorMessage(err), requestId },
			{ status: 503, headers: { "X-Request-ID": requestId } },
		);
	}
}
