package news

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"tradeviewfusion/go-backend/internal/connectors/base"
	marketServices "tradeviewfusion/go-backend/internal/services/market"
)

const DefaultGDELTBaseURL = "https://api.gdeltproject.org/api/v2/doc/doc"

type GDELTClientConfig struct {
	BaseURL           string
	RequestTimeout    time.Duration
	RequestRetries    int
	SnapshotStorePath string
}

type GDELTClient struct {
	baseURL            string
	requestRetries     int
	baseClient         *base.Client
	snapshotRecorder   func(context.Context, base.FetchSnapshot) error
	snapshotNormalizer func(context.Context, string, []byte, time.Time) error
}

func NewGDELTClient(cfg GDELTClientConfig) *GDELTClient {
	timeout := cfg.RequestTimeout
	if timeout <= 0 {
		timeout = 4 * time.Second
	}
	baseURL := strings.TrimSpace(cfg.BaseURL)
	if baseURL == "" {
		baseURL = DefaultGDELTBaseURL
	}
	retries := cfg.RequestRetries
	retries = max(retries, 0)
	return &GDELTClient{
		baseURL:        baseURL,
		requestRetries: retries,
		baseClient: base.NewClient(base.Config{
			Timeout:    timeout,
			RetryCount: 0,
		}),
		snapshotRecorder: base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
			SourceID:      "gdelt-news",
			Subdir:        "gdelt-news",
			SourceClass:   "api-snapshot",
			FetchMode:     "poll",
			StorePath:     strings.TrimSpace(cfg.SnapshotStorePath),
			DatasetName:   "gdelt-news",
			CadenceHint:   "hourly",
			ParserVersion: "gdelt-news-json-v1",
		}),
		snapshotNormalizer: base.NewLocalSnapshotNormalizer(base.LocalSnapshotRecorderConfig{
			SourceID:      "gdelt-news",
			Subdir:        "gdelt-news",
			StorePath:     strings.TrimSpace(cfg.SnapshotStorePath),
			ParserVersion: "gdelt-news-normalized-v1",
		}),
	}
}

