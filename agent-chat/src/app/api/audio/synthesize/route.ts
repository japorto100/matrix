// Audio Synthesize BFF — Phase 22f / AC49b
// Proxies to Go Gateway → Python agent /api/v1/audio/synthesize
// Accepts { text, voice?, model? } → returns audio/mpeg bytes

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const synthesizeSchema = z.object({
	text: z.string().min(1).max(4096),
	voice: z.enum(["alloy", "echo", "fable", "onyx", "nova", "shimmer"]).optional().default("alloy"),
	model: z.string().max(50).optional(),
});

export async function POST(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? randomUUID();

	let payload: unknown;
	try {
		payload = await request.json();
	} catch {
		return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
	}

	const parsed = synthesizeSchema.safeParse(payload);
	if (!parsed.success) {
		return Response.json({ ok: false, error: "Invalid request" }, { status: 400 });
	}

	const gatewayURL = `${getGatewayBaseURL()}/api/v1/audio/synthesize`;

	try {
		const upstream = await fetch(gatewayURL, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Request-ID": requestId,
			},
			body: JSON.stringify(parsed.data),
			signal: request.signal,
		});

		if (!upstream.ok) {
			const err = await upstream.json().catch(() => ({ error: `HTTP ${upstream.status}` }));
			return Response.json(
				{ ok: false, error: (err as { error?: string }).error ?? "Synthesize failed" },
				{ status: 502 },
			);
		}

		const audioBytes = await upstream.arrayBuffer();
		return new Response(audioBytes, {
			headers: {
				"Content-Type": "audio/mpeg",
				"Content-Disposition": "inline; filename=speech.mp3",
				"X-Request-ID": requestId,
			},
		});
	} catch (err) {
		return Response.json(
			{ ok: false, error: `Synthesize unavailable: ${getErrorMessage(err)}` },
			{ status: 502 },
		);
	}
}
