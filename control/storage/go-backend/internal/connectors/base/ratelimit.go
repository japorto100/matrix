package base

import (
	"context"
	"fmt"

	"golang.org/x/time/rate"
)

func newRateLimiter(ratePerSecond float64, burst int) *rate.Limiter {
	if ratePerSecond <= 0 {
		return nil
	}
	if burst <= 0 {
		burst = max(1, int(ratePerSecond))
	}
	return rate.NewLimiter(rate.Limit(ratePerSecond), burst)
}

func waitForRateLimiter(ctx context.Context, limiter *rate.Limiter) error {
	if limiter == nil {
		return nil
	}
	if err := limiter.Wait(ctx); err != nil {
		return fmt.Errorf("wait for rate limiter token: %w", err)
	}
	return nil
}