func (c *GDELTClient) Fetch(ctx context.Context, symbol string, limit int) ([]marketServices.Headline, error) {
	if limit <= 0 {
		limit = 20
	}
	if limit > 250 {
		limit = 250
	}

	queryTerm := "finance OR markets"
	symbol = strings.TrimSpace(symbol)
	if symbol != "" {
		queryTerm = symbol + " AND (finance OR markets)"
	}

	parsedURL, err := url.Parse(c.baseURL)
	if err != nil {
		return nil, fmt.Errorf("parse gdelt base url %q: %w", c.baseURL, err)
	}
	query := parsedURL.Query()
	query.Set("query", queryTerm)
	query.Set("mode", "artlist")
	query.Set("format", "json")
	query.Set("maxrecords", strconv.Itoa(limit))
	query.Set("sort", "DateDesc")
	parsedURL.RawQuery = query.Encode()

	var payload struct {
		Articles []struct {
			Title string `json:"title"`
			URL   string `json:"url"`
			Seen  string `json:"seendate"`
		} `json:"articles"`
	}
	var fetchedAt time.Time
	snapshotID := ""

	attempts := c.requestRetries + 1
	for attempt := 1; attempt <= attempts; attempt++ {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, parsedURL.String(), nil)
		if err != nil {
			return nil, fmt.Errorf("build gdelt news request for %s: %w", symbol, err)
		}
		req.Header.Set("Accept", "application/json")
		req.Header.Set("User-Agent", "tradeview-fusion-go-backend/1.0")

		resp, err := c.baseClient.Do(req)
		if err != nil {
			if attempt < attempts {
				if !sleepWithContext(ctx, backoffDuration(attempt)) {
					return nil, fmt.Errorf("gdelt news retry backoff canceled after request failure for %s: %w", symbol, ctx.Err())
				}
				continue
			}
			return nil, fmt.Errorf("request gdelt news for %s: %w", symbol, err)
		}

		if resp.StatusCode >= http.StatusInternalServerError {
			_ = resp.Body.Close()
			if attempt < attempts {
				if !sleepWithContext(ctx, backoffDuration(attempt)) {
					return nil, fmt.Errorf("gdelt news retry backoff canceled after server error for %s: %w", symbol, ctx.Err())
				}
				continue
			}
			return nil, nil
		}
		if resp.StatusCode >= http.StatusBadRequest {
			_ = resp.Body.Close()
			return nil, nil
		}

		rawBody, readErr := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		if readErr != nil {
			if attempt < attempts {
				if !sleepWithContext(ctx, backoffDuration(attempt)) {
					return nil, fmt.Errorf("gdelt news retry backoff canceled after read failure for %s: %w", symbol, ctx.Err())
				}
				continue
			}
			return nil, fmt.Errorf("read gdelt news response for %s: %w", symbol, readErr)
		}

		fetchedAt = time.Now().UTC()
		if c.snapshotRecorder != nil {
			sum := sha256.Sum256(rawBody)
			snapshotID = base.LocalSnapshotID("gdelt-news", fetchedAt, hex.EncodeToString(sum[:]))
			if recordErr := c.snapshotRecorder(ctx, base.FetchSnapshot{
				WatcherName:   "GDELT_NEWS",
				SourceURL:     parsedURL.String(),
				ContentType:   strings.TrimSpace(resp.Header.Get("Content-Type")),
				ContentLength: int64(len(rawBody)),
				ETag:          strings.TrimSpace(resp.Header.Get("ETag")),
				LastModified:  strings.TrimSpace(resp.Header.Get("Last-Modified")),
				SHA256Hex:     hex.EncodeToString(sum[:]),
				FetchedAt:     fetchedAt,
				Payload:       append([]byte(nil), rawBody...),
			}); recordErr != nil {
				if attempt < attempts {
					if !sleepWithContext(ctx, backoffDuration(attempt)) {
						return nil, fmt.Errorf("gdelt snapshot retry backoff canceled for %s: %w", symbol, ctx.Err())
					}
					continue
				}
				return nil, fmt.Errorf("record gdelt news snapshot for %s: %w", symbol, recordErr)
			}
		}

		if err := json.NewDecoder(bytes.NewReader(rawBody)).Decode(&payload); err != nil {
			if attempt < attempts {
				if !sleepWithContext(ctx, backoffDuration(attempt)) {
					return nil, fmt.Errorf("gdelt decode retry backoff canceled for %s: %w", symbol, ctx.Err())
				}
				continue
			}
			return nil, fmt.Errorf("decode gdelt news response for %s: %w", symbol, err)
		}
		break
	}

	items := make([]marketServices.Headline, 0, len(payload.Articles))
	for _, article := range payload.Articles {
		publishedAt := time.Now().UTC()
		if parsedSeen, err := time.Parse("20060102T150405Z", strings.TrimSpace(article.Seen)); err == nil {
			publishedAt = parsedSeen.UTC()
		}
		items = append(items, marketServices.Headline{
			Title:       strings.TrimSpace(article.Title),
			URL:         strings.TrimSpace(article.URL),
			Source:      "gdelt",
			PublishedAt: publishedAt,
		})
	}
	if c.snapshotNormalizer != nil && snapshotID != "" {
		normalizedPayload, err := json.Marshal(struct {
			SourceID     string                    `json:"sourceId"`
			NormalizedAt time.Time                 `json:"normalizedAt"`
			QuerySymbol  string                    `json:"querySymbol"`
			Limit        int                       `json:"limit"`
			Items        []marketServices.Headline `json:"items"`
		}{
			SourceID:     "gdelt-news",
			NormalizedAt: fetchedAt,
			QuerySymbol:  symbol,
			Limit:        limit,
			Items:        items,
		})
		if err != nil {
			return nil, fmt.Errorf("marshal gdelt normalized snapshot for %s: %w", symbol, err)
		}
		if err := c.snapshotNormalizer(ctx, snapshotID, normalizedPayload, fetchedAt); err != nil {
			return nil, fmt.Errorf("normalize gdelt snapshot for %s: %w", symbol, err)
		}
	}
	return items, nil
}
