// GET /api/control/agents — read-only, no-store (AC10, AC11)

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const DEGRADED_FALLBACK = { agents: [], degraded: true };

function jsonResponse(body: unknown, requestId: string) {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: {
			"Content-Type": "application/json",
			"Cache-Control": "no-store",
			"X-Request-ID": requestId,
		},
	});
}

export async function GET(request: NextRequest) {
	const requestId = request.headers.get("x-request-id")?.trim() ?? randomUUID();
	const userRole = request.headers.get("x-user-role")?.trim() ?? "";

	try {
		const res = await fetch(`${getGatewayBaseURL()}/api/v1/control/agents`, {
			headers: {
				Accept: "application/json",
				"X-Request-ID": requestId,
				...(userRole ? { "X-User-Role": userRole } : {}),
			},
			cache: "no-store",
			signal: AbortSignal.timeout(5000),
		});

		if (!res.ok) {
			return jsonResponse(
				{ ...DEGRADED_FALLBACK, degraded_reasons: [`GATEWAY_HTTP_${res.status}`], requestId },
				requestId,
			);
		}

		const body: unknown = await res.json();
		return jsonResponse({ ...(body as object), requestId }, requestId);
	} catch (err) {
		const reason =
			err instanceof Error && err.name === "TimeoutError" ? "GATEWAY_TIMEOUT" : "GATEWAY_ERROR";
		return jsonResponse(
			{
				...DEGRADED_FALLBACK,
				degraded_reasons: [reason],
				message: getErrorMessage(err),
				requestId,
			},
			requestId,
		);
	}
}
