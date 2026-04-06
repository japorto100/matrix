/**
 * Server-side pending TOTP secrets.
 * Stored during setupTOTP, consumed during enableTOTP.
 * The raw secret never roundtrips through the client.
 */

const TTL_MS = 5 * 60 * 1000; // 5 minutes — enough time to scan QR and enter code

interface Pending {
	secret: string;
	expires: number;
}

const store = new Map<string, Pending>(); // userId → pending

export function storePendingTOTPSecret(userId: string, secret: string): void {
	store.set(userId, { secret, expires: Date.now() + TTL_MS });
}

/** Retrieve and remove pending secret. Returns null if expired or not found. */
export function consumePendingTOTPSecret(userId: string): string | null {
	const entry = store.get(userId);
	store.delete(userId);
	if (!entry || Date.now() > entry.expires) return null;
	return entry.secret;
}
