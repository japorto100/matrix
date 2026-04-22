// Catch-all BFF proxy for /api/control/* → Go Appservice (:29318) → Python Agent (:8094)
// Slice 7 Phase H — single thin proxy for all 54 control routes.

import { controlProxy } from "@/lib/server/control-proxy";

interface RouteContext {
	params: Promise<{ path: string[] }>;
}

async function handler(req: Request, ctx: RouteContext): Promise<Response> {
	const { path } = await ctx.params;
	const upstreamPath = `/api/v1/control/${path.join("/")}`;
	return controlProxy(req, upstreamPath);
}

export const GET = handler;
export const POST = handler;
export const PATCH = handler;
export const PUT = handler;
export const DELETE = handler;
