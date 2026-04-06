package base

import (
	"fmt"
	"net/http"
	"time"
)

type Config struct {
	BaseURL             string
	Timeout             time.Duration
	RetryCount          int
	RateLimitPerSecond  float64
	RateLimitBurst      int
	Transport           http.RoundTripper
	MaxIdleConnsPerHost int // 0 = Go default (2). High-velocity sources: 50, moderate: 10.
}

type Pair struct {
	Base  string `json:"base"`
	Quote string `json:"quote"`
}

type Ticker struct {
	Symbol    string    `json:"symbol"`
	Price     float64   `json:"price"`
	Timestamp time.Time `json:"timestamp"`
	Source    string    `json:"source,omitempty"`
}

type SeriesPoint struct {
	Time  time.Time `json:"time"`
	Value float64   `json:"value"`
}

type RequestError struct {
	Provider   string `json:"provider,omitempty"`
	StatusCode int    `json:"statusCode,omitempty"`
	Body       string `json:"body,omitempty"`
	Message    string `json:"message"`
}

func (e *RequestError) Error() string {
	if e == nil {
		return "request error"
	}
	if e.Provider != "" && e.StatusCode > 0 {
		return fmt.Sprintf("%s request failed (%d): %s", e.Provider, e.StatusCode, e.Message)
	}
	if e.Provider != "" {
		return fmt.Sprintf("%s request failed: %s", e.Provider, e.Message)
	}
	if e.StatusCode > 0 {
		return fmt.Sprintf("request failed (%d): %s", e.StatusCode, e.Message)
	}
	if e.Message != "" {
		return e.Message
	}
	return "request error"
}
