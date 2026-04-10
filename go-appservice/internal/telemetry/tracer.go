// Package telemetry provides OpenTelemetry initialisation helpers.
// When OTEL_ENABLED != "true" this package is never called and no
// tracing overhead is incurred.
package telemetry

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

// InitTracerProvider initialises an OTLP gRPC tracer provider and registers it
// as the global OTel tracer provider. The caller must call tp.Shutdown(ctx) on
// clean exit to flush pending spans.
//
// otlpEndpoint is in host:port form (e.g. "localhost:5081"), no scheme.
// Basic auth is injected when OPENOBSERVE_USER + OPENOBSERVE_PASSWORD are set.
func InitTracerProvider(ctx context.Context, serviceName, otlpEndpoint string) (*sdktrace.TracerProvider, error) {
	res, err := resource.New(ctx,
		resource.WithAttributes(semconv.ServiceName(serviceName)),
	)
	if err != nil {
		return nil, fmt.Errorf("telemetry: build resource: %w", err)
	}

	opts := []otlptracegrpc.Option{
		otlptracegrpc.WithInsecure(),
		otlptracegrpc.WithEndpoint(stripScheme(otlpEndpoint)),
	}
	if hdrs := otelHeaders(); hdrs != nil {
		opts = append(opts, otlptracegrpc.WithHeaders(hdrs))
	}

	exp, err := otlptracegrpc.New(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("telemetry: create OTLP gRPC exporter: %w", err)
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	return tp, nil
}
