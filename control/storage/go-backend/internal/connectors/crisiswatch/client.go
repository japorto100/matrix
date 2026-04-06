package crisiswatch

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"tradeviewfusion/go-backend/internal/connectors/base"
)

const (
	DefaultRSSURL = "https://www.crisisgroup.org/rss-0"
	defaultUA     = "tradeview-fusion-go-backend/1.0"
)

type Config struct {
	RSSURL            string
	RequestTimeout    time.Duration
	CacheTTL          time.Duration
	PersistPath       string
	SnapshotStorePath string
}

type Item struct {
	ID          string
	Title       string
	URL         string
	Summary     string
	PublishedAt string
	Region      string
}

type Client struct {
	rssURL             string
	baseClient         *base.Client
	cacheTTL           time.Duration
	persistPath        string
	snapshotRecorder   func(context.Context, base.FetchSnapshot) error
	snapshotNormalizer func(context.Context, string, []byte, time.Time) error

	mu        sync.RWMutex
	cachedAt  time.Time
	cachedRaw []Item
}

func NewClient(cfg Config) *Client {
	rssURL := strings.TrimSpace(cfg.RSSURL)
	if rssURL == "" {
		rssURL = DefaultRSSURL
	}

	timeout := cfg.RequestTimeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}

	cacheTTL := cfg.CacheTTL
	cacheTTL = max(cacheTTL, 0)

	client := &Client{
		rssURL: rssURL,
		baseClient: base.NewClient(base.Config{
			Timeout:    timeout,
			RetryCount: 0,
		}),
		cacheTTL:    cacheTTL,
		persistPath: strings.TrimSpace(cfg.PersistPath),
		snapshotRecorder: base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
			SourceID:      "crisiswatch",
			Subdir:        "crisiswatch",
			SourceClass:   "api-snapshot",
			FetchMode:     "poll",
			StorePath:     strings.TrimSpace(cfg.SnapshotStorePath),
			DatasetName:   "crisiswatch-rss",
			CadenceHint:   "hourly",
			ParserVersion: "crisiswatch-rss-v1",
		}),
		snapshotNormalizer: base.NewLocalSnapshotNormalizer(base.LocalSnapshotRecorderConfig{
			SourceID:      "crisiswatch",
			Subdir:        "crisiswatch",
			StorePath:     strings.TrimSpace(cfg.SnapshotStorePath),
			ParserVersion: "crisiswatch-normalized-v1",
		}),
	}
	client.loadPersistedCache()
	return client
}

func (c *Client) List(ctx context.Context, limit int, region string, q string) ([]Item, error) {
	if c == nil {
		return nil, errors.New("crisiswatch client unavailable")
	}

	if cached, ok := c.cachedSnapshot(); ok && c.cacheTTL > 0 && time.Since(cached.cachedAt) <= c.cacheTTL {
		return filterItems(cached.items, limit, region, q), nil
	}

	freshItems, err := c.fetchFromUpstream(ctx)
	if err != nil {
		if cached, ok := c.cachedSnapshot(); ok {
			return filterItems(cached.items, limit, region, q), nil
		}
		return nil, err
	}

	c.storeCache(freshItems, time.Now().UTC())
	c.persistCache()
	return filterItems(freshItems, limit, region, q), nil
}

func (c *Client) fetchFromUpstream(ctx context.Context) ([]Item, error) {
	req, err := c.baseClient.NewRequest(ctx, http.MethodGet, c.rssURL, nil, nil)
	if err != nil {
		return nil, fmt.Errorf("build crisiswatch request: %w", err)
	}
	req.Header.Set("Accept", "application/rss+xml, application/xml;q=0.9, */*;q=0.8")
	req.Header.Set("User-Agent", defaultUA)

	resp, err := c.baseClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("crisiswatch request failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode >= http.StatusBadRequest {
		return nil, fmt.Errorf("crisiswatch upstream status %d", resp.StatusCode)
	}

	rawBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read crisiswatch rss: %w", err)
	}
	fetchedAt := time.Now().UTC()
	snapshotID := ""
	if c.snapshotRecorder != nil {
		sum := sha256.Sum256(rawBody)
		snapshotID = base.LocalSnapshotID("crisiswatch", fetchedAt, hex.EncodeToString(sum[:]))
		if recordErr := c.snapshotRecorder(ctx, base.FetchSnapshot{
			WatcherName:   "CRISISWATCH",
			SourceURL:     c.rssURL,
			ContentType:   strings.TrimSpace(resp.Header.Get("Content-Type")),
			ContentLength: int64(len(rawBody)),
			ETag:          strings.TrimSpace(resp.Header.Get("ETag")),
			LastModified:  strings.TrimSpace(resp.Header.Get("Last-Modified")),
			SHA256Hex:     hex.EncodeToString(sum[:]),
			FetchedAt:     fetchedAt,
			Payload:       append([]byte(nil), rawBody...),
		}); recordErr != nil {
			return nil, fmt.Errorf("record crisiswatch snapshot: %w", recordErr)
		}
	}

	var doc struct {
		Channel struct {
			Items []struct {
				GUID        string `xml:"guid"`
				Title       string `xml:"title"`
				Link        string `xml:"link"`
				Description string `xml:"description"`
				PubDate     string `xml:"pubDate"`
			} `xml:"item"`
		} `xml:"channel"`
	}
	if err := xml.NewDecoder(bytes.NewReader(rawBody)).Decode(&doc); err != nil {
		return nil, fmt.Errorf("decode crisiswatch rss: %w", err)
	}

	items := make([]Item, 0, len(doc.Channel.Items))
	for _, raw := range doc.Channel.Items {
		title := strings.TrimSpace(raw.Title)
		url := strings.TrimSpace(raw.Link)
		if title == "" || url == "" {
			continue
		}

		publishedAt := ""
		if parsed, err := parsePubDate(raw.PubDate); err == nil {
			publishedAt = parsed.Format(time.RFC3339)
		}

		summary := strings.TrimSpace(raw.Description)
		maybeRegion := inferRegion(title, summary)

		id := strings.TrimSpace(raw.GUID)
		if id == "" {
			id = url
		}

		items = append(items, Item{
			ID:          id,
			Title:       title,
			URL:         url,
			Summary:     summary,
			PublishedAt: publishedAt,
			Region:      maybeRegion,
		})
	}
	if c.snapshotNormalizer != nil && snapshotID != "" {
		normalizedPayload, err := json.Marshal(struct {
			SourceID     string    `json:"sourceId"`
			NormalizedAt time.Time `json:"normalizedAt"`
			Items        []Item    `json:"items"`
		}{
			SourceID:     "crisiswatch",
			NormalizedAt: fetchedAt,
			Items:        items,
		})
		if err != nil {
			return nil, fmt.Errorf("marshal crisiswatch normalized snapshot: %w", err)
		}
		if err := c.snapshotNormalizer(ctx, snapshotID, normalizedPayload, fetchedAt); err != nil {
			return nil, fmt.Errorf("normalize crisiswatch snapshot: %w", err)
		}
	}

	return items, nil
}

