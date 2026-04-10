package telemetry

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

// InitMeterProvider initialises an OTLP gRPC meter provider and registers it
// as the global OTel meter provider. Call mp.Shutdown(ctx) on clean exit.
func InitMeterProvider(ctx context.Context, serviceName, otlpEndpoint string) (*metric.MeterProvider, error) {
	res, err := resource.New(ctx,
		resource.WithAttributes(semconv.ServiceName(serviceName)),
	)
	if err != nil {
		return nil, fmt.Errorf("telemetry: build resource: %w", err)
	}

	opts := []otlpmetricgrpc.Option{
		otlpmetricgrpc.WithInsecure(),
		otlpmetricgrpc.WithEndpoint(stripScheme(otlpEndpoint)),
	}
	if hdrs := otelHeaders(); hdrs != nil {
		opts = append(opts, otlpmetricgrpc.WithHeaders(hdrs))
	}

	exp, err := otlpmetricgrpc.New(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("telemetry: create OTLP metric exporter: %w", err)
	}

	mp := metric.NewMeterProvider(
		metric.WithReader(metric.NewPeriodicReader(exp)),
		metric.WithResource(res),
	)
	otel.SetMeterProvider(mp)
	return mp, nil
}
