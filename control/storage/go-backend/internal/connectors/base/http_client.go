package base

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/failsafe-go/failsafe-go/circuitbreaker"
	"github.com/failsafe-go/failsafe-go/failsafehttp"
	"github.com/failsafe-go/failsafe-go/retrypolicy"
	"golang.org/x/time/rate"
)

type Client struct {
	baseURL    string
	timeout    time.Duration
	retryCount int
	httpClient *http.Client
	limiter    *rate.Limiter
}

func NewClient(cfg Config) *Client {
	baseURL := strings.TrimRight(strings.TrimSpace(cfg.BaseURL), "/")

	timeout := cfg.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}

	retryCount := cfg.RetryCount
	retryCount = max(retryCount, 0)

	transport := cfg.Transport
	if transport == nil {
		if defaultTransport, ok := http.DefaultTransport.(*http.Transport); ok {
			transport = defaultTransport.Clone()
		} else {
			transport = http.DefaultTransport
		}
	}
	// Per-connector override wins; env var is the global fallback.
	// Set CONN_MAX_IDLE_CONNS_PER_HOST in go-backend/.env to tune globally (e.g. 10).
	// High-velocity connectors (Yahoo, GCT) set MaxIdleConnsPerHost: 50 explicitly.
	if cfg.MaxIdleConnsPerHost == 0 {
		if v := os.Getenv("CONN_MAX_IDLE_CONNS_PER_HOST"); v != "" {
			if n, err := strconv.Atoi(v); err == nil && n > 0 {
				cfg.MaxIdleConnsPerHost = n
			}
		}
	}
	if cfg.MaxIdleConnsPerHost > 0 {
		if t, ok := transport.(*http.Transport); ok {
			t.MaxIdleConnsPerHost = cfg.MaxIdleConnsPerHost
		}
	}

	retryPolicy := failsafehttp.NewRetryPolicyBuilder().
		WithMaxRetries(retryCount).
		WithBackoff(100*time.Millisecond, 1500*time.Millisecond).
		AbortIf(func(resp *http.Response, err error) bool {
			if resp != nil && resp.Request != nil && !isIdempotentMethod(resp.Request.Method) {
				return true
			}
			return false
		}).
		Build()

	cb := circuitbreaker.NewBuilder[*http.Response]().
		HandleIf(func(resp *http.Response, err error) bool {
			if err != nil {
				return true
			}
			if resp != nil && (resp.StatusCode == 429 || resp.StatusCode >= 500) {
				return true
			}
			return false
		}).
		WithFailureThreshold(3).
		WithDelay(10 * time.Second).
		Build()

	roundTripper := failsafehttp.NewRoundTripper(transport, retryPolicy, cb)

	return &Client{
		baseURL:    baseURL,
		timeout:    timeout,
		retryCount: retryCount,
		httpClient: &http.Client{Timeout: timeout, Transport: roundTripper},
		limiter:    newRateLimiter(cfg.RateLimitPerSecond, cfg.RateLimitBurst),
	}
}

func (c *Client) BaseURL() string {
	if c == nil {
		return ""
	}
	return c.baseURL
}

func (c *Client) Timeout() time.Duration {
	if c == nil {
		return 0
	}
	return c.timeout
}

func (c *Client) HTTP() *http.Client {
	if c == nil {
		return nil
	}
	return c.httpClient
}

func (c *Client) NewRequest(ctx context.Context, method, path string, query url.Values, body io.Reader) (*http.Request, error) {
	if c == nil {
		return nil, fmt.Errorf("base client unavailable")
	}
	target, err := c.buildURL(path, query)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, method, target, body)
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	return req, nil
}

func (c *Client) buildURL(path string, query url.Values) (string, error) {
	if c == nil {
		return "", fmt.Errorf("base client unavailable")
	}

	if strings.HasPrefix(path, "http://") || strings.HasPrefix(path, "https://") {
		endpoint, err := url.Parse(path)
		if err != nil {
			return "", fmt.Errorf("build url: %w", err)
		}
		if len(query) > 0 {
			endpoint.RawQuery = query.Encode()
		}
		return endpoint.String(), nil
	}

	baseURL := c.baseURL
	if baseURL == "" {
		return "", fmt.Errorf("base url required")
	}
	endpoint, err := url.Parse(baseURL)
	if err != nil {
		return "", fmt.Errorf("parse base url: %w", err)
	}
	joined, err := endpoint.Parse(path)
	if err != nil {
		return "", fmt.Errorf("build request url: %w", err)
	}
	if len(query) > 0 {
		joined.RawQuery = query.Encode()
	}
	return joined.String(), nil
}

func (c *Client) Do(req *http.Request) (*http.Response, error) {
	if c == nil {
		return nil, fmt.Errorf("base client unavailable")
	}
	if req == nil {
		return nil, fmt.Errorf("request required")
	}

	if waitErr := waitForRateLimiter(req.Context(), c.limiter); waitErr != nil {
		return nil, waitErr
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		var exceededErr retrypolicy.ExceededError
		if errors.As(err, &exceededErr) {
			if lastResp, ok := exceededErr.LastResult.(*http.Response); ok && lastResp != nil {
				return lastResp, exceededErr.LastError
			}
		}
		return nil, fmt.Errorf("perform http request: %w", err)
	}
	return resp, nil
}
