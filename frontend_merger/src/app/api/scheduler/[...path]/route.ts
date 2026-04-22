// BFF proxy for /api/scheduler/* → Go Appservice (:29318) /api/v1/scheduler/*.
// Reuses the existing control-proxy machinery (header forwarding, gateway URL
// resolution). The Go side handles auth via hsTokenMiddleware.

import { controlProxy } from "@/lib/server/control-proxy";

interface RouteContext {
	params: Promise<{ path: string[] }>;
}

async function handler(req: Request, ctx: RouteContext): Promise<Response> {
	const { path } = await ctx.params;
	const upstreamPath = `/api/v1/scheduler/${path.join("/")}`;
	return controlProxy(req, upstreamPath);
}

export const GET = handler;
export const POST = handler;
export const PATCH = handler;
export const PUT = handler;
export const DELETE = handler;
