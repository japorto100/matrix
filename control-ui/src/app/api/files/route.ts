// GET /api/files — list files + metadata
// BFF boundary: proxies to Go Gateway (DW13, DW14, DW15)
// no-store: metadata must always be fresh.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getErrorMessage } from "@/lib/utils";

const GATEWAY_BASE = process.env.GATEWAY_URL ?? "http://localhost:9060";

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();

	try {
		const upstreamUrl = `${GATEWAY_BASE}/api/v1/files`;
		const upstream = await fetch(upstreamUrl, {
			headers: {
				"x-request-id": requestId,
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
