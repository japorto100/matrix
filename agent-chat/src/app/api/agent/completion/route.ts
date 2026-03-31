// AC95: Single-shot indicator explanation endpoint for useCompletion.
// Proxies to Go Gateway /api/v1/agent/chat (one-shot, no threadId).
// Converts UIMessage SSE stream → plain text stream expected by useCompletion.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const ENCODER = new TextEncoder();
const DECODER = new TextDecoder();

const requestSchema = z.object({
	prompt: z.string().trim().min(1).max(500),
});

const SYSTEM_PREFIX =
	"You are a concise trading analyst. Explain this indicator in 2-3 short plain-text sentences. Be direct and actionable. No markdown, no lists:\n\n";

export async function POST(req: NextRequest) {
	const requestId = randomUUID();

	let body: unknown;
	try {
		body = await req.json();
	} catch {
		return new Response("Invalid JSON", { status: 400 });
	}

	const parsed = requestSchema.safeParse(body);
	if (!parsed.success) {
		return new Response("Bad request", { status: 400 });
	}

	const gatewayURL = new URL("/api/v1/agent/chat", getGatewayBaseURL());

	let upstream: Response;
	try {
		upstream = await fetch(gatewayURL.toString(), {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Accept: "text/event-stream",
				"X-Request-ID": requestId,
			},
			body: JSON.stringify({
				message: SYSTEM_PREFIX + parsed.data.prompt,
				model: "claude-haiku-4-5-20251001",
			}),
			cache: "no-store",
			signal: req.signal,
		});
	} catch (err) {
		return new Response(getErrorMessage(err), { status: 503 });
	}

	if (!upstream.ok || !upstream.body) {
		return new Response(`Gateway error: HTTP ${upstream.status}`, { status: 502 });
	}

	// Convert UIMessage SSE frames → plain text stream for useCompletion
	const reader = upstream.body.getReader();
	const stream = new ReadableStream<Uint8Array>({
		async pull(controller) {
			try {
				const { done, value } = await reader.read();
				if (done) {
					controller.close();
					return;
				}
				const raw = DECODER.decode(value, { stream: true });
				for (const line of raw.split("\n")) {
					if (!line.startsWith("data:")) continue;
					const json = line.slice(5).trim();
					if (!json || json === "[DONE]") continue;
					try {
						const frame = JSON.parse(json) as Record<string, unknown>;
						// UIMessage stream: text-delta frames carry the text
						if (frame.type === "text-delta" && typeof frame.textDelta === "string") {
							controller.enqueue(ENCODER.encode(frame.textDelta));
						}
					} catch {
						// skip malformed frames
					}
				}
			} catch {
				controller.close();
			}
		},
		cancel() {
			void reader.cancel();
		},
	});

	return new Response(stream, {
		headers: {
			"Content-Type": "text/plain; charset=utf-8",
			"Cache-Control": "no-cache, no-transform",
			"X-Request-ID": requestId,
		},
	});
}
