/**
 * Simple in-memory sliding-window rate limiter.
 * Suitable for single-instance Next.js (dev / small prod).
 * For multi-instance production: replace with Redis-backed limiter.
 */

interface Window {
	count: number;
	windowStart: number;
}

const windows = new Map<string, Window>();

export interface RateLimitResult {
	allowed: boolean;
	remaining: number;
	resetInMs: number;
}

export function checkRateLimit(
	key: string,
	maxRequests: number,
	windowMs: number,
): RateLimitResult {
	const now = Date.now();
	const existing = windows.get(key);

	if (!existing || now - existing.windowStart > windowMs) {
		windows.set(key, { count: 1, windowStart: now });
		return { allowed: true, remaining: maxRequests - 1, resetInMs: windowMs };
	}

	existing.count += 1;
	const resetInMs = windowMs - (now - existing.windowStart);

	if (existing.count > maxRequests) {
		return { allowed: false, remaining: 0, resetInMs };
	}

	return { allowed: true, remaining: maxRequests - existing.count, resetInMs };
}
