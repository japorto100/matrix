// Catch-all BFF proxy for /api/memory/* → Go Appservice (:8090) → Python Agent (:8094)
// Slice 7 Phase H. Memory sub-routes map to /api/v1/control/memory/* and
// /api/v1/control/episodes/* and /api/v1/control/kg/* on the python backend.
//
// Mapping (BFF → Python):
//   /api/memory/health                 → /api/v1/control/memory/health
//   /api/memory/banks                  → /api/v1/control/memory/banks
//   /api/memory/episodes               → /api/v1/control/episodes
//   /api/memory/episodes/{id}          → /api/v1/control/episodes/{id}
//   /api/memory/kg/nodes               → /api/v1/control/kg/nodes
//   /api/memory/kg/nodes/{id}          → /api/v1/control/kg/nodes/{id}
//   /api/memory/kg/edges               → /api/v1/control/kg/edges
//   /api/memory/kg/seed                → /api/v1/control/kg/seed

import { controlProxy } from "@/lib/server/control-proxy";

interface RouteContext {
	params: Promise<{ path: string[] }>;
}

function mapPath(segments: string[]): string {
	const [first, ...rest] = segments;
	if (first === "health" || first === "banks") {
		return `/api/v1/control/memory/${first}`;
	}
	if (first === "episodes") {
		return `/api/v1/control/episodes${rest.length ? `/${rest.join("/")}` : ""}`;
	}
	if (first === "kg") {
		return `/api/v1/control/kg${rest.length ? `/${rest.join("/")}` : ""}`;
	}
	// fallback — pass-through as control/memory/*
	return `/api/v1/control/memory/${segments.join("/")}`;
}

async function handler(req: Request, ctx: RouteContext): Promise<Response> {
	const { path } = await ctx.params;
	return controlProxy(req, mapPath(path));
}

export const GET = handler;
export const POST = handler;
export const PATCH = handler;
export const PUT = handler;
export const DELETE = handler;
