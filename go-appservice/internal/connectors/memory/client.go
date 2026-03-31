// Package memory provides an HTTP client for the Python memory service (port 8093).
// Simplified from Hauptprojekt: pure HTTP, no gRPC/IPC dual-transport.
package memory

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const DefaultBaseURL = "http://127.0.0.1:8093"

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

// ── Request / Response Types ─────────────────────────────────────────────────

type KGSeedRequest struct {
	Force bool `json:"force"`
}

type KGQueryRequest struct {
	Query      string         `json:"query"`
	Parameters map[string]any `json:"parameters,omitempty"`
}

type KGNodesResponse struct {
	OK    bool             `json:"ok"`
	Nodes []map[string]any `json:"nodes"`
	Total int              `json:"total"`
}

type KGSyncResponse struct {
	OK       bool           `json:"ok"`
	Snapshot map[string]any `json:"snapshot"`
	Checksum string         `json:"checksum"`
	SyncedAt string         `json:"synced_at"`
}

type EpisodeCreateRequest struct {
	SessionID  string   `json:"session_id"`
	AgentRole  string   `json:"agent_role"`
	InputJSON  string   `json:"input_json"`
	OutputJSON string   `json:"output_json"`
	ToolsUsed  []string `json:"tools_used,omitempty"`
}

type VectorSearchRequest struct {
	Query          string         `json:"query"`
	NResults       int            `json:"n_results,omitempty"`
	FilterMetadata map[string]any `json:"filter_metadata,omitempty"`
}

type VectorSearchResult struct {
	ID       string         `json:"id"`
	Text     string         `json:"text"`
	Distance float64        `json:"distance"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// ── HTTP Methods ─────────────────────────────────────────────────────────────

func (c *Client) postJSON(ctx context.Context, path string, payload any) (int, []byte, error) {
	body, err := json.Marshal(payload)
	if err != nil {
		return 0, nil, fmt.Errorf("memory marshal %s: %w", path, err)
	}
	url := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return 0, nil, fmt.Errorf("memory POST %s: %w", path, err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return 0, nil, fmt.Errorf("memory POST %s: %w", path, err)
	}
	defer func() { _ = resp.Body.Close() }()
	respBody, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, respBody, nil
}

func (c *Client) get(ctx context.Context, path string) (int, []byte, error) {
	url := c.baseURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, nil, fmt.Errorf("memory GET %s: %w", path, err)
	}
	req.Header.Set("Accept", "application/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return 0, nil, fmt.Errorf("memory GET %s: %w", path, err)
	}
	defer func() { _ = resp.Body.Close() }()
	respBody, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, respBody, nil
}

// ── Public API ───────────────────────────────────────────────────────────────

func (c *Client) PostKGSeed(ctx context.Context, req KGSeedRequest) (int, []byte, error) {
	return c.postJSON(ctx, "/api/v1/kg/seed", req)
}

func (c *Client) PostKGQuery(ctx context.Context, req KGQueryRequest) (int, []byte, error) {
	return c.postJSON(ctx, "/api/v1/kg/query", req)
}

func (c *Client) GetKGNodes(ctx context.Context, nodeType string) (int, []byte, error) {
	path := "/api/v1/kg/nodes"
	if nodeType != "" {
		path += "?type=" + nodeType
	}
	return c.get(ctx, path)
}

func (c *Client) GetKGSync(ctx context.Context) (int, []byte, error) {
	return c.get(ctx, "/api/v1/kg/sync")
}

func (c *Client) PostEpisode(ctx context.Context, req EpisodeCreateRequest) (int, []byte, error) {
	return c.postJSON(ctx, "/api/v1/episode", req)
}

func (c *Client) GetEpisodes(ctx context.Context, role string, limit int) (int, []byte, error) {
	path := fmt.Sprintf("/api/v1/episodes?role=%s&limit=%d", role, limit)
	return c.get(ctx, path)
}

func (c *Client) PostSearch(ctx context.Context, req VectorSearchRequest) (int, []byte, error) {
	if req.NResults <= 0 {
		req.NResults = 5
	}
	return c.postJSON(ctx, "/api/v1/search", req)
}

func (c *Client) GetHealth(ctx context.Context) (int, []byte, error) {
	return c.get(ctx, "/health")
}
