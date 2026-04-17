// GET /api/control/memory — read-only, no-store (AC8, AC11)
// Memory layer health: episodic / kg / vector.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const DEGRADED_FALLBACK = {
	layers: [],
	ops: { layers: [], degraded: true, degradedReasons: ["GATEWAY_ERROR"] },
	inspector: {
		activeSession: null,
		sourceLayerCounts: {},
		contextBlocks: [],
		degradationFlags: ["NO_PERSONAL_MEMORY"],
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

function normalizeLayer(value: unknown) {
	const layer = asRecord(value);
	return {
		type: String(layer.type ?? "episodic") as "episodic" | "kg" | "vector",
		provider: String(layer.provider ?? ""),
		health: normalizeHealth(layer.health),
		itemCount: Number(layer.itemCount ?? layer.item_count ?? 0),
		lastSyncAt: (layer.lastSyncAt ?? layer.last_sync_at ?? null) as string | null,
		consolidationPending: Number(layer.consolidationPending ?? layer.consolidation_pending ?? 0),
	};
}

function normalizePayload(body: unknown, requestId: string) {
	const record = asRecord(body);
	const ops = asRecord(record.ops);
	const rawLayers = Array.isArray(record.layers)
		? record.layers
		: Array.isArray(ops.layers)
			? ops.layers
			: [];
	const layers = rawLayers.map(normalizeLayer);
	const degradedReasons = (
		Array.isArray(record.degradedReasons)
			? record.degradedReasons
			: Array.isArray(record.degraded_reasons)
				? record.degraded_reasons
				: Array.isArray(ops.degradedReasons)
					? ops.degradedReasons
					: []
	).map((entry) => String(entry));
	const degraded = Boolean(record.degraded ?? ops.degraded ?? degradedReasons.length > 0);
	return {
		...record,
		layers,
		ops: {
			...ops,
			layers,
			degraded,
			degradedReasons,
		},
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
		const res = await fetch(`${getGatewayBaseURL()}/api/v1/control/memory`, {
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
