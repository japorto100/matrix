package acled

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"tradeviewfusion/go-backend/internal/connectors/base"
	"tradeviewfusion/go-backend/internal/connectors/gct"
)

const (
	DefaultBaseURL = "https://acleddata.com/api"
	defaultLimit   = 50
	maxLimit       = 500
	defaultPath    = "/acled/read"
)

type Config struct {
	BaseURL           string
	APIToken          string
	Email             string
	AccessKey         string
	RequestTimeout    time.Duration
	MockEnabled       bool
	MockDataPath      string
	SnapshotStorePath string
}

type Query struct {
	Country      string
	Region       string
	EventType    string
	SubEventType string
	StartDate    string
	EndDate      string
	Limit        int
}

type Event struct {
	ID           string  `json:"id"`
	EventDate    string  `json:"eventDate"`
	Country      string  `json:"country"`
	Region       string  `json:"region"`
	EventType    string  `json:"eventType"`
	SubEventType string  `json:"subEventType"`
	Actor1       string  `json:"actor1"`
	Actor2       string  `json:"actor2"`
	Fatalities   int     `json:"fatalities"`
	Location     string  `json:"location"`
	Latitude     float64 `json:"latitude"`
	Longitude    float64 `json:"longitude"`
	Source       string  `json:"source"`
	Notes        string  `json:"notes"`
}

type Client struct {
	baseClient         *base.Client
	apiToken           string
	email              string
	accessKey          string
	mockEnabled        bool
	mockDataPath       string
	snapshotRecorder   func(context.Context, base.FetchSnapshot) error
	snapshotNormalizer func(context.Context, string, []byte, time.Time) error
}

func NewClient(cfg Config) *Client {
	timeout := cfg.RequestTimeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}

	baseURL := strings.TrimSpace(cfg.BaseURL)
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}

	return &Client{
		baseClient: base.NewClient(base.Config{
			BaseURL:    baseURL,
			Timeout:    timeout,
			RetryCount: 1,
		}),
		apiToken:     strings.TrimSpace(cfg.APIToken),
		email:        strings.TrimSpace(cfg.Email),
		accessKey:    strings.TrimSpace(cfg.AccessKey),
		mockEnabled:  cfg.MockEnabled,
		mockDataPath: strings.TrimSpace(cfg.MockDataPath),
		snapshotRecorder: base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
			SourceID:      "acled",
			Subdir:        "acled",
			SourceClass:   "api-snapshot",
			FetchMode:     "poll",
			StorePath:     strings.TrimSpace(cfg.SnapshotStorePath),
			DatasetName:   "acled-events",
			CadenceHint:   "hourly",
			ParserVersion: "acled-events-json-v1",
		}),
		snapshotNormalizer: base.NewLocalSnapshotNormalizer(base.LocalSnapshotRecorderConfig{
			SourceID:      "acled",
			Subdir:        "acled",
			StorePath:     strings.TrimSpace(cfg.SnapshotStorePath),
			ParserVersion: "acled-events-normalized-v1",
		}),
	}
}