type cacheSnapshot struct {
	cachedAt time.Time
	items    []Item
}

func (c *Client) cachedSnapshot() (cacheSnapshot, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	if len(c.cachedRaw) == 0 || c.cachedAt.IsZero() {
		return cacheSnapshot{}, false
	}
	items := make([]Item, len(c.cachedRaw))
	copy(items, c.cachedRaw)
	return cacheSnapshot{
		cachedAt: c.cachedAt,
		items:    items,
	}, true
}

func (c *Client) storeCache(items []Item, cachedAt time.Time) {
	copied := make([]Item, len(items))
	copy(copied, items)

	c.mu.Lock()
	c.cachedRaw = copied
	c.cachedAt = cachedAt
	c.mu.Unlock()
}

type persistedCache struct {
	CachedAt string `json:"cachedAt"`
	Items    []Item `json:"items"`
}

func (c *Client) persistCache() {
	if c.persistPath == "" {
		return
	}
	snapshot, ok := c.cachedSnapshot()
	if !ok {
		return
	}

	payload := persistedCache{
		CachedAt: snapshot.cachedAt.UTC().Format(time.RFC3339),
		Items:    snapshot.items,
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		return
	}

	if err := os.MkdirAll(filepath.Dir(c.persistPath), 0o750); err != nil {
		return
	}

	tmpPath := c.persistPath + ".tmp"
	if err := os.WriteFile(tmpPath, raw, 0o600); err != nil {
		return
	}
	_ = os.Rename(tmpPath, c.persistPath)
}

func (c *Client) loadPersistedCache() {
	if c.persistPath == "" {
		return
	}
	raw, err := os.ReadFile(c.persistPath)
	if err != nil {
		return
	}

	var payload persistedCache
	if unmarshalErr := json.Unmarshal(raw, &payload); unmarshalErr != nil {
		return
	}
	if len(payload.Items) == 0 {
		return
	}

	cachedAt, err := time.Parse(time.RFC3339, strings.TrimSpace(payload.CachedAt))
	if err != nil {
		cachedAt = time.Now().UTC()
	}
	c.storeCache(payload.Items, cachedAt.UTC())
}

func filterItems(items []Item, limit int, region string, q string) []Item {
	normalizedRegion := strings.ToLower(strings.TrimSpace(region))
	normalizedQuery := strings.ToLower(strings.TrimSpace(q))

	result := make([]Item, 0, len(items))
	for _, item := range items {
		if normalizedRegion != "" && !strings.Contains(strings.ToLower(item.Region), normalizedRegion) {
			continue
		}
		if normalizedQuery != "" {
			searchSpace := strings.ToLower(item.Title + " " + item.Summary + " " + item.Region)
			if !strings.Contains(searchSpace, normalizedQuery) {
				continue
			}
		}
		result = append(result, item)
		if limit > 0 && len(result) >= limit {
			break
		}
	}
	return result
}

func parsePubDate(raw string) (time.Time, error) {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return time.Time{}, errors.New("empty pubDate")
	}

	layouts := []string{
		time.RFC1123Z,
		time.RFC1123,
		time.RFC3339,
		"Mon, 2 Jan 2006 15:04:05 -0700",
		"Mon, 2 Jan 2006 15:04:05 MST",
	}
	for _, layout := range layouts {
		if parsed, err := time.Parse(layout, trimmed); err == nil {
			return parsed.UTC(), nil
		}
	}
	return time.Time{}, errors.New("unsupported pubDate")
}

func inferRegion(title string, summary string) string {
	combined := strings.ToLower(title + " " + summary)
	switch {
	case strings.Contains(combined, "ukraine"), strings.Contains(combined, "russia"), strings.Contains(combined, "europe"):
		return "Europe"
	case strings.Contains(combined, "gaza"), strings.Contains(combined, "israel"), strings.Contains(combined, "iran"), strings.Contains(combined, "middle east"):
		return "Middle East"
	case strings.Contains(combined, "china"), strings.Contains(combined, "taiwan"), strings.Contains(combined, "korea"), strings.Contains(combined, "asia"):
		return "Asia"
	case strings.Contains(combined, "africa"), strings.Contains(combined, "sahel"), strings.Contains(combined, "sudan"), strings.Contains(combined, "congo"):
		return "Africa"
	case strings.Contains(combined, "latin america"), strings.Contains(combined, "colombia"), strings.Contains(combined, "haiti"):
		return "Americas"
	default:
		return ""
	}
}
