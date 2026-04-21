// GET /api/files/[id] — single file detail
// DELETE /api/files/[id] — bounded-write action (DW18)
// Proxies to Go Gateway; writes FileAuditLog for DELETE.
// exec-19 Stufe 3: proxy.ts injects X-Actor-User-Id.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { writeFileAudit } from "@/lib/server/file-audit";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";

	try {
		const upstream = await fetch(`${getGatewayBaseURL()}/api/v1/files/${encodeURIComponent(id)}`, {
			headers: {
				"x-request-id": requestId,
				"x-actor-user-id": actorUserId,
				accept: "application/json",
			},
			cache: "no-store",
		});

		if (!upstream.ok) {
			const body = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
			return NextResponse.json(
				{ code: (body.code as string) ?? "NOT_FOUND", requestId },
				{ status: upstream.status, headers: { "x-request-id": requestId } },
			);
		}

		const data: unknown = await upstream.json();
		return NextResponse.json(data, {
			headers: { "cache-control": "no-store", "x-request-id": requestId },
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ code: "STORAGE_UNAVAILABLE", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}

export async function DELETE(
	request: NextRequest,
	{ params }: { params: Promise<{ id: string }> },
) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? undefined;
	const actorRole = request.headers.get("x-actor-role") ?? undefined;

	try {
		const upstream = await fetch(`${getGatewayBaseURL()}/api/v1/files/${encodeURIComponent(id)}`, {
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