func (c *Client) FetchEvents(ctx context.Context, query Query) ([]Event, error) {
	if !c.hasCredentials() {
		if c.mockEnabled {
			return c.mockEvents(query), nil
		}
		return nil, &gct.RequestError{
			Path:       defaultPath,
			StatusCode: http.StatusUnauthorized,
			Cause:      fmt.Errorf("missing acled credentials"),
		}
	}

	urlQuery := url.Values{}
	urlQuery.Set("_format", "json")
	urlQuery.Set("fields", "event_id_cnty,event_date,country,region,event_type,sub_event_type,actor1,actor2,fatalities,location,latitude,longitude,source,notes")
	urlQuery.Set("limit", strconv.Itoa(normalizeLimit(query.Limit)))

	country := strings.TrimSpace(query.Country)
	if country != "" {
		urlQuery.Set("country", country)
	}

	region := strings.TrimSpace(query.Region)
	if region != "" {
		urlQuery.Set("region", region)
	}

	eventType := strings.TrimSpace(query.EventType)
	if eventType != "" {
		urlQuery.Set("event_type", eventType)
	}

	subEventType := strings.TrimSpace(query.SubEventType)
	if subEventType != "" {
		urlQuery.Set("sub_event_type", subEventType)
	}

	startDate := strings.TrimSpace(query.StartDate)
	endDate := strings.TrimSpace(query.EndDate)
	switch {
	case startDate != "" && endDate != "":
		urlQuery.Set("event_date", fmt.Sprintf("%s|%s", startDate, endDate))
		urlQuery.Set("event_date_where", "BETWEEN")
	case startDate != "":
		urlQuery.Set("event_date", startDate)
		urlQuery.Set("event_date_where", ">=")
	case endDate != "":
		urlQuery.Set("event_date", endDate)
		urlQuery.Set("event_date_where", "<=")
	}

	if c.apiToken != "" {
		// Token auth is the preferred mode for ACLED.
	} else {
		urlQuery.Set("email", c.email)
		urlQuery.Set("key", c.accessKey)
	}

	req, err := c.baseClient.NewRequest(ctx, http.MethodGet, defaultPath, urlQuery, nil)
	if err != nil {
		return nil, fmt.Errorf("build acled request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if c.apiToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiToken)
	}

	resp, err := c.baseClient.Do(req)
	if err != nil {
		timeout := false
		var netErr net.Error
		if errors.As(err, &netErr) && netErr.Timeout() {
			timeout = true
		}
		return nil, &gct.RequestError{
			Path:    defaultPath,
			Timeout: timeout,
			Cause:   err,
		}
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode >= http.StatusBadRequest {
		return nil, &gct.RequestError{
			Path:       defaultPath,
			StatusCode: resp.StatusCode,
		}
	}

	rawBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read acled response: %w", err)
	}
	fetchedAt := time.Now().UTC()
	snapshotID := ""
	if c.snapshotRecorder != nil {
		sum := sha256.Sum256(rawBody)
		snapshotID = base.LocalSnapshotID("acled", fetchedAt, hex.EncodeToString(sum[:]))
		if recordErr := c.snapshotRecorder(ctx, base.FetchSnapshot{
			WatcherName:   "ACLED",
			SourceURL:     req.URL.String(),
			ContentType:   strings.TrimSpace(resp.Header.Get("Content-Type")),
			ContentLength: int64(len(rawBody)),
			ETag:          strings.TrimSpace(resp.Header.Get("ETag")),
			LastModified:  strings.TrimSpace(resp.Header.Get("Last-Modified")),
			SHA256Hex:     hex.EncodeToString(sum[:]),
			FetchedAt:     fetchedAt,
			Payload:       append([]byte(nil), rawBody...),
		}); recordErr != nil {
			return nil, fmt.Errorf("record acled snapshot: %w", recordErr)
		}
	}

	var payload struct {
		Data []struct {
			ID           string `json:"event_id_cnty"`
			EventDate    string `json:"event_date"`
			Country      string `json:"country"`
			Region       string `json:"region"`
			EventType    string `json:"event_type"`
			SubEventType string `json:"sub_event_type"`
			Actor1       string `json:"actor1"`
			Actor2       string `json:"actor2"`
			Fatalities   any    `json:"fatalities"`
			Location     string `json:"location"`
			Latitude     any    `json:"latitude"`
			Longitude    any    `json:"longitude"`
			Source       string `json:"source"`
			Notes        string `json:"notes"`
		} `json:"data"`
	}
	if err := json.NewDecoder(bytes.NewReader(rawBody)).Decode(&payload); err != nil {
		return nil, fmt.Errorf("decode acled response: %w", err)
	}

	events := make([]Event, 0, len(payload.Data))
	for _, item := range payload.Data {
		events = append(events, Event{
			ID:           strings.TrimSpace(item.ID),
			EventDate:    strings.TrimSpace(item.EventDate),
			Country:      strings.TrimSpace(item.Country),
			Region:       strings.TrimSpace(item.Region),
			EventType:    strings.TrimSpace(item.EventType),
			SubEventType: strings.TrimSpace(item.SubEventType),
			Actor1:       strings.TrimSpace(item.Actor1),
			Actor2:       strings.TrimSpace(item.Actor2),
			Fatalities:   parseInt(item.Fatalities),
			Location:     strings.TrimSpace(item.Location),
			Latitude:     parseFloat(item.Latitude),
			Longitude:    parseFloat(item.Longitude),
			Source:       strings.TrimSpace(item.Source),
			Notes:        strings.TrimSpace(item.Notes),
		})
	}
	if c.snapshotNormalizer != nil && snapshotID != "" {
		normalizedPayload, err := json.Marshal(struct {
			SourceID     string    `json:"sourceId"`
			NormalizedAt time.Time `json:"normalizedAt"`
			Query        Query     `json:"query"`
			Events       []Event   `json:"events"`
		}{
			SourceID:     "acled",
			NormalizedAt: fetchedAt,
			Query:        query,
			Events:       events,
		})
		if err != nil {
			return nil, fmt.Errorf("marshal acled normalized snapshot: %w", err)
		}
		if err := c.snapshotNormalizer(ctx, snapshotID, normalizedPayload, fetchedAt); err != nil {
			return nil, fmt.Errorf("normalize acled snapshot: %w", err)
		}
	}
	return events, nil
}

func (c *Client) hasCredentials() bool {
	return c.apiToken != "" || (c.email != "" && c.accessKey != "")
}

func (c *Client) mockEvents(query Query) []Event {
	if fromFile, err := c.readMockEventsFromFile(); err == nil && len(fromFile) > 0 {
		return fromFile
	}

	country := strings.TrimSpace(query.Country)
	if country == "" {
		country = "United States"
	}
	region := strings.TrimSpace(query.Region)
	if region == "" {
		region = "Americas"
	}
	eventType := strings.TrimSpace(query.EventType)
	if eventType == "" {
		eventType = "Strategic developments"
	}
	subEventType := strings.TrimSpace(query.SubEventType)
	if subEventType == "" {
		subEventType = "Policy signal"
	}
	return []Event{
		{
			ID:           "mock-acled-1",
			EventDate:    time.Now().UTC().Format("2006-01-02"),
			Country:      country,
			Region:       region,
			EventType:    eventType,
			SubEventType: subEventType,
			Actor1:       "Mock Actor A",
			Actor2:       "Mock Actor B",
			Fatalities:   0,
			Location:     "Mock City",
			Latitude:     38.9072,
			Longitude:    -77.0369,
			Source:       "mock:acled",
			Notes:        "Mocked ACLED event for local live verification.",
		},
	}
}

func (c *Client) readMockEventsFromFile() ([]Event, error) {
	if c.mockDataPath == "" {
		return nil, fmt.Errorf("mock data path is empty")
	}
	raw, err := os.ReadFile(c.mockDataPath)
	if err != nil {
		return nil, fmt.Errorf("read acled mock data %s: %w", c.mockDataPath, err)
	}
	var payload struct {
		Events []Event `json:"events"`
	}
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("decode acled mock data %s: %w", c.mockDataPath, err)
	}
	if len(payload.Events) == 0 {
		return nil, fmt.Errorf("mock data contains no events")
	}
	return payload.Events, nil
}

