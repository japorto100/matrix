// GET /api/control/kg-context — read-only, no-store (AC8, AC11)
// Knowledge graph stats + recent nodes.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const DEGRADED_FALLBACK = {
	stats: { nodeCount: 0, edgeCount: 0, health: "unknown", lastSyncAt: null },
	recentNodes: [],
	inspector: {
		activeSession: null,
		sourceLayerCounts: {},
		contextBlocks: [],
		worldClaims: [],
		degradationFlags: ["NO_WORLD_KG"],
	},
	degraded: true,
	degradedReasons: ["GATEWAY_ERROR"],
};

function asRecord(value: unknown): Record<string, unknown> {
	return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function normalizeHealth(value: unknown): "healthy" | "degraded" | "offline" | "unknown" {
	const health = String(value ?? "").trim().toLowerCase();
	if (health === "ok" || health === "ready" || health === "healthy") return "healthy";
	if (health === "warning" || health === "degraded") return "degraded";
	if (health === "error" || health === "offline") return "offline";
	return "unknown";
}

function normalizePayload(body: unknown, requestId: string) {
	const record = asRecord(body);
	const stats = asRecord(record.stats);
	const recentNodes = Array.isArray(record.recentNodes) ? record.recentNodes : [];
	const degradedReasons = (
		Array.isArray(record.degradedReasons)
			? record.degradedReasons
			: Array.isArray(record.degraded_reasons)
				? record.degraded_reasons
				: []
	).map((entry) => String(entry));
	const degraded = Boolean(record.degraded ?? degradedReasons.length > 0);
	return {
		...record,
		stats: {
			nodeCount: Number(stats.nodeCount ?? stats.node_count ?? 0),
			edgeCount: Number(stats.edgeCount ?? stats.edge_count ?? 0),
			health: normalizeHealth(stats.health),
			lastSyncAt: (stats.lastSyncAt ?? stats.last_sync_at ?? null) as string | null,
		},
		recentNodes: recentNodes.map((node) => {
			const item = asRecord(node);
			return {
				id: String(item.id ?? ""),
				label: String(item.label ?? item.node ?? ""),
				type: String(item.type ?? "unknown"),
				connectedEdges: Number(item.connectedEdges ?? item.connected_edges ?? 0),
			};
		}),
		inspector: asRecord(record.inspector),
		degraded,
		degradedReasons,
		requestId,
	};
}

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
		const res = await fetch(`${getGatewayBaseURL()}/api/v1/control/kg-context`, {
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
				{
					...DEGRADED_FALLBACK,
					degradedReasons: [`GATEWAY_HTTP_${res.status}`],
					requestId,
				},
				requestId,
			);
		}

		const body: unknown = await res.json();
		return jsonResponse(normalizePayload(body, requestId), requestId);
	} catch (err) {
		const reason =
			err instanceof Error && err.name === "TimeoutError" ? "GATEWAY_TIMEOUT" : "GATEWAY_ERROR";
		return jsonResponse(
			{
				...DEGRADED_FALLBACK,
				degradedReasons: [reason],
				message: getErrorMessage(err),
				requestId,
			},
			requestId,
		);
	}
}
