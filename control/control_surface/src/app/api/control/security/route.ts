// Control Security BFF — Phase 22b (AC11, AC12, AC13)
// read-only, no-store, X-Request-ID propagation.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

function degradedResponse(requestId: string, reasons: string[]) {
	return new Response(
		JSON.stringify({
			postureScore: 0,
			postureTrend: "unknown",
			recentEvents: [],
			totalBlocked: 0,
			totalApproved: 0,
			lastUpdated: new Date().toISOString(),
			degraded: true,
			degraded_reasons: reasons,
			requestId,
		}),
		{
			status: 200,
			headers: {
				"Content-Type": "application/json",
				"Cache-Control": "no-store",
				"X-Request-ID": requestId,
			},
		},
	);
}

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id")?.trim() || randomUUID();
	const userRole = request.headers.get("x-user-role")?.trim() || "";

	const headers: Record<string, string> = {
		Accept: "application/json",
		"X-Request-ID": requestId,
	};
	if (userRole) headers["X-User-Role"] = userRole;

	try {
		const res = await fetch(new URL("/api/v1/control/security", getGatewayBaseURL()).toString(), {
			headers,
			cache: "no-store",
			signal: AbortSignal.timeout(5000),
		});

		if (!res.ok) {
			return degradedResponse(requestId, [`GATEWAY_HTTP_${res.status}`]);
		}

		const body = await res.json();
		return new Response(JSON.stringify({ ...body, requestId }), {
			headers: {
				"Content-Type": "application/json",
				"Cache-Control": "no-store",
				"X-Request-ID": requestId,
			},
		});
	} catch (err) {
		const reason =
			err instanceof Error && err.name === "TimeoutError"
				? "GATEWAY_TIMEOUT"
				: `GATEWAY_ERROR: ${getErrorMessage(err)}`;
		return degradedResponse(requestId, [reason]);
	}
}
