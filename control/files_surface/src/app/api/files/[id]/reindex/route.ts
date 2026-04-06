// POST /api/files/[id]/reindex — approval-write action (DW19)
// Requires client to have passed the confirm step (checked via x-confirm-token header).
// Writes FileAuditLog with expiresAt so the nonce window is traceable.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { writeFileAudit } from "@/lib/server/file-audit";
import { getErrorMessage } from "@/lib/utils";

const GATEWAY_BASE = process.env.GATEWAY_URL ?? "http://localhost:9060";
// Approval nonce TTL: client must confirm within 30s
const NONCE_TTL_MS = 30_000;

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? undefined;
	const actorRole = request.headers.get("x-actor-role") ?? undefined;
	const confirmToken = request.headers.get("x-confirm-token");

	// Approval gate: confirm token required
	if (!confirmToken) {
		return NextResponse.json(
			{ code: "APPROVAL_REQUIRED", message: "x-confirm-token header missing", requestId },
			{ status: 403, headers: { "x-request-id": requestId } },
		);
	}

	const expiresAt = new Date(Date.now() + NONCE_TTL_MS);

	try {
		const upstream = await fetch(`${GATEWAY_BASE}/api/v1/files/${encodeURIComponent(id)}/reindex`, {
			method: "POST",
			headers: {
				"x-request-id": requestId,
				"x-confirm-token": confirmToken,
				...(actorUserId ? { "x-actor-user-id": actorUserId } : {}),
			},
			cache: "no-store",
		});

		if (!upstream.ok) {
			const body = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
			const errorCode = (body.code as string) ?? "REINDEX_FAILED";

			await writeFileAudit({
				action: "reindex",
				actionClass: "approval-write",
				requestId,
				target: id,
				actorUserId,
				actorRole,
				status: "failed",
				errorCode,
				expiresAt,
			});

			return NextResponse.json(
				{ code: errorCode, requestId },
				{ status: upstream.status, headers: { "x-request-id": requestId } },
			);
		}

		await writeFileAudit({
			action: "reindex",
			actionClass: "approval-write",
			requestId,
			target: id,
			actorUserId,
			actorRole,
			status: "ok",
			expiresAt,
		});

		const data: unknown = await upstream.json().catch(() => ({ queued: true }));
		return NextResponse.json(data, {
			status: 202,
			headers: {
				"cache-control": "no-store",
				"x-request-id": requestId,
			},
		});
	} catch (error: unknown) {
		await writeFileAudit({
			action: "reindex",
			actionClass: "approval-write",
			requestId,
			target: id,
			actorUserId,
			actorRole,
			status: "failed",
			errorCode: "GATEWAY_UNAVAILABLE",
			expiresAt,
		});

		return NextResponse.json(
			{ code: "GATEWAY_UNAVAILABLE", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}
