import { type NextRequest, NextResponse } from "next/server";

/**
 * B-5: URL-Preview Proxy
 * Leitet /_matrix/client/v3/preview_url an den Homeserver weiter (mit Auth-Header).
 * Browser kann keinen Authorization-Header an externe URLs senden → Proxy nötig.
 *
 * GET /api/matrix/preview?url=https://example.com
 */
export async function GET(req: NextRequest) {
	const url = req.nextUrl.searchParams.get("url");
	if (!url) {
		return NextResponse.json({ error: "url param required" }, { status: 400 });
	}

	const homeserverUrl = process.env.MATRIX_HOMESERVER_URL;
	if (!homeserverUrl) {
		return NextResponse.json({ error: "Matrix env not configured" }, { status: 500 });
	}

	// B-5: Prefer user's session token from Authorization header; fall back to static env token
	const authHeader = req.headers.get("authorization");
	const accessToken = authHeader?.startsWith("Bearer ")
		? authHeader.slice(7)
		: process.env.MATRIX_ACCESS_TOKEN;

	if (!accessToken) {
		return NextResponse.json({ error: "No access token provided" }, { status: 401 });
	}

	try {
		const previewUrl = new URL("/_matrix/client/v3/preview_url", homeserverUrl);
		previewUrl.searchParams.set("url", url);

		const res = await fetch(previewUrl.toString(), {
			headers: { Authorization: `Bearer ${accessToken}` },
			// 5s Timeout — Preview-Fetch darf nicht blockieren
			signal: AbortSignal.timeout(5000),
		});

		if (!res.ok) {
			return NextResponse.json({ error: "Preview fetch failed" }, { status: res.status });
		}

		const data = await res.json();
		return NextResponse.json(data, {
			headers: {
				// Client darf 5 Minuten cachen
				"Cache-Control": "public, max-age=300",
			},
		});
	} catch {
		return NextResponse.json({ error: "Preview unavailable" }, { status: 503 });
	}
}
