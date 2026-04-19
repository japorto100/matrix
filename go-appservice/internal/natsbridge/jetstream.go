package natsbridge

import (
	"context"
	"fmt"
	"log/slog"
	"slices"
	"strings"
	"time"

	"github.com/nats-io/nats.go"
)

// JetStream returns the underlying NATS connection's JetStream context.
// exec-scheduler Lane B: the Go scheduler publishes to
// matrix.scheduler.> subjects which must be backed by a JetStream stream
// for durability (Python subscribers may reconnect after a fire).
func (b *Bridge) JetStream() (nats.JetStreamContext, error) {
	if b == nil || b.nc == nil {
		return nil, fmt.Errorf("nats bridge not connected")
	}
	js, err := b.nc.JetStream()
	if err != nil {
		return nil, fmt.Errorf("jetstream context: %w", err)
	}
	return js, nil
}

// EnsureStream creates (or reuses) a JetStream stream named `stream`
// that persists subjects matching `subjectPrefix` + ">". Called at
// scheduler startup so Lane-C subscribers find the stream already
// provisioned. Idempotent; updating the subjects is a no-op if they
// already match.
func (b *Bridge) EnsureStream(ctx context.Context, stream, subjectPrefix string) error {
	js, jsErr := b.JetStream()
	if jsErr != nil {
		return jsErr
	}
	subjectPrefix = strings.TrimRight(subjectPrefix, ".")
	subject := subjectPrefix + ".>"
	// Check if already present; AddStream fails with "stream name already
	// in use" when configs diverge, so we do a get-then-update/add.
	existing, infoErr := js.StreamInfo(stream, nats.Context(ctx))
	if infoErr == nil && existing != nil {
		if slices.Contains(existing.Config.Subjects, subject) {
			slog.Info("jetstream: stream already configured",
				"stream", stream, "subject", subject)
			return nil
		}
		// Update existing stream to include our subject.
		cfg := existing.Config
		cfg.Subjects = mergeSubjects(cfg.Subjects, subject)
		if _, updErr := js.UpdateStream(&cfg, nats.Context(ctx)); updErr != nil {
			return fmt.Errorf("update jetstream %s: %w", stream, updErr)
		}
		slog.Info("jetstream: stream updated with new subject",
			"stream", stream, "subject", subject)
		return nil
	}
	// Create fresh.
	_, addErr := js.AddStream(&nats.StreamConfig{
		Name:      stream,
		Subjects:  []string{subject},
		Retention: nats.LimitsPolicy,
		Storage:   nats.FileStorage,
		MaxAge:    7 * 24 * time.Hour,
		// Replicas left at 1 — dev stack is single-node. Production
		// config should bump this via NATS server config or a separate
		// helper that inspects cluster size.
	}, nats.Context(ctx))
	if addErr != nil {
		return fmt.Errorf("add jetstream %s: %w", stream, addErr)
	}
	slog.Info("jetstream: stream created",
		"stream", stream, "subject", subject)
	return nil
}

func mergeSubjects(existing []string, extra string) []string {
	if slices.Contains(existing, extra) {
		return existing
	}
	return append(existing, extra)
}
