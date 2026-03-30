// Audio Transcribe BFF — Phase 22f / AC48
// Proxies to Go Gateway → Python agent /api/v1/audio/transcribe
// Accepts { audio_base64, mime_type?, language? } → returns { ok, text }

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const transcribeSchema = z.object({
	audio_base64: z.string().min(1),
	mime_type: z.string().max(50).optional().default("audio/webm"),
	language: z.string().max(10).optional(),
});

export async function POST(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? randomUUID();

	let payload: unknown;
	try {
		payload = await request.json();
	} catch {
		return Response.json({ ok: false, error: "Invalid JSON body" }, { status: 400 });
	}

	const parsed = transcribeSchema.safeParse(payload);
	if (!parsed.success) {
		return Response.json({ ok: false, error: "Invalid request" }, { status: 400 });
	}

	const gatewayURL = `${getGatewayBaseURL()}/api/v1/audio/transcribe`;

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
		const json = await upstream.json();
		return Response.json(json, { status: upstream.ok ? 200 : 502 });
	} catch (err) {
		return Response.json(
			{ ok: false, error: `Transcribe unavailable: ${getErrorMessage(err)}` },
			{ status: 502 },
		);
	}
}
