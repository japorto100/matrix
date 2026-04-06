package requestctx

import (
	"context"
	"testing"

	baseconnectors "tradeviewfusion/go-backend/internal/connectors/base"
)

func TestWithProviderCredentialsRoundTrip(t *testing.T) {
	creds := baseconnectors.CredentialStore{
		"finnhub": {Key: "demo-key"},
		"binance": {Key: "bin-key", Secret: "bin-secret"},
	}

	ctx := WithProviderCredentials(context.Background(), creds)
	got := ProviderCredentials(ctx)
	if len(got) != 2 {
		t.Fatalf("expected 2 provider credentials, got %d", len(got))
	}

	finnhub, ok := ProviderCredential(ctx, "FINNHUB")
	if !ok || finnhub.Key != "demo-key" {
		t.Fatalf("expected finnhub credential, got %+v", finnhub)
	}
}

func TestProviderCredentialsMissingReturnsEmptyStore(t *testing.T) {
	if got := ProviderCredentials(context.Background()); len(got) != 0 {
		t.Fatalf("expected empty provider credential store, got %+v", got)
	}
}
