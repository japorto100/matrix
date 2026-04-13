// POST /api/files/[id]/mark-ready — finalize a direct-PUT upload
// exec-19 Stufe 3. Proxies to Go /api/v1/files/{id}/mark-ready.
// Returns 207 Multi-Status when mark-ready succeeds but auto-ingest fails.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";

	try {
		const body = await request.text();
		const upstream = await fetch(
			`${getGatewayBaseURL()}/api/v1/files/${encodeURIComponent(id)}/mark-ready`,
			{
				method: "POST",
				headers: {
					"content-type": "application/json",
					"x-request-id": requestId,
					"x-actor-user-id": actorUserId,
				},
				body,
				cache: "no-store",
			},
		);

		const data: unknown = await upstream.json().catch(() => ({}));
		return NextResponse.json(data, {
			status: upstream.status,
			headers: { "x-request-id": requestId },
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ code: "STORAGE_UNAVAILABLE", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}
