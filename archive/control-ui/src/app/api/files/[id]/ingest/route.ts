// POST /api/files/[id]/ingest — trigger ingestion pipeline for an uploaded file
// exec-19 Stufe 3. Proxies to Go /api/v1/files/{id}/ingest.
// Body: { "pipeline": "document" | "image" | "audio" | "video" | "" (auto-detect) }

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
			`${getGatewayBaseURL()}/api/v1/files/${encodeURIComponent(id)}/ingest`,
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
