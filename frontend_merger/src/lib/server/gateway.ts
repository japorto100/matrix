// Single source of truth for Go Gateway base URL.
// All Next.js server-side code must import from here instead of hardcoding the URL.
//
// NOTE (2026-04-22):
// - go-appservice runs a single HTTP listener on MATRIX_APPSERVICE_PORT (29318
//   by default). The same mux handles /_matrix/* (homeserver → appservice
//   handshake, HSToken-gated) and /api/v1/* (BFF routes, X-Actor-User-Id-gated).
// - Historical split (gateway :8090 + appservice :29318) has been consolidated;
//   the old :8090 literal has been removed from env defaults.
// - control-ui BFF routes proxy to :29318/api/v1/control/* which then forwards
//   to Python agent :8094 (via ControlProxyHandler inside go-appservice).

/** Returns the Go Appservice base URL from env, with matrix-correct fallback. */
export function getGatewayBaseURL(): string {
	return (process.env.GO_GATEWAY_BASE_URL ?? "http://127.0.0.1:29318").trim();
}
