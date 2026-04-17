import { type NextRequest, NextResponse } from "next/server";

/**
 * QW-4: Authenticated Media Proxy
 *
 * Browser kann keinen Authorization-Header an <img src="...">, <video src="..."> etc. senden.
 * Diese Route proxied Matrix Media-Requests mit dem server-seitigen Access-Token.
 *
 * GET /api/matrix/media?mxc=server/mediaId
 * GET /api/matrix/media?mxc=server/mediaId&thumbnail=1&w=800&h=600
 */
export async function GET(req: NextRequest) {
	const mxc = req.nextUrl.searchParams.get("mxc");
	if (!mxc) {
		return NextResponse.json({ error: "mxc param required" }, { status: 400 });
	}

	const homeserverUrl = process.env.MATRIX_HOMESERVER_URL;
	const accessToken = process.env.MATRIX_ACCESS_TOKEN;

	if (!homeserverUrl || !accessToken) {
		return NextResponse.json({ error: "Matrix env not configured" }, { status: 500 });
	}

	const isThumbnail = req.nextUrl.searchParams.get("thumbnail") === "1";
	const width = req.nextUrl.searchParams.get("w") ?? "800";
	const height = req.nextUrl.searchParams.get("h") ?? "600";

	// Authenticated Media API (MSC3916): /_matrix/client/v1/media/...
	// Fallback auf Legacy: /_matrix/media/v3/...
	let mediaUrl: string;
	if (isThumbnail) {
		mediaUrl = `${homeserverUrl}/_matrix/client/v1/media/thumbnail/${mxc}?width=${width}&height=${height}&method=scale`;
	} else {
		mediaUrl = `${homeserverUrl}/_matrix/client/v1/media/download/${mxc}`;
	}

	try {
		const res = await fetch(mediaUrl, {
			headers: { Authorization: `Bearer ${accessToken}` },
			signal: AbortSignal.timeout(15_000),
		});

		if (!res.ok) {
			// Fallback auf Legacy-API (für Homeserver ohne MSC3916)
			const legacyUrl = isThumbnail
				? `${homeserverUrl}/_matrix/media/v3/thumbnail/${mxc}?width=${width}&height=${height}&method=scale`
				: `${homeserverUrl}/_matrix/media/v3/download/${mxc}`;

			const legacyRes = await fetch(legacyUrl, {
				signal: AbortSignal.timeout(15_000),
			});

			if (!legacyRes.ok) {
				return NextResponse.json({ error: "Media fetch failed" }, { status: legacyRes.status });
			}

			return new NextResponse(legacyRes.body, {
				headers: {
					"Content-Type": legacyRes.headers.get("Content-Type") ?? "application/octet-stream",
					"Cache-Control": "public, max-age=86400, immutable",
				},
			});
		}

		return new NextResponse(res.body, {
			headers: {
				"Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream",
				"Cache-Control": "public, max-age=86400, immutable",
			},
		});
	} catch {
		return NextResponse.json({ error: "Media unavailable" }, { status: 503 });
	}
}
