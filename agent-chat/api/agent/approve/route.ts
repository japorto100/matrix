// AC66: Tool-Approval BFF — proxies approve/deny decision to Go Gateway.
// Go holds the tool-call pending until this endpoint is called.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const requestSchema = z.object({
	toolCallId: z.string().min(1),
	decision: z.enum(["approve", "deny"]),
	threadId: z.string().optional(),
});

export async function POST(req: NextRequest) {
	const requestId = req.headers.get("x-request-id") ?? randomUUID();

	let body: unknown;
	try {
		body = await req.json();
	} catch {
		return new Response("Invalid JSON", { status: 400 });
	}

	const parsed = requestSchema.safeParse(body);
	if (!parsed.success) {
		return new Response(`Bad request: ${parsed.error.message}`, { status: 400 });
	}

	const url = new URL("/api/v1/agent/approve", getGatewayBaseURL());

	try {
		const upstream = await fetch(url.toString(), {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Request-ID": requestId,
			},
			body: JSON.stringify(parsed.data),
			cache: "no-store",
			signal: req.signal,
		});

		if (!upstream.ok) {
			return new Response(`Gateway error: HTTP ${upstream.status}`, { status: 502 });
		}

		return new Response(null, { status: 204 });
	} catch (err) {
		return new Response(getErrorMessage(err), { status: 503 });
	}
}
