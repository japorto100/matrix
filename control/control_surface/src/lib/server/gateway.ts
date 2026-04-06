// Single source of truth for Go Gateway base URL.
// All Next.js server-side code must import from here instead of hardcoding the URL.
/** Returns the Go Gateway base URL from env, with fallback for local dev. */
export function getGatewayBaseURL(): string {
	return (process.env.GO_GATEWAY_BASE_URL ?? "http://127.0.0.1:9060").trim();
}
