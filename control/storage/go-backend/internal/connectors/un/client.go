// Package un provides UN SDMX connector. Phase 14a.2.
// Ref: REFERENCE_SOURCE_STATUS.md, UN Stats API (unstats.un.org)
// Symbol format: UN_<DATAFLOW>__<KEY> where KEY preserves SDMX dimension separators.
// The gateway's currency code normalization uppercases the canonical symbol before parsing.
package un

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/thrasher-corp/gocryptotrader/currency"
	"github.com/thrasher-corp/gocryptotrader/exchanges/asset"
	"tradeviewfusion/go-backend/internal/connectors/base"
	"tradeviewfusion/go-backend/internal/connectors/gct"
)

const DefaultBaseURL = "https://data.un.org/ws/rest"

const (
	seriesPrefix = "UN_"
)

type Config struct {
	BaseURL        string
	RequestTimeout time.Duration
}

type Client struct {
	httpClient  *base.Client
	unSDMX      *base.SDMXClient
	defaultPath string
}

func NewClient(cfg Config) *Client {
	baseURL := strings.TrimSpace(cfg.BaseURL)
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}
	timeout := cfg.RequestTimeout
	if timeout <= 0 {
		timeout = 6 * time.Second
	}
	httpClient := base.NewClient(base.Config{
		BaseURL:    baseURL,
		Timeout:    timeout,
		RetryCount: 1,
	})
	return &Client{
		httpClient: httpClient,
		unSDMX: base.NewSDMXClient(base.SDMXConfig{
			HTTPClient:             httpClient,
			DataflowID:             "UN",
			Provider:               base.SDMXProviderUN,
			DimensionOrder:         []string{"REF_AREA", "INDICATOR", "FREQ"},
			Format:                 "jsondata",
			DimensionAtObservation: "TIME_PERIOD",
			DataPathPrefix:         "data",
		}),
		defaultPath: "data",
	}
}

func (c *Client) GetTicker(ctx context.Context, pair currency.Pair, assetType asset.Item) (gct.Ticker, error) {
	series, err := c.GetSeries(ctx, pair, assetType, 1)
	if err != nil {
		return gct.Ticker{}, err
	}
	if len(series) == 0 {
		return gct.Ticker{}, &gct.RequestError{
			Path:       c.defaultPath,
			StatusCode: http.StatusNotFound,
			Cause:      fmt.Errorf("no observations"),
		}
	}
	value := series[0].Value
	lastUpdated := series[0].Timestamp
	if lastUpdated <= 0 {
		lastUpdated = time.Now().Unix()
	}
	canonical := normalizeCanonical(pair.Base.String())
	return gct.Ticker{
		Pair:        currency.NewPair(currency.NewCode(canonical), currency.NewCode("USD")),
		Currency:    canonical,
		LastUpdated: lastUpdated,
		Last:        value,
		Bid:         value,
		Ask:         value,
		High:        value,
		Low:         value,
		Volume:      0,
	}, nil
}

func (c *Client) GetSeries(ctx context.Context, pair currency.Pair, assetType asset.Item, limit int) ([]gct.SeriesPoint, error) {
	if !gct.IsSemanticAssetType(assetType, "macro") {
		return nil, &gct.RequestError{
			Path:       c.defaultPath,
			StatusCode: http.StatusBadRequest,
			Cause:      fmt.Errorf("unsupported un assetType"),
		}
	}
	if c == nil || c.httpClient == nil {
		return nil, fmt.Errorf("un client unavailable")
	}
	if limit <= 0 {
		limit = 1
	}
	if limit > 1000 {
		limit = 1000
	}

	dataflow, key, canonical, err := parseSeriesSymbol(pair.Base.String())
	if err != nil {
		return nil, &gct.RequestError{
			Path:       c.defaultPath,
			StatusCode: http.StatusBadRequest,
			Cause:      err,
		}
	}

	path := strings.TrimRight(c.defaultPath, "/") + "/" + url.PathEscape(dataflow)
	if key != "" {
		path += "/" + key
	}
	query := url.Values{}
	query.Set("format", "json")
	query.Set("dimensionAtObservation", "TIME_PERIOD")

	req, err := c.httpClient.NewRequest(ctx, http.MethodGet, path, query, nil)
	if err != nil {
		return nil, fmt.Errorf("build un request: %w", err)
	}
	req.Header.Set("Accept", "text/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, &gct.RequestError{Path: c.defaultPath, Cause: err}
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode >= http.StatusBadRequest {
		return nil, &gct.RequestError{
			Path:       c.defaultPath,
			StatusCode: resp.StatusCode,
			Cause:      fmt.Errorf("un data request failed"),
		}
	}

	points, err := base.ParseSDMXJSONSingleSeries(resp.Body)
	if err != nil {
		return nil, mapSDMXError(c.defaultPath, err)
	}
	converted := make([]gct.SeriesPoint, 0, len(points))
	for _, point := range points {
		ts := point.Time.UTC().Unix()
		if ts <= 0 {
			continue
		}
		converted = append(converted, gct.SeriesPoint{
			Timestamp: ts,
			Value:     point.Value,
		})
	}
	if len(converted) == 0 {
		return nil, &gct.RequestError{
			Path:       c.defaultPath,
			StatusCode: http.StatusNotFound,
			Cause:      fmt.Errorf("no parsable observations for %s", canonical),
		}
	}
	ensureLatestFirst(converted)
	if len(converted) > limit {
		converted = converted[:limit]
	}
	return converted, nil
}

func mapSDMXError(path string, err error) error {
	var reqErr *base.RequestError
	if errors.As(err, &reqErr) {
		return &gct.RequestError{
			Path:       path,
			StatusCode: reqErr.StatusCode,
			Cause:      fmt.Errorf("%s", reqErr.Error()),
		}
	}
	return &gct.RequestError{Path: path, Cause: err}
}

func parseSeriesSymbol(raw string) (string, string, string, error) {
	canonical := normalizeCanonical(raw)
	if canonical == "" {
		return "", "", "", fmt.Errorf("invalid UN symbol")
	}
	payload := strings.TrimPrefix(canonical, seriesPrefix)
	parts := strings.SplitN(payload, "__", 2)
	if len(parts) != 2 {
		return "", "", "", fmt.Errorf("invalid UN symbol: expected UN_<DATAFLOW>__<KEY>")
	}
	dataflow := strings.TrimSpace(parts[0])
	key := strings.TrimSpace(parts[1])
	if dataflow == "" || key == "" {
		return "", "", "", fmt.Errorf("invalid UN symbol: expected UN_<DATAFLOW>__<KEY>")
	}
	return dataflow, key, canonical, nil
}

func normalizeCanonical(raw string) string {
	value := strings.TrimSpace(raw)
	if value == "" {
		return ""
	}
	upper := strings.ToUpper(value)
	if strings.HasPrefix(upper, seriesPrefix) {
		return seriesPrefix + value[len(seriesPrefix):]
	}
	return seriesPrefix + value
}

func ensureLatestFirst(points []gct.SeriesPoint) {
	if len(points) < 2 {
		return
	}
	if points[0].Timestamp >= points[len(points)-1].Timestamp {
		return
	}
	for i, j := 0, len(points)-1; i < j; i, j = i+1, j-1 {
		points[i], points[j] = points[j], points[i]
	}
}
