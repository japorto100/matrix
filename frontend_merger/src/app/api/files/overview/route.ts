// GET /api/files/overview — aggregate file statistics for the Files tab header
// exec-19 Stufe 3. Proxies to Go /api/v1/files/overview.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";

	try {
		const upstream = await fetch(`${getGatewayBaseURL()}/api/v1/files/overview`, {
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
				{ code: (body.code as string) ?? "STORAGE_UNAVAILABLE", requestId },
				{ status: upstream.status, headers: { "x-request-id": requestId } },
			);
		}

		const raw = (await upstream.json()) as Record<string, unknown>;
		// go-appservice wraps responses in `{success, data}` — unwrap so the
		// frontend sees the flat shape its type definitions expect.
		const data = raw && typeof raw === "object" && "data" in raw ? raw.data : raw;
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
