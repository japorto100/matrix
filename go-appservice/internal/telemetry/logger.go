package telemetry

import (
	"context"
	"fmt"
	"log/slog"
	"os"

	"go.opentelemetry.io/contrib/bridges/otelslog"
	"go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc"
	"go.opentelemetry.io/otel/log/global"
	sdklog "go.opentelemetry.io/otel/sdk/log"
	"go.opentelemetry.io/otel/sdk/resource"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.opentelemetry.io/otel/trace"
)

// InitLogProvider initialises an OTLP gRPC log provider, registers it as the
// global OTel logger provider, and replaces the default slog handler with a
// fanout that writes to both stdout (JSON) and OpenObserve (OTLP).
// Call lp.Shutdown(ctx) on clean exit.
func InitLogProvider(ctx context.Context, serviceName, otlpEndpoint string) (*sdklog.LoggerProvider, error) {
	res, err := resource.New(ctx,
		resource.WithAttributes(semconv.ServiceName(serviceName)),
	)
	if err != nil {
		return nil, fmt.Errorf("telemetry: build resource: %w", err)
	}

	opts := []otlploggrpc.Option{
		otlploggrpc.WithInsecure(),
		otlploggrpc.WithEndpoint(stripScheme(otlpEndpoint)),
	}
	if hdrs := otelHeaders(); hdrs != nil {
		opts = append(opts, otlploggrpc.WithHeaders(hdrs))
	}

	exp, err := otlploggrpc.New(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("telemetry: create OTLP log exporter: %w", err)
	}

	lp := sdklog.NewLoggerProvider(
		sdklog.WithProcessor(sdklog.NewBatchProcessor(exp)),
		sdklog.WithResource(res),
	)
	global.SetLoggerProvider(lp)

	// Fan out: JSON stdout (existing) + OTel bridge (new).
	otelHandler := otelslog.NewHandler(serviceName, otelslog.WithLoggerProvider(lp))
	jsonHandler := slog.NewJSONHandler(os.Stdout, nil)
	tracedJsonHandler := &traceContextHandler{Handler: jsonHandler}
	slog.SetDefault(slog.New(&fanoutHandler{handlers: []slog.Handler{tracedJsonHandler, otelHandler}}))

	return lp, nil
}

// traceContextHandler extracts OTel trace_id and span_id from context and adds them to stdout JSON.
type traceContextHandler struct {
	slog.Handler
}

func (h *traceContextHandler) Handle(ctx context.Context, r slog.Record) error {
	if spanCtx := trace.SpanContextFromContext(ctx); spanCtx.IsValid() {
		r.AddAttrs(
			slog.String("trace_id", spanCtx.TraceID().String()),
			slog.String("span_id", spanCtx.SpanID().String()),
		)
	}
	if err := h.Handler.Handle(ctx, r); err != nil {
		return fmt.Errorf("handle slog record with trace context: %w", err)
	}
	return nil
}

// fanoutHandler forwards every slog record to multiple slog.Handlers.
type fanoutHandler struct {
	handlers []slog.Handler
}

func (f *fanoutHandler) Enabled(ctx context.Context, level slog.Level) bool {
	for _, h := range f.handlers {
		if h.Enabled(ctx, level) {
			return true
		}
	}
	return false
}

func (f *fanoutHandler) Handle(ctx context.Context, r slog.Record) error {
	for _, h := range f.handlers {
		if h.Enabled(ctx, r.Level) {
			_ = h.Handle(ctx, r.Clone())
		}
	}
	return nil
}

func (f *fanoutHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	hs := make([]slog.Handler, len(f.handlers))
	for i, h := range f.handlers {
		hs[i] = h.WithAttrs(attrs)
	}
	return &fanoutHandler{handlers: hs}
}

func (f *fanoutHandler) WithGroup(name string) slog.Handler {
	hs := make([]slog.Handler, len(f.handlers))
	for i, h := range f.handlers {
		hs[i] = h.WithGroup(name)
	}
	return &fanoutHandler{handlers: hs}
}
