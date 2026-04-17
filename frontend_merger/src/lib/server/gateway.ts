// Single source of truth for Go Gateway base URL.
// All Next.js server-side code must import from here instead of hardcoding the URL.
//
// NOTE (2026-04-08, exec-15 Slice 7 Phase H):
// - matrix go-appservice default runs on :8090 (go-appservice/.env.development)
// - the tradeview-fusion main project uses :9060 — DO NOT use that here
// - control-ui BFF routes proxy to :8090 which then forwards to Python agent :8094
//   for /api/v1/control/* (via ControlProxyHandler).

/** Returns the Go Appservice base URL from env, with matrix-correct fallback. */
export function getGatewayBaseURL(): string {
	return (process.env.GO_GATEWAY_BASE_URL ?? "http://127.0.0.1:8090").trim();
}
