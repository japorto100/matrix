// GET /api/files/[id]/url — fetch fresh presigned download URL (TTL 15 min)
// BFF boundary: Go Gateway signs; browser never touches object store directly (DW16).

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";

	try {
		const upstream = await fetch(
			`${getGatewayBaseURL()}/api/v1/files/${encodeURIComponent(id)}/url`,
			{
				headers: {
					"x-request-id": requestId,
					"x-actor-user-id": actorUserId,
				},
				cache: "no-store",
			},
		);

		if (!upstream.ok) {
			const body = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
			return NextResponse.json(
				{ code: (body.code as string) ?? "NO_DOCUMENT_INDEX", requestId },
				{ status: upstream.status, headers: { "x-request-id": requestId } },
			);
		}

		const data: unknown = await upstream.json();
		return NextResponse.json(data, {
			headers: {
				"cache-control": "no-store",
				"x-request-id": requestId,
			},
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ code: "STORAGE_UNAVAILABLE", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}
