// DELETE /api/files/[id] — bounded-write action (DW18)
// Proxies delete to Go Gateway; writes FileAuditLog entry (requestId, actor, role, target).
// Auth headers forwarded; actorUserId extracted from session if available.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { writeFileAudit } from "@/lib/server/file-audit";
import { getErrorMessage } from "@/lib/utils";

const GATEWAY_BASE = process.env.GATEWAY_URL ?? "http://localhost:9060";

export async function DELETE(
	request: NextRequest,
	{ params }: { params: Promise<{ id: string }> },
) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? undefined;
	const actorRole = request.headers.get("x-actor-role") ?? undefined;

	try {
		const upstream = await fetch(`${GATEWAY_BASE}/api/v1/files/${encodeURIComponent(id)}`, {
			method: "DELETE",
			headers: {
				"x-request-id": requestId,
				...(actorUserId ? { "x-actor-user-id": actorUserId } : {}),
			},
			cache: "no-store",
		});

		if (!upstream.ok) {
			const body = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
			const errorCode = (body.code as string) ?? "DELETE_FAILED";

			await writeFileAudit({
				action: "delete",
				actionClass: "bounded-write",
				requestId,
				target: id,
				actorUserId,
				actorRole,
				status: "failed",
				errorCode,
			});

			return NextResponse.json(
				{ code: errorCode, requestId },
				{ status: upstream.status, headers: { "x-request-id": requestId } },
			);
		}

		await writeFileAudit({
			action: "delete",
			actionClass: "bounded-write",
			requestId,
			target: id,
			actorUserId,
			actorRole,
			status: "ok",
		});

		return new NextResponse(null, {
			status: 204,
			headers: { "x-request-id": requestId },
		});
	} catch (error: unknown) {
		await writeFileAudit({
			action: "delete",
			actionClass: "bounded-write",
			requestId,
			target: id,
			actorUserId,
			actorRole,
			status: "failed",
			errorCode: "STORAGE_UNAVAILABLE",
		});

		return NextResponse.json(
			{ code: "STORAGE_UNAVAILABLE", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}
