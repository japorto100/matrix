// exec-06 §4c Phase 5 — compression indicator endpoint
// GET /api/v1/agent/context/compression-status?thread_id=X&model=Y
// Returns {thread_id, model, window, thresholds, stage, engine}.

import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";

export async function GET(request: NextRequest) {
	const url = new URL(request.url);
	const target = new URL("/api/v1/agent/context/compression-status", getGatewayBaseURL());
	for (const [k, v] of url.searchParams.entries()) {
		target.searchParams.set(k, v);
	}

	try {
		const upstream = await fetch(target.toString(), {
			method: "GET",
			headers: { Accept: "application/json" },
			cache: "no-store",
			signal: request.signal,
		});

		if (!upstream.ok) {
			return Response.json(
				{ error: `Upstream error: ${upstream.status}` },
				{ status: upstream.status },
			);
		}

		const data = await upstream.json();
		return Response.json(data, {
			headers: { "Cache-Control": "private, max-age=300" },
		});
	} catch {
		return Response.json({ error: "Gateway unreachable" }, { status: 502 });
	}
}
