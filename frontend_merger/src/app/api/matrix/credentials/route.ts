import { NextResponse } from "next/server";

/**
 * GET /api/matrix/credentials
 *
 * Gibt Matrix-Credentials für den Browser-Client zurück.
 * Testsetup: Aus .env.local (MATRIX_USER_ID, MATRIX_ACCESS_TOKEN, etc.)
 * Production: Aus Session + Go-Backend (Token-Exchange).
 */
export async function GET() {
	const homeserverUrl = process.env.MATRIX_HOMESERVER_URL;
	const userId = process.env.MATRIX_USER_ID;
	const accessToken = process.env.MATRIX_ACCESS_TOKEN;
	const deviceId = process.env.MATRIX_DEVICE_ID;

	if (!homeserverUrl || !userId || !accessToken) {
		return NextResponse.json(
			{
				error:
					"Matrix-Credentials nicht konfiguriert (MATRIX_HOMESERVER_URL, MATRIX_USER_ID, MATRIX_ACCESS_TOKEN)",
			},
			{ status: 503 },
		);
	}

	return NextResponse.json({
		homeserverUrl,
		userId,
		accessToken,
		deviceId: deviceId ?? undefined,
	});
}
