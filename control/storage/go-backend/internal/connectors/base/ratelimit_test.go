package base

import (
	"context"
	"testing"
	"time"
)

func TestNewRateLimiterNilWhenDisabled(t *testing.T) {
	if limiter := newRateLimiter(0, 0); limiter != nil {
		t.Fatal("expected nil limiter when rate limit disabled")
	}
}

func TestWaitForRateLimiterHonorsContextCancellation(t *testing.T) {
	limiter := newRateLimiter(1, 1)
	if limiter == nil {
		t.Fatal("expected limiter")
	}
	if err := waitForRateLimiter(context.Background(), limiter); err != nil {
		t.Fatalf("expected first wait to pass immediately: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Millisecond)
	defer cancel()
	if err := waitForRateLimiter(ctx, limiter); err == nil {
		t.Fatal("expected canceled wait")
	}
}
