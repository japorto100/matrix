package telemetry

import (
	"context"
	"log/slog"
	"os"
	"testing"
	"time"
)

// TestStripScheme verifies that http:// and https:// prefixes are removed from
// OTLP endpoints — Go gRPC exporters require bare host:port, not a URL.
func TestStripScheme(t *testing.T) {
	cases := []struct{ in, want string }{
		{"localhost:5081", "localhost:5081"},
		{"http://localhost:5081", "localhost:5081"},
		{"https://localhost:5081", "localhost:5081"},
		{"http://otel-collector:4317", "otel-collector:4317"},
	}
	for _, c := range cases {
		if got := stripScheme(c.in); got != c.want {
			t.Errorf("stripScheme(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TestOtelHeaders verifies auth header construction from env vars.
func TestOtelHeaders(t *testing.T) {
	t.Run("no env vars returns nil", func(t *testing.T) {
		t.Setenv("OPENOBSERVE_USER", "")
		if got := otelHeaders(); got != nil {
			t.Fatalf("expected nil, got %v", got)
		}
	})

	t.Run("with credentials returns auth + org headers", func(t *testing.T) {
		t.Setenv("OPENOBSERVE_USER", "admin")
		t.Setenv("OPENOBSERVE_PASSWORD", "secret")
		t.Setenv("OPENOBSERVE_ORG", "myorg")

		hdrs := otelHeaders()
		if hdrs == nil {
			t.Fatal("expected headers, got nil")
		}
		if _, ok := hdrs["Authorization"]; !ok {
			t.Error("missing Authorization header")
		}
		if got := hdrs["organization"]; got != "myorg" {
			t.Errorf("organization = %q, want %q", got, "myorg")
		}
	})

	t.Run("missing org defaults to 'default'", func(t *testing.T) {
		t.Setenv("OPENOBSERVE_USER", "admin")
		t.Setenv("OPENOBSERVE_PASSWORD", "secret")
		t.Setenv("OPENOBSERVE_ORG", "")

		hdrs := otelHeaders()
		if got := hdrs["organization"]; got != "default" {
			t.Errorf("organization = %q, want %q", got, "default")
		}
	})
}

// TestOtelHeadersAuthEncoding verifies the Basic-auth token format.
func TestOtelHeadersAuthEncoding(t *testing.T) {
	t.Setenv("OPENOBSERVE_USER", "root@example.com")
	t.Setenv("OPENOBSERVE_PASSWORD", "Complexpass#123")
	t.Setenv("OPENOBSERVE_ORG", "")
	t.Cleanup(func() {
		os.Unsetenv("OPENOBSERVE_USER")
		os.Unsetenv("OPENOBSERVE_PASSWORD")
	})

	hdrs := otelHeaders()
	auth := hdrs["Authorization"]
	if len(auth) < 7 || auth[:6] != "Basic " {
		t.Errorf("Authorization header malformed: %q", auth)
	}
	if hdrs["organization"] != "default" {
		t.Errorf("org = %q, want %q", hdrs["organization"], "default")
	}
}

// TestInitTracerProvider verifies the provider is constructed without error
// even when the OTLP endpoint is unreachable (connection is lazy).
func TestInitTracerProvider(t *testing.T) {
	t.Setenv("OPENOBSERVE_USER", "")
	ctx := context.Background()

	tp, err := InitTracerProvider(ctx, "test-svc", "localhost:19317")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tp == nil {
		t.Fatal("expected non-nil TracerProvider")
	}
	_ = tp.Shutdown(ctx)
}

// TestInitMeterProvider verifies the meter provider is constructed correctly.
func TestInitMeterProvider(t *testing.T) {
	t.Setenv("OPENOBSERVE_USER", "")
	ctx := context.Background()

	mp, err := InitMeterProvider(ctx, "test-svc", "localhost:19317")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if mp == nil {
		t.Fatal("expected non-nil MeterProvider")
	}
	_ = mp.Shutdown(ctx)
}

// TestInitLogProvider verifies the log provider is constructed and slog is replaced.
func TestInitLogProvider(t *testing.T) {
	t.Setenv("OPENOBSERVE_USER", "")
	ctx := context.Background()

	original := slog.Default()
	t.Cleanup(func() { slog.SetDefault(original) })

	lp, err := InitLogProvider(ctx, "test-svc", "localhost:19317")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if lp == nil {
		t.Fatal("expected non-nil LoggerProvider")
	}

	// slog must not panic after handler replacement.
	slog.Info("test log from InitLogProvider", "key", "value")

	_ = lp.Shutdown(ctx)
}

// TestFanoutHandler exercises all slog.Handler interface methods.
func TestFanoutHandler(t *testing.T) {
	ctx := context.Background()

	rec1 := &recordingHandler{}
	rec2 := &recordingHandler{}
	h := &fanoutHandler{handlers: []slog.Handler{rec1, rec2}}

	// Enabled: true when any child returns true.
	if !h.Enabled(ctx, slog.LevelInfo) {
		t.Error("Enabled should return true when child is enabled")
	}

	// Handle: both children must be called.
	r := slog.NewRecord(time.Now(), slog.LevelInfo, "hello fanout", 0)
	if err := h.Handle(ctx, r); err != nil {
		t.Fatalf("Handle returned error: %v", err)
	}
	if rec1.count != 1 || rec2.count != 1 {
		t.Errorf("expected each handler called once, got rec1=%d rec2=%d", rec1.count, rec2.count)
	}

	// WithAttrs: returns new handler, does not panic.
	h2 := h.WithAttrs([]slog.Attr{slog.String("k", "v")})
	if h2 == nil {
		t.Fatal("WithAttrs returned nil")
	}

	// WithGroup: returns new handler, does not panic.
	h3 := h.WithGroup("grp")
	if h3 == nil {
		t.Fatal("WithGroup returned nil")
	}

	// A disabled child should not receive Handle calls.
	disabled := &recordingHandler{disabled: true}
	hMixed := &fanoutHandler{handlers: []slog.Handler{disabled, rec1}}
	r2 := slog.NewRecord(time.Now(), slog.LevelInfo, "partial", 0)
	_ = hMixed.Handle(ctx, r2)
	if disabled.count != 0 {
		t.Error("disabled handler should not have been called")
	}
}

// recordingHandler is a minimal slog.Handler stub for testing fanoutHandler.
type recordingHandler struct {
	count    int
	disabled bool
}

func (r *recordingHandler) Enabled(_ context.Context, _ slog.Level) bool { return !r.disabled }
func (r *recordingHandler) Handle(_ context.Context, _ slog.Record) error {
	r.count++
	return nil
}
func (r *recordingHandler) WithAttrs(_ []slog.Attr) slog.Handler { return r }
func (r *recordingHandler) WithGroup(_ string) slog.Handler      { return r }
