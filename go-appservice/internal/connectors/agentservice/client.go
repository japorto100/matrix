// Package agentservice provides an HTTP client for the Python agent service (port 8094).
// Simplified from Hauptprojekt: pure HTTP, no gRPC/IPC dual-transport.
package agentservice

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const DefaultBaseURL = "http://127.0.0.1:8094"

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(baseURL string, timeout time.Duration) *Client {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		base = DefaultBaseURL
	}
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	return &Client{
		baseURL:    base,
		httpClient: &http.Client{Timeout: timeout},
	}
}

func (c *Client) Post(ctx context.Context, path string, body []byte) (int, []byte, error) {
	if c == nil {
		return 0, nil, fmt.Errorf("agentservice client is nil")
	}
	url := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return 0, nil, fmt.Errorf("agentservice POST %s: %w", path, err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return 0, nil, fmt.Errorf("agentservice POST %s: %w", path, err)
	}
	defer func() { _ = resp.Body.Close() }()
	respBody, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, respBody, nil
}

func (c *Client) Get(ctx context.Context, path string) (int, []byte, error) {
	if c == nil {
		return 0, nil, fmt.Errorf("agentservice client is nil")
	}
	url := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, nil, fmt.Errorf("agentservice GET %s: %w", path, err)
	}
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return 0, nil, fmt.Errorf("agentservice GET %s: %w", path, err)
	}
	defer func() { _ = resp.Body.Close() }()
	respBody, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, respBody, nil
}
