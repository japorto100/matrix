package scheduler

import (
	"context"
	"fmt"

	"matrix/go-appservice/internal/natsbridge"
)

// BridgeJetStreamProvider adapts natsbridge.Bridge to the
// JetStreamProvider interface the scheduler expects. Kept in the
// scheduler package so the natsbridge package stays ignorant of the
// scheduler's interface shape.
type BridgeJetStreamProvider struct {
	Bridge *natsbridge.Bridge
}

// JetStream returns the JetStream context as the scheduler-facing
// jsContext type. nats.JetStreamContext already implements the minimal
// Publish surface jsContext requires.
func (p *BridgeJetStreamProvider) JetStream() (jsContext, error) {
	js, err := p.Bridge.JetStream()
	if err != nil {
		return nil, fmt.Errorf("bridge jetstream: %w", err)
	}
	return js, nil
}

// EnsureStream delegates to the bridge helper.
func (p *BridgeJetStreamProvider) EnsureStream(ctx context.Context, stream, subjectPrefix string) error {
	if err := p.Bridge.EnsureStream(ctx, stream, subjectPrefix); err != nil {
		return fmt.Errorf("bridge ensure stream: %w", err)
	}
	return nil
}
