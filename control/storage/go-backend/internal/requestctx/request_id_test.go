package requestctx

import (
	"context"
	"testing"
)

func TestWithRequestIDRoundTrip(t *testing.T) {
	base := context.Background()
	ctx := WithRequestID(base, "req-123")

	if got := RequestID(ctx); got != "req-123" {
		t.Fatalf("expected request id req-123, got %q", got)
	}
}

func TestRequestIDMissingReturnsEmptyString(t *testing.T) {
	if got := RequestID(context.Background()); got != "" {
		t.Fatalf("expected empty request id, got %q", got)
	}
}
