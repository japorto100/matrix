// Agent Chat BFF - Phase 22d
// SSE proxy: Next.js → Go Gateway → Python/Anthropic.
// Converts Python error format (error) → ai v6 format (errorText) for DefaultChatTransport.
// Sets x-vercel-ai-ui-message-stream: v1 so DefaultChatTransport parses stream natively.

import { randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { getGatewayBaseURL } from "@/lib/server/gateway";
import { getErrorMessage } from "@/lib/utils";

const ENCODER = new TextEncoder();
const DECODER = new TextDecoder();

const attachmentSchema = z.object({
	base64: z.string().min(1),
	mime_type: z.string().max(50),
	name: z.string().max(255),
});

const chatRequestSchema = z
	.object({
		message: z.string().trim().min(1),
		threadId: z.string().trim().min(1).optional(),
		agentId: z.string().trim().min(1).optional(),
		/** AC107: optional model override (e.g. claude-opus-4-6, claude-haiku-4-5) */
		model: z.string().trim().min(1).optional(),
		/** AC56: multimodal image attachments */
		attachments: z.array(attachmentSchema).max(5).optional(),
		/** AC108: reasoning effort — dynamic per provider (LiteLLM validates) */
		reasoningEffort: z.string().trim().min(1).optional(),
		/** exec-09: Browser-Tools via WebMCP (dynamisch je nach aktueller Page) */
		browserTools: z
			.array(
				z.object({
					name: z.string(),
					description: z.string(),
					input_schema: z.record(z.string(), z.unknown()),
				}),
			)
			.optional(),
	})
	.strict();

function jsonError(message: string, reason: string, requestId: string, status: number): Response {
	return new Response(JSON.stringify({ error: message, reason }), {
		status,
		headers: { "Content-Type": "application/json", "X-Request-ID": requestId },
	});
}

function sseErrorFrame(msg: string): Uint8Array {
	return ENCODER.encode(`data: ${JSON.stringify({ type: "error", errorText: msg })}\n\n`);
}

/**
 * Smooth text deltas by splitting into word-sized chunks with micro-delays.
 * Non-text frames pass through immediately.
 * Returns an array of frames to emit (may be 1:1 or 1:N for text deltas).
 */
const SMOOTH_DELAY_MS = 12;

function splitTextDelta(frame: string): string[] {
	const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
	if (!dataLine) return [frame];
	try {
		const parsed = JSON.parse(dataLine.slice(5).trim()) as Record<string, unknown>;
		if (parsed.type !== "text-delta" || typeof parsed.textDelta !== "string") return [frame];

		const text = parsed.textDelta as string;
		// Split into words (keep whitespace attached to following word)
		const words = text.match(/\S+\s*/g);
		if (!words || words.length <= 1) return [frame];

		return words.map((word) => {
			const chunk = { ...parsed, textDelta: word };
			return `data: ${JSON.stringify(chunk)}`;
		});
	} catch {
		return [frame];
	}
}

/**
 * Fix Python error format: { type:"error", error:"msg" } → { type:"error", errorText:"msg" }
 * ai v6 DefaultChatTransport expects errorText, not error.
 */
function rewriteFrame(rawFrame: string): string {
	const dataLine = rawFrame.split("\n").find((l) => l.startsWith("data:"));
	if (!dataLine) return rawFrame;
	try {
		const parsed = JSON.parse(dataLine.slice(5).trim()) as Record<string, unknown>;
		if (parsed.type === "error" && "error" in parsed && !("errorText" in parsed)) {
			const { error: errMsg, ...rest } = parsed;
			const fixed = { ...rest, errorText: errMsg };
			const fixedLine = `data: ${JSON.stringify(fixed)}`;
			return rawFrame.replace(dataLine, fixedLine);
		}
	} catch {
		// pass through unchanged
	}
	return rawFrame;
}

export async function POST(request: NextRequest) {
	const requestId = request.headers.get("x-request-id")?.trim() || randomUUID();
	const userRole = request.headers.get("x-user-role")?.trim() || "";

	let payload: unknown;
	try {
		payload = await request.json();
	} catch {
		return jsonError("Invalid request body", "INVALID_JSON_BODY", requestId, 400);
	}

	const parsed = chatRequestSchema.safeParse(payload);
	if (!parsed.success) {
		return jsonError("Invalid chat payload", "INVALID_CHAT_PAYLOAD", requestId, 400);
	}

	const body = parsed.data;
	const gatewayURL = new URL("/api/v1/agent/chat", getGatewayBaseURL());
	const headers: Record<string, string> = {
		"Content-Type": "application/json",
		Accept: "text/event-stream",
		"X-Request-ID": requestId,
	};
	if (userRole) headers["X-User-Role"] = userRole;

	let upstream: Response;
	try {
		upstream = await fetch(gatewayURL.toString(), {
			method: "POST",
			headers,
			body: JSON.stringify({
				message: body.message,
				threadId: body.threadId,
				agentId: body.agentId,
				model: body.model,
				attachments: body.attachments,
				reasoningEffort: body.reasoningEffort,
				browserTools: body.browserTools,
			}),
			cache: "no-store",
			signal: request.signal,
		});
	} catch (err) {
		const stream = new ReadableStream<Uint8Array>({
			start(controller) {
				controller.enqueue(sseErrorFrame(`Agent gateway unreachable: ${getErrorMessage(err)}`));
				controller.close();
			},
		});
		return new Response(stream, {
			headers: {
				"Content-Type": "text/event-stream",
				"x-vercel-ai-ui-message-stream": "v1",
				"Cache-Control": "no-cache, no-transform",
				"X-Request-ID": requestId,
				"X-Stream-Backend": "unavailable",
			},
		});
	}

	if (!upstream.ok || !upstream.body) {
		const stream = new ReadableStream<Uint8Array>({
			start(controller) {
				controller.enqueue(sseErrorFrame(`Agent gateway error: HTTP ${upstream.status}`));
				controller.close();
			},
		});
		return new Response(stream, {
			headers: {
				"Content-Type": "text/event-stream",
				"x-vercel-ai-ui-message-stream": "v1",
				"Cache-Control": "no-cache, no-transform",
				"X-Request-ID": requestId,
			},
		});
	}

	let cancelled = false;
	const proxyStream = new ReadableStream<Uint8Array>({
		start(controller) {
			const reader = upstream.body!.getReader();
			let buffer = "";

			const close = async () => {
				if (cancelled) return;
				cancelled = true;
				try {
					await reader.cancel();
				} catch {
					// ignore
				}
				controller.close();
			};

			request.signal.addEventListener("abort", () => {
				void close();
			});

			void (async () => {
				const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
				try {
					while (!cancelled) {
						const { done, value } = await reader.read();
						if (done) break;
						buffer += DECODER.decode(value, { stream: true });
						let boundary = buffer.indexOf("\n\n");
						while (boundary >= 0) {
							const rawFrame = buffer.slice(0, boundary);
							buffer = buffer.slice(boundary + 2);
							if (rawFrame.trim()) {
								const frame = rewriteFrame(rawFrame);
								const chunks = splitTextDelta(frame);
								for (let i = 0; i < chunks.length && !cancelled; i++) {
									controller.enqueue(ENCODER.encode(`${chunks[i]}\n\n`));
									if (chunks.length > 1 && i < chunks.length - 1) {
										await sleep(SMOOTH_DELAY_MS);
									}
								}
							}
							boundary = buffer.indexOf("\n\n");
						}
					}
					if (!cancelled && buffer.trim()) {
						const frame = rewriteFrame(buffer);
						controller.enqueue(ENCODER.encode(`${frame}\n\n`));
					}
				} catch (err) {
					if (!cancelled) {
						controller.enqueue(sseErrorFrame(`Stream interrupted: ${getErrorMessage(err)}`));
					}
				} finally {
					if (!cancelled) {
						controller.close();
					}
				}
			})();
		},
		cancel() {
			cancelled = true;
		},
	});

	return new Response(proxyStream, {
		headers: {
			"Content-Type": "text/event-stream",
			"x-vercel-ai-ui-message-stream": "v1",
			"Cache-Control": "no-cache, no-transform",
			Connection: "keep-alive",
			"X-Accel-Buffering": "no",
			"X-Request-ID": requestId,
			"X-Stream-Backend": "go-agent",
		},
	});
}