func normalizeLimit(limit int) int {
	if limit <= 0 {
		return defaultLimit
	}
	if limit > maxLimit {
		return maxLimit
	}
	return limit
}

func parseInt(value any) int {
	switch typed := value.(type) {
	case nil:
		return 0
	case float64:
		return int(typed)
	case int:
		return typed
	case json.Number:
		n, err := typed.Int64()
		if err == nil {
			return int(n)
		}
		f, err := typed.Float64()
		if err == nil {
			return int(f)
		}
	case string:
		trimmed := strings.TrimSpace(typed)
		if trimmed == "" {
			return 0
		}
		if n, err := strconv.Atoi(trimmed); err == nil {
			return n
		}
		if f, err := strconv.ParseFloat(trimmed, 64); err == nil {
			return int(f)
		}
	}
	return 0
}

func parseFloat(value any) float64 {
	switch typed := value.(type) {
	case nil:
		return 0
	case float64:
		return typed
	case int:
		return float64(typed)
	case json.Number:
		f, err := typed.Float64()
		if err == nil {
			return f
		}
	case string:
		trimmed := strings.TrimSpace(typed)
		if trimmed == "" {
			return 0
		}
		f, err := strconv.ParseFloat(trimmed, 64)
		if err == nil {
			return f
		}
	}
	return 0
}
