// Package base provides connector utilities. retry.go holds scaffold for future retry logic.
package base

import (
	"errors"
	"net"
	"net/http"
	"strings"
	"time"

	gctrequest "github.com/thrasher-corp/gocryptotrader/exchanges/request"
)

func isIdempotentMethod(method string) bool {
	switch strings.ToUpper(strings.TrimSpace(method)) {
	case http.MethodGet, http.MethodHead, http.MethodOptions:
		return true
	default:
		return false
	}
}

func shouldRetry(method string, resp *http.Response, err error) bool {
	if !isIdempotentMethod(method) {
		return false
	}
	if err != nil {
		var netErr net.Error
		if errors.As(err, &netErr) {
			return true
		}
		return true
	}
	if resp == nil {
		return false
	}
	if resp.StatusCode == http.StatusTooManyRequests {
		return true
	}
	return resp.StatusCode >= http.StatusInternalServerError
}

type RetryPlan struct {
	ShouldRetry bool
	Delay       time.Duration
}

func RetryDecision(method string, resp *http.Response, err error, now time.Time) RetryPlan {
	if !shouldRetry(method, resp, err) {
		return RetryPlan{}
	}

	if delay := gctrequest.RetryAfter(resp, now); delay > 0 {
		return RetryPlan{ShouldRetry: true, Delay: delay}
	}
	return RetryPlan{ShouldRetry: true, Delay: retryBackoff(0)}
}

func retryBackoff(attempt int) time.Duration {
	if attempt < 0 {
		attempt = 0
	}
	// Conservative connector-level backoff. Keep short to avoid UI stalls.
	base := 100 * time.Millisecond
	delay := min(base<<min(attempt, 4), 1500*time.Millisecond)
	return delay
}
