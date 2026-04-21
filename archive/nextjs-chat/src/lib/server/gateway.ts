// Go Gateway base URL — single source of truth for all BFF API routes.
// Default: Port 8090 (current go-appservice runtime).
export function getGatewayBaseURL(): string {
	return (process.env.GO_GATEWAY_BASE_URL ?? "http://127.0.0.1:8090").trim();
}
