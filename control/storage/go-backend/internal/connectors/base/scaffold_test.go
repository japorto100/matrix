package base

import (
	"context"
	"net/http"
	"testing"
	"time"
)

// ── B1: MaxIdleConnsPerHost ──────────────────────────────────────────────────

func TestNewClient_MaxIdleConnsPerHost_ExplicitConfig(t *testing.T) {
	transport := &http.Transport{}
	_ = NewClient(Config{
		BaseURL:             "http://example.com",
		MaxIdleConnsPerHost: 50,
		Transport:           transport,
	})
	if transport.MaxIdleConnsPerHost != 50 {
		t.Fatalf("expected MaxIdleConnsPerHost=50, got %d", transport.MaxIdleConnsPerHost)
	}
}

func TestNewClient_MaxIdleConnsPerHost_EnvFallback(t *testing.T) {
	t.Setenv("CONN_MAX_IDLE_CONNS_PER_HOST", "15")
	transport := &http.Transport{}
	_ = NewClient(Config{
		BaseURL:   "http://example.com",
		Transport: transport,
	})
	if transport.MaxIdleConnsPerHost != 15 {
		t.Fatalf("expected MaxIdleConnsPerHost=15 from env, got %d", transport.MaxIdleConnsPerHost)
	}
}

func TestNewClient_MaxIdleConnsPerHost_ExplicitWinsOverEnv(t *testing.T) {
	// Per-connector override (50) must win over env fallback (15).
	t.Setenv("CONN_MAX_IDLE_CONNS_PER_HOST", "15")
	transport := &http.Transport{}
	_ = NewClient(Config{
		BaseURL:             "http://example.com",
		MaxIdleConnsPerHost: 50,
		Transport:           transport,
	})
	if transport.MaxIdleConnsPerHost != 50 {
		t.Fatalf("expected explicit override=50 to win over env=15, got %d", transport.MaxIdleConnsPerHost)
	}
}

func TestComputeOracleDisagreement(t *testing.T) {
	oracle := &OracleQuote{
		Symbol:    "BTC/USD",
		Price:     101,
		Timestamp: time.Now().UTC(),
		Source:    "chainlink",
		Verified:  true,
	}
	got := ComputeOracleDisagreement("BTC/USD", "finnhub", 100, oracle)
	if got == nil {
		t.Fatal("expected disagreement")
	}
	if got.BpsGap <= 0 {
		t.Fatalf("expected positive bps gap, got %f", got.BpsGap)
	}
}

func TestRequestErrorError(t *testing.T) {
	err := (&RequestError{
		Provider:   "finnhub",
		StatusCode: 429,
		Message:    "rate limited",
	}).Error()
	if err == "" {
		t.Fatal("expected non-empty error string")
	}
}

func TestCapabilitiesHelpers(t *testing.T) {
	caps := Capabilities{Quote: true, Depth: true, Streaming: true, OrderStatus: true}
	if !caps.SupportsRealtime() {
		t.Fatal("expected realtime support")
	}
	if caps.SupportsAnalyticsSeed() {
		t.Fatal("did not expect analytics seed support")
	}
	if !caps.Market().Depth {
		t.Fatal("expected depth support in market capabilities")
	}
	if !caps.Stream().Live {
		t.Fatal("expected live stream support")
	}
	if !caps.Order().Status {
		t.Fatal("expected order status support")
	}
}

func TestClassifyHTTPStatusAndErrors(t *testing.T) {
	if got := ClassifyHTTPStatus(http.StatusTooManyRequests); got != ErrorClassQuota {
		t.Fatalf("expected quota class, got %q", got)
	}
	if got := ClassifyError(context.DeadlineExceeded, nil); got != ErrorClassTimeout {
		t.Fatalf("expected timeout class, got %q", got)
	}
	if got := ClassifyError(&RequestError{StatusCode: 401, Message: "bad auth"}, nil); got != ErrorClassAuth {
		t.Fatalf("expected auth class, got %q", got)
	}
	if got := ClassifyError(&RequestError{Message: "decode failed: unexpected field x"}, nil); got != ErrorClassSchemaDrift {
		t.Fatalf("expected schema drift class, got %q", got)
	}
	if !IsRetryableClass(ErrorClassUpstream5xx) {
		t.Fatal("expected 5xx to be retryable")
	}
	if IsRetryableClass(ErrorClassAuth) {
		t.Fatal("did not expect auth to be retryable")
	}
}

func TestRetryDecisionRespectsRetryAfter(t *testing.T) {
	resp, err := http.NewRequest(http.MethodGet, "https://example.com", nil)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	_ = resp

	response := &http.Response{
		StatusCode: http.StatusTooManyRequests,
		Header:     make(http.Header),
	}
	response.Header.Set("Retry-After", "5")

	decision := RetryDecision(http.MethodGet, response, nil, time.Unix(1700000000, 0))
	if !decision.ShouldRetry {
		t.Fatal("expected retry decision to allow retry")
	}
	if decision.Delay != 5*time.Second {
		t.Fatalf("expected 5s delay, got %s", decision.Delay)
	}
}

func TestCredentialSetRedacted(t *testing.T) {
	creds := CredentialSet{
		Key:        "abc12345",
		Secret:     "secret-9876",
		Passphrase: "passphrase",
		ClientID:   "client-1",
		SubAccount: "desk-a",
	}

	if creds.IsEmpty() {
		t.Fatal("expected credentials to be non-empty")
	}
	if !creds.HasSecrets() {
		t.Fatal("expected credentials to report secrets")
	}

	redacted := creds.Redacted()
	if redacted.Key == creds.Key || redacted.Secret == creds.Secret || redacted.Passphrase == creds.Passphrase {
		t.Fatalf("expected secrets to be redacted, got %+v", redacted)
	}
	if redacted.ClientID != "client-1" || redacted.SubAccount != "desk-a" {
		t.Fatalf("expected non-secret fields preserved, got %+v", redacted)
	}
}

func TestCredentialStoreHelpers(t *testing.T) {
	store := CredentialStore{
		" FINNHUB ": {Key: "demo-key"},
		"binance":   {Key: "bin-key", Secret: "bin-secret"},
		"empty":     {},
	}

	normalized := store.Normalized()
	if len(normalized) != 2 {
		t.Fatalf("expected 2 normalized entries, got %+v", normalized)
	}
	if _, ok := normalized["finnhub"]; !ok {
		t.Fatalf("expected normalized finnhub entry, got %+v", normalized)
	}

	creds, ok := normalized.Get("BINANCE")
	if !ok || creds.Secret != "bin-secret" {
		t.Fatalf("expected binance credentials, got %+v", creds)
	}

	redacted := normalized.Redacted()
	if redacted["binance"].Secret == "bin-secret" {
		t.Fatalf("expected redacted secret, got %+v", redacted["binance"])
	}
}
