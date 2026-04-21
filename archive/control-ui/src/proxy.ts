// proxy.ts — Next.js 16 Proxy (successor to middleware.ts)
//
// Runs on every /api/* request BEFORE route handlers. Injects the
// X-Actor-User-Id header that go-appservice uses for per-user isolation
// (see specs/17-schema-ownership.md "Trust boundary: BFF is the gatekeeper").
//
// Dev mode (no auth): sets a hardcoded default user so the Files API works
// out-of-the-box without NextAuth or Matrix session.
//
// Production / portierung to tradefusion: replace the dev-fallback with
// the authenticated user from NextAuth JWT (token.sub) — same pattern as
// tradeview-fusion/src/proxy.ts which reads `getToken()` from next-auth/jwt.
//
// This file is the SINGLE place that maps "who is the current user" to the
// outgoing header. No BFF route should ever hardcode or guess the user.

import { type NextRequest, NextResponse } from "next/server";

const REQUEST_ID_HEADER = "x-request-id";

function getDevDefaultUser(): string {
	return (process.env.DEV_DEFAULT_USER ?? "").trim();
}

export function proxy(request: NextRequest) {
	const requestHeaders = new Headers(request.headers);

	// Ensure every request has a trace-friendly request ID
	if (!requestHeaders.get(REQUEST_ID_HEADER)) {
		requestHeaders.set(REQUEST_ID_HEADER, crypto.randomUUID());
	}

	// ── User Identity ──────────────────────────────────────────────
	// In production with NextAuth:
	//   const token = await getToken({ req: request });
	//   if (token?.sub) requestHeaders.set("x-actor-user-id", token.sub);
	//
	// In dev mode without auth: inject a stable default so Go's
	// ownership checks + signed tokens work correctly. The value
	// comes from DEV_DEFAULT_USER env var (set in .env.local).
	// Empty = no injection (production with NextAuth handles it).
	if (!requestHeaders.get("x-actor-user-id")) {
		const devUser = getDevDefaultUser();
		if (devUser) {
			requestHeaders.set("x-actor-user-id", devUser);
		}
	}

	return NextResponse.next({
		request: { headers: requestHeaders },
	});
}

export const config = {
	matcher: ["/api/:path*"],
};
