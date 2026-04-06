import { signOut } from "next-auth/react";
import { broadcastSessionEnded } from "./session-broadcast";

export async function signOutAndBroadcast(options?: { callbackUrl?: string }): Promise<void> {
	const callbackUrl = options?.callbackUrl ?? "/auth/sign-in";
	// CRITICAL: signOut FIRST so the server clears the httpOnly cookie via Set-Cookie: Max-Age=0.
	// broadcastSessionEnded() must come AFTER — otherwise other tabs call updateSession() concurrently,
	// which re-issues a fresh JWT cookie that overwrites the cleared one (race condition).
	await signOut({ redirect: false });
	broadcastSessionEnded();
	window.location.href = callbackUrl;
}
