// plan-v2 Phase-2 #31 — surfaces BFF proxy
// GET/PUT/DELETE /api/surfaces/[id] → Go appservice /api/v1/surfaces/[id]
// Backs usePersistentSurface's server-sync path (Phase-2). X-Actor-User-Id
// is sourced from the incoming request header set by the auth middleware
// (same pattern as /api/files/[id]).

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

function forwardHeaders(request: NextRequest, requestId: string): Record<string, string> {
	const actorUserId = request.headers.get("x-actor-user-id") ?? "";
	return {
		"x-request-id": requestId,
		"x-actor-user-id": actorUserId,
		accept: "application/json",
	};
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();

	try {
		const upstream = await fetch(
			`${getGatewayBaseURL()}/api/v1/surfaces/${encodeURIComponent(id)}`,
			{ headers: forwardHeaders(request, requestId), cache: "no-store", signal: request.signal },
		);
		const data: unknown = await upstream.json().catch(() => ({}));
		return NextResponse.json(data, {
			status: upstream.status,
			headers: { "cache-control": "no-store", "x-request-id": requestId },
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ error: "gateway unreachable", message: getErrorMessage(error), requestId },
			{ status: 502, headers: { "x-request-id": requestId } },
		);
	}
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const body = await request.text();

	try {
		const upstream = await fetch(
			`${getGatewayBaseURL()}/api/v1/surfaces/${encodeURIComponent(id)}`,
			{
				method: "PUT",
				headers: { ...forwardHeaders(request, requestId), "content-type": "application/json" },
				body,
				cache: "no-store",
				signal: request.signal,
			},
		);
		const data: unknown = await upstream.json().catch(() => ({}));
		return NextResponse.json(data, {
			status: upstream.status,
			headers: { "x-request-id": requestId },
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ error: "gateway unreachable", message: getErrorMessage(error), requestId },
			{ status: 502, headers: { "x-request-id": requestId } },
		);
	}
}

export async function DELETE(
	request: NextRequest,
	{ params }: { params: Promise<{ id: string }> },
) {
	const { id } = await params;
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();

	try {
		const upstream = await fetch(
			`${getGatewayBaseURL()}/api/v1/surfaces/${encodeURIComponent(id)}`,
			{ method: "DELETE", headers: forwardHeaders(request, requestId), cache: "no-store" },
		);
		if (upstream.status === 204) {
			return new NextResponse(null, {
				status: 204,
				headers: { "x-request-id": requestId },
			});
		}
		const data: unknown = await upstream.json().catch(() => ({}));
		return NextResponse.json(data, {
			status: upstream.status,
			headers: { "x-request-id": requestId },
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ error: "gateway unreachable", message: getErrorMessage(error), requestId },
			{ status: 502, headers: { "x-request-id": requestId } },
		);
	}
}
