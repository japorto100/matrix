// Agent Models BFF — proxy to Python backend via Go Gateway
// Returns user's available models (dynamic from provider APIs)

import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";

export async function GET(request: NextRequest) {
	const target = new URL("/api/v1/control/user/llm", getGatewayBaseURL());

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
			headers: { "Cache-Control": "private, max-age=60" },
		});
	} catch {
		return Response.json({ error: "Gateway unreachable" }, { status: 502 });
	}
}
