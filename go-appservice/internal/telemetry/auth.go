package telemetry

import (
	"encoding/base64"
	"os"
	"strings"
)

// stripScheme removes any http:// or https:// prefix from an OTLP endpoint so
// the gRPC exporter always receives a plain host:port address.
// Python OTel SDK requires the http:// prefix; Go's gRPC exporter rejects it.
// By normalising here we tolerate either format in the env var.
func stripScheme(endpoint string) string {
	endpoint = strings.TrimPrefix(endpoint, "https://")
	endpoint = strings.TrimPrefix(endpoint, "http://")
	return endpoint
}

// otelHeaders returns gRPC metadata headers for OpenObserve auth.
// Returns nil if no user is configured (auth skipped).
func otelHeaders() map[string]string {
	user := os.Getenv("OPENOBSERVE_USER")
	if user == "" {
		return nil
	}
	pass := os.Getenv("OPENOBSERVE_PASSWORD")
	token := base64.StdEncoding.EncodeToString([]byte(user + ":" + pass))
	org := os.Getenv("OPENOBSERVE_ORG")
	if org == "" {
		org = "default"
	}
	return map[string]string{
		"Authorization": "Basic " + token,
		"organization":  org,
	}
}
