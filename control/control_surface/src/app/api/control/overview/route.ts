// Control Overview BFF — Phase 22b (AC11, AC12, AC13)
// read-only, no-store, X-Request-ID propagation.
// Aggregates runtime health signals from Go Gateway.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

function errorResponse(requestId: string, status: number, message: string) {
	return new Response(JSON.stringify({ success: false, error: message, requestId }), {
		status,
		headers: {
			"Content-Type": "application/json",
			"Cache-Control": "no-store",
			"X-Request-ID": requestId,
		},
	});
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
		const res = await fetch(new URL("/api/v1/control/overview", getGatewayBaseURL()).toString(), {
			headers,
			cache: "no-store",
			signal: AbortSignal.timeout(5000),
		});

		if (!res.ok) {
			// Gateway unavailable — return degraded placeholder (AC.V4 empty state)
			return new Response(
				JSON.stringify({
					runtimeHealth: "unknown",
					memoryHealth: "unknown",
					securityPosture: "unknown",
					activeSessions: 0,
					recentToolErrors: 0,
					lastUpdated: new Date().toISOString(),
					degraded: true,
					degraded_reasons: [`GATEWAY_HTTP_${res.status}`],
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

		const body = await res.json();
		return new Response(JSON.stringify({ ...body, requestId }), {
			headers: {
				"Content-Type": "application/json",
				"Cache-Control": "no-store",
				"X-Request-ID": requestId,
			},
		});
	} catch (err) {
		// Gateway unreachable — return degraded placeholder (visible degradation, no silent fallback)
		if (err instanceof Error && err.name === "TimeoutError") {
			return new Response(
				JSON.stringify({
					runtimeHealth: "unknown",
					memoryHealth: "unknown",
					securityPosture: "unknown",
					activeSessions: 0,
					recentToolErrors: 0,
					lastUpdated: new Date().toISOString(),
					degraded: true,
					degraded_reasons: ["GATEWAY_TIMEOUT"],
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
		return errorResponse(requestId, 502, `Gateway unavailable: ${getErrorMessage(err)}`);
	}
}
