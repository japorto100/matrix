// Package scheduler — harness_client.go wires the Phase-C A/B-experiment
// scorer backfill worker (exec-scheduler §8.1, exec-harness §4g.4) to the
// Python endpoint POST /internal/harness/backfill.
//
// The Python endpoint polls agent.ab_experiments for rows where
// harness_fitness_score is NULL AND finished_at IS NOT NULL, then calls
// agent.harness.scorer.score_session(thread_id) for each. The scorer
// dispatches a fire-and-forget UPDATE into agent.ab_experiments via
// backfill_ab_experiment_fitness.
//
// Without this worker running on a schedule, the ab_experiments column
// stays NULL and Phase-C A/B analysis has no quality signal.
package scheduler

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

// HarnessBackfillHTTPClient is a minimal HTTP client that POSTs to the
// Python backfill endpoint. Default base URL is
// http://localhost:8088/internal/harness/backfill (matrix agent-service
// port) — override via constructor or env AGENT_SERVICE_URL.
type HarnessBackfillHTTPClient struct {
	BaseURL string
	Client  *http.Client
}

// NewHarnessBackfillHTTPClient constructs the HTTP client. Pass "" to
// read AGENT_SERVICE_URL from the environment; falls back to the
// localhost default when neither is provided.
func NewHarnessBackfillHTTPClient(baseURL string) *HarnessBackfillHTTPClient {
	if baseURL == "" {
		if env := os.Getenv("AGENT_SERVICE_URL"); env != "" {
			baseURL = env
		} else {
			baseURL = "http://localhost:8088"
		}
	}
	return &HarnessBackfillHTTPClient{
		BaseURL: baseURL,
		Client: &http.Client{
			// Backfill can score many sessions per call; generous timeout
			// but not unbounded. Workers are idle 14 of 15 minutes so
			// there's no contention pressure.
			Timeout: 5 * time.Minute,
		},
	}
}

// Backfill implements HarnessBackfillClient.
func (c *HarnessBackfillHTTPClient) Backfill(ctx context.Context) (int, error) {
	url := c.BaseURL + "/internal/harness/backfill"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		return 0, fmt.Errorf("new request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.Client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("POST %s: %w", url, err)
	}
	defer func() { _ = resp.Body.Close() }()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 300 {
		return 0, fmt.Errorf("harness backfill returned %d: %s",
			resp.StatusCode, string(body))
	}

	// Response shape: {"scored": N, "skipped": M}
	var out struct {
		Scored  int `json:"scored"`
		Skipped int `json:"skipped"`
	}
	if jsonErr := json.Unmarshal(body, &out); jsonErr != nil {
		// Not fatal — endpoint may return different shape during rollout.
		return 0, nil
	}
	return out.Scored, nil
}
