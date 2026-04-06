package base

import (
	"context"
	"fmt"
	"strings"
	"time"
)

type AuthStyle string

const (
	AuthNone       AuthStyle = "none"
	AuthQueryParam AuthStyle = "query"
	AuthHeader     AuthStyle = "header"
	AuthBearer     AuthStyle = "bearer"
)

type TimeSeriesConfig struct {
	HTTPClient   *Client
	URLTemplate  string
	DateField    string
	ValueField   string
	DateFormat   string
	AuthStyle    AuthStyle
	AuthKeyName  string
	AuthKeyValue string
}

type TimeSeriesClient struct {
	httpClient *Client
	cfg        TimeSeriesConfig
}

func NewTimeSeriesClient(cfg TimeSeriesConfig) *TimeSeriesClient {
	return &TimeSeriesClient{httpClient: cfg.HTTPClient, cfg: cfg}
}

func (c *TimeSeriesClient) BuildURL(seriesID string) (string, error) {
	if c == nil {
		return "", fmt.Errorf("timeseries client unavailable")
	}
	tpl := strings.TrimSpace(c.cfg.URLTemplate)
	if tpl == "" {
		return "", fmt.Errorf("timeseries url template required")
	}
	if strings.Contains(tpl, "%s") {
		return fmt.Sprintf(tpl, urlEscapeSeriesID(seriesID)), nil
	}
	return tpl, nil
}

func (c *TimeSeriesClient) GetSeries(ctx context.Context, seriesID string, from, to time.Time) ([]SeriesPoint, error) {
	_, err := c.BuildURL(seriesID)
	if err != nil {
		return nil, err
	}
	_ = ctx
	_ = from
	_ = to
	return nil, fmt.Errorf("timeseries base scaffold: provider-specific parser not implemented")
}

func urlEscapeSeriesID(seriesID string) string {
	replacer := strings.NewReplacer(" ", "%20", "/", "%2F")
	return replacer.Replace(strings.TrimSpace(seriesID))
}
