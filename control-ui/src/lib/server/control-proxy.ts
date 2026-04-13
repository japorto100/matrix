// control-proxy.ts — shared helper for all /api/control/* + /api/memory/* BFF routes.
//
// Pattern: forward request 1:1 to Go Appservice (:8090) /api/v1/control/* or
// /api/v1/memory/*. Go Appservice then forwards to Python Agent (:8094) via
// ControlProxyHandler.
//
// Usage (in a BFF route.ts):
//   import { controlProxy } from "@/lib/server/control-proxy";
//   export const GET = (req: Request) => controlProxy(req, "/api/v1/control/agents");
//   export const PATCH = (req: Request) => controlProxy(req, "/api/v1/control/agents/{role_id}");

import { getGatewayBaseURL } from "@/lib/server/gateway";

interface ProxyOptions {
	/** Forward these inbound headers (default: content-type, authorization) */
	forwardHeaders?: string[];
}

const DEFAULT_FORWARD_HEADERS = [
	"content-type",
	"authorization",
	"x-user-role",
	"x-actor-user-id",
	"x-request-id",
];

export async function controlProxy(
	req: Request,
	upstreamPath: string,
	options: ProxyOptions = {},
): Promise<Response> {
	const base = getGatewayBaseURL();
	const inboundUrl = new URL(req.url);
	const targetUrl = new URL(upstreamPath, base);
	// Copy query params
	inboundUrl.searchParams.forEach((value, key) => {
		targetUrl.searchParams.set(key, value);
	});

	const forwardHeaders = options.forwardHeaders ?? DEFAULT_FORWARD_HEADERS;
	const headers = new Headers();
	for (const h of forwardHeaders) {
		const val = req.headers.get(h);
		if (val) headers.set(h, val);
	}
	if (
		!headers.has("content-type") &&
		(req.method === "POST" || req.method === "PATCH" || req.method === "PUT")
	) {
		headers.set("content-type", "application/json");
	}

	let body: BodyInit | null = null;
	if (req.method !== "GET" && req.method !== "HEAD") {
		body = req.body;
	}

	try {
		const upstream = await fetch(targetUrl.toString(), {
			method: req.method,
			headers,
			body,
			// @ts-expect-error — Next.js edge runtime needs this for streams
			duplex: "half",
			cache: "no-store",
		});

		// Stream response back to client
		const responseHeaders = new Headers();
		upstream.headers.forEach((value, key) => {
			if (key.toLowerCase() !== "transfer-encoding") {
				responseHeaders.set(key, value);
			}
		});
		return new Response(upstream.body, {
			status: upstream.status,
			headers: responseHeaders,
		});
	} catch (err) {
		const message = err instanceof Error ? err.message : String(err);
		return new Response(
			JSON.stringify({
				error: "gateway_unreachable",
				upstream: targetUrl.toString(),
				detail: message,
			}),
			{
				status: 502,
				headers: { "content-type": "application/json" },
			},
		);
	}
}
