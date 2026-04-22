// GET /api/files — file list for the various Files tabs. Frontend tabs
// (Images/Audio/Video/Data/Documents/Overview) expect
// `{ recent_uploads: FileRecord[] }` — the overview shape. We proxy to
// /api/v1/files/overview (not /api/v1/files paginated list) and unwrap the
// `{success, data}` envelope the go-appservice returns.
//
// Query params (search, type, status) are forwarded in case the user paged
// deeper, but overview is the default.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";

	try {
		const upstreamUrl = new URL(`${getGatewayBaseURL()}/api/v1/files/overview`);
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

		const raw = (await upstream.json()) as Record<string, unknown>;
		// go-appservice wraps all /api/v1/* in `{success, data}` — unwrap so the
		// frontend sees the flat `{recent_uploads, total_files, ...}` shape.
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
