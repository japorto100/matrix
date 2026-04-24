/**
 * Next.js instrumentation — runs once when the server starts.
 *
 * exec-17 #46 tier-2: OTel tracing via @vercel/otel (opt-in, OTEL_ENABLED=true).
 *
 * Only runs in the Node.js runtime (server-side). Browser-side telemetry
 * stays out of scope here — see tier-3 follow-up (#92) for RUM via a
 * BFF-proxy.
 *
 * Exporter config is picked up from standard OTEL_* env vars by
 * @vercel/otel (OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS,
 * etc). In our stack this points at otel-collector :4317, no auth on the
 * internal hop — the collector attaches basic-auth downstream to
 * OpenObserve.
 */
export async function register() {
	if (process.env.OTEL_ENABLED !== "true") return;
	if (process.env.NEXT_RUNTIME !== "nodejs") return;

	const { registerOTel } = await import("@vercel/otel");
	registerOTel({
		serviceName: process.env.OTEL_SERVICE_NAME ?? "frontend-merger-bff",
	});
}
