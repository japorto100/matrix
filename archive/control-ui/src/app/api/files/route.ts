// GET /api/files — list files + metadata
// BFF boundary: proxies to Go Gateway /api/v1/files
// Forwards all query params (type, status, search, limit, offset) + X-Actor-User-Id.
// exec-19 Stufe 3: proxy.ts injects X-Actor-User-Id before this route runs.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";

	try {
		// Forward all query params transparently (type, status, search, limit, offset)
		const upstreamUrl = new URL(`${getGatewayBaseURL()}/api/v1/files`);
		for (const [key, value] of request.nextUrl.searchParams.entries()) {
			upstreamUrl.searchParams.set(key, value);
		}

		const upstream = await fetch(upstreamUrl.toString(), {
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
