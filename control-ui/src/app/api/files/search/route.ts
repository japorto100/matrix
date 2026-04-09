// GET /api/files/search — proxy to Meilisearch / fuse.js metadata index
// v1: Go proxies to fuse.js index or embedded search
// v1.5: upgrade to Meilisearch

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getErrorMessage } from "@/lib/utils";

const GATEWAY_BASE = process.env.GATEWAY_URL ?? "http://localhost:9060";

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const { searchParams } = new URL(request.url);
	const q = searchParams.get("q") ?? "";

	try {
		const upstreamUrl = new URL(`${GATEWAY_BASE}/api/v1/files/search`);
		if (q) upstreamUrl.searchParams.set("q", q);

		const upstream = await fetch(upstreamUrl.toString(), {
			headers: { "x-request-id": requestId },
			cache: "no-store",
		});

		if (!upstream.ok) {
			const err = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
			return NextResponse.json(
				{ code: (err.code as string) ?? "NO_DOCUMENT_INDEX", requestId },
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
			{ code: "NO_DOCUMENT_INDEX", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}
