// Go Gateway base URL — single source of truth for all BFF API routes.
// Default: Port 8090 (unser Go Appservice, nicht 9060 wie im Hauptprojekt).
export function getGatewayBaseURL(): string {
	return (process.env.GO_GATEWAY_BASE_URL ?? "http://127.0.0.1:8090").trim();
}
