import { type NextRequest, NextResponse } from "next/server";

/**
 * Dev-mode BFF actor injection.
 *
 * Production will replace this with a proper session-cookie lookup (NextAuth,
 * Matrix access-token, etc.). For now the go-appservice's X-Actor-User-Id
 * header is the only gate on /api/v1/files|memory|control routes and the
 * browser can't send it on its own. Without the default here every request
 * bounces off `success:false / forbidden`.
 */

const DEFAULT_ACTOR_USER_ID = process.env.NEXT_PUBLIC_DEFAULT_ACTOR_USER_ID ?? "alice";

export function middleware(req: NextRequest) {
	// Only touch /api/* — no point adding headers to page requests.
	if (!req.nextUrl.pathname.startsWith("/api/")) {
		return NextResponse.next();
	}
	if (req.headers.has("x-actor-user-id")) {
		return NextResponse.next();
	}
	const headers = new Headers(req.headers);
	headers.set("x-actor-user-id", DEFAULT_ACTOR_USER_ID);
	return NextResponse.next({ request: { headers } });
}

export const config = {
	matcher: "/api/:path*",
};
