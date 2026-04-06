package base

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"
)

type SDMXProvider string

const (
	SDMXProviderIMF       SDMXProvider = "imf"
	SDMXProviderOECD      SDMXProvider = "oecd"
	SDMXProviderECB       SDMXProvider = "ecb"
	SDMXProviderWorldBank SDMXProvider = "worldbank"
	SDMXProviderUN        SDMXProvider = "un"
	SDMXProviderADB       SDMXProvider = "adb"
)

type SDMXConfig struct {
	HTTPClient              *Client
	DataflowID              string
	Provider                SDMXProvider
	DimensionOrder          []string
	Format                  string
	DimensionAtObservation  string
	DataPathPrefix          string
	DataflowPathPrefix      string
	StructurePathPrefix     string
	PathSuffix              string // e.g. "OECD" for OECD REST API agency segment
	AdditionalDefaultParams map[string]string
}

type SDMXClient struct {
	httpClient             *Client
	dataflowID             string
	provider               SDMXProvider
	dimensionOrder         []string
	format                 string
	dimensionAtObservation string
	dataPathPrefix         string
	dataflowPathPrefix     string
	structurePathPrefix    string
	pathSuffix             string
	defaultParams          map[string]string
}

func NewSDMXClient(cfg SDMXConfig) *SDMXClient {
	format := strings.TrimSpace(cfg.Format)
	if format == "" {
		format = "jsondata"
	}
	dataPathPrefix := strings.TrimSpace(cfg.DataPathPrefix)
	if dataPathPrefix == "" {
		dataPathPrefix = "/data"
	}
	dataflowPathPrefix := strings.TrimSpace(cfg.DataflowPathPrefix)
	if dataflowPathPrefix == "" {
		dataflowPathPrefix = "/dataflow"
	}
	structurePathPrefix := strings.TrimSpace(cfg.StructurePathPrefix)
	if structurePathPrefix == "" {
		structurePathPrefix = "/datastructure"
	}
	defaultParams := make(map[string]string, len(cfg.AdditionalDefaultParams))
	for k, v := range cfg.AdditionalDefaultParams {
		key := strings.TrimSpace(k)
		if key == "" {
			continue
		}
		defaultParams[key] = strings.TrimSpace(v)
	}
	return &SDMXClient{
		httpClient:             cfg.HTTPClient,
		dataflowID:             strings.TrimSpace(cfg.DataflowID),
		provider:               cfg.Provider,
		dimensionOrder:         append([]string(nil), cfg.DimensionOrder...),
		format:                 format,
		dimensionAtObservation: strings.TrimSpace(cfg.DimensionAtObservation),
		dataPathPrefix:         dataPathPrefix,
		dataflowPathPrefix:     dataflowPathPrefix,
		structurePathPrefix:    structurePathPrefix,
		pathSuffix:             strings.TrimSpace(cfg.PathSuffix),
		defaultParams:          defaultParams,
	}
}

func (c *SDMXClient) BuildSeriesPath(dimensions map[string]string, startPeriod, endPeriod string) (string, url.Values, error) {
	return c.BuildSeriesPathWithOptions(dimensions, startPeriod, endPeriod, nil)
}

func (c *SDMXClient) BuildSeriesPathWithOptions(dimensions map[string]string, startPeriod, endPeriod string, extra map[string]string) (string, url.Values, error) {
	if c == nil {
		return "", nil, fmt.Errorf("sdmx client unavailable")
	}
	if c.dataflowID == "" {
		return "", nil, fmt.Errorf("sdmx dataflow id required")
	}
	key, err := c.BuildSeriesKey(dimensions)
	if err != nil {
		return "", nil, err
	}
	q := url.Values{}
	if strings.TrimSpace(startPeriod) != "" {
		q.Set("startPeriod", strings.TrimSpace(startPeriod))
	}
	if strings.TrimSpace(endPeriod) != "" {
		q.Set("endPeriod", strings.TrimSpace(endPeriod))
	}
	if c.format != "" {
		q.Set("format", c.format)
	}
	if c.dimensionAtObservation != "" {
		q.Set("dimensionAtObservation", c.dimensionAtObservation)
	}
	for k, v := range c.defaultParams {
		if _, exists := q[k]; !exists && strings.TrimSpace(v) != "" {
			q.Set(k, v)
		}
	}
	for k, v := range extra {
		extraKey := strings.TrimSpace(k)
		if extraKey == "" {
			continue
		}
		q.Set(extraKey, strings.TrimSpace(v))
	}
	path := strings.TrimRight(c.dataPathPrefix, "/") + "/" + url.PathEscape(c.dataflowID)
	if key != "" {
		path += "/" + key
	}
	if c.pathSuffix != "" {
		path += "/" + url.PathEscape(c.pathSuffix)
	}
	return path, q, nil
}

func (c *SDMXClient) BuildSeriesKey(dimensions map[string]string) (string, error) {
	if c == nil {
		return "", fmt.Errorf("sdmx client unavailable")
	}
	if len(dimensions) == 0 {
		return "", nil
	}
	if len(c.dimensionOrder) == 0 {
		return "", fmt.Errorf("sdmx dimension order required")
	}
	normalized := make(map[string]string, len(dimensions))
	for k, v := range dimensions {
		key := strings.ToUpper(strings.TrimSpace(k))
		if key == "" {
			continue
		}
		normalized[key] = strings.TrimSpace(v)
	}
	parts := make([]string, 0, len(c.dimensionOrder))
	for _, rawDim := range c.dimensionOrder {
		dim := strings.ToUpper(strings.TrimSpace(rawDim))
		if dim == "" {
			continue
		}
		value := strings.TrimSpace(normalized[dim])
		if value == "" {
			value = "."
		}
		parts = append(parts, value)
	}
	return strings.Join(parts, "."), nil
}

func (c *SDMXClient) BuildDataflowPath() (string, url.Values, error) {
	if c == nil {
		return "", nil, fmt.Errorf("sdmx client unavailable")
	}
	prefix := strings.TrimRight(c.dataflowPathPrefix, "/")
	if c.dataflowID == "" {
		return prefix, nil, nil
	}
	return prefix + "/" + url.PathEscape(c.dataflowID), nil, nil
}

func (c *SDMXClient) BuildDataStructurePath() (string, url.Values, error) {
	if c == nil {
		return "", nil, fmt.Errorf("sdmx client unavailable")
	}
	prefix := strings.TrimRight(c.structurePathPrefix, "/")
	if c.dataflowID == "" {
		return prefix, nil, nil
	}
	return prefix + "/" + url.PathEscape(c.dataflowID), nil, nil
}

func (c *SDMXClient) GetSeries(ctx context.Context, dimensions map[string]string, startPeriod, endPeriod string) ([]SeriesPoint, error) {
	if c == nil {
		return nil, fmt.Errorf("sdmx client unavailable")
	}
	if c.httpClient == nil {
		return nil, fmt.Errorf("sdmx http client unavailable")
	}
	path, q, err := c.BuildSeriesPath(dimensions, startPeriod, endPeriod)
	if err != nil {
		return nil, err
	}
	req, err := c.httpClient.NewRequest(ctx, http.MethodGet, path, q, nil)
	if err != nil {
		return nil, fmt.Errorf("build sdmx request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, &RequestError{Provider: string(c.provider), Message: err.Error()}
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode >= http.StatusBadRequest {
		return nil, &RequestError{Provider: string(c.provider), StatusCode: resp.StatusCode, Message: "sdmx request failed"}
	}
	points, err := ParseSDMXJSONSingleSeries(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("parse sdmx json: %w", err)
	}
	return points, nil
}

func ParseSDMXJSONSingleSeries(r interface{ Read([]byte) (int, error) }) ([]SeriesPoint, error) {
	var payload struct {
		DataSets []struct {
			Series map[string]struct {
				Observations map[string][]json.RawMessage `json:"observations"`
			} `json:"series"`
		} `json:"dataSets"`
		Structure struct {
			Dimensions struct {
				Observation []struct {
					ID     string `json:"id"`
					Values []struct {
						ID string `json:"id"`
					} `json:"values"`
				} `json:"observation"`
			} `json:"dimensions"`
		} `json:"structure"`
	}
	if err := json.NewDecoder(r).Decode(&payload); err != nil {
		return nil, fmt.Errorf("decode sdmx json payload: %w", err)
	}
	if len(payload.DataSets) == 0 || len(payload.DataSets[0].Series) == 0 {
		return nil, fmt.Errorf("missing sdmx dataset series")
	}
	obsDims := payload.Structure.Dimensions.Observation
	if len(obsDims) == 0 {
		return nil, fmt.Errorf("missing sdmx observation dimensions")
	}
	timeDimIndex := 0
	for i, dim := range obsDims {
		if strings.Contains(strings.ToUpper(dim.ID), "TIME") {
			timeDimIndex = i
			break
		}
	}
	var observations map[string][]json.RawMessage
	for _, series := range payload.DataSets[0].Series {
		observations = series.Observations
		break
	}
	if len(observations) == 0 {
		return nil, fmt.Errorf("missing sdmx observations")
	}
	points := make([]SeriesPoint, 0, len(observations))
	for key, values := range observations {
		ts, ok := parseSDMXObservationTimestamp(obsDims, timeDimIndex, key)
		if !ok {
			continue
		}
		value, ok := parseSDMXObservationValue(values)
		if !ok {
			continue
		}
		points = append(points, SeriesPoint{Time: ts, Value: value})
	}
	if len(points) == 0 {
		return nil, fmt.Errorf("no parsable sdmx observations")
	}
	sort.Slice(points, func(i, j int) bool { return points[i].Time.Before(points[j].Time) })
	return points, nil
}

func parseSDMXObservationTimestamp(obsDims []struct {
	ID     string `json:"id"`
	Values []struct {
		ID string `json:"id"`
	} `json:"values"`
}, timeDimIndex int, obsKey string) (time.Time, bool) {
	if timeDimIndex < 0 || timeDimIndex >= len(obsDims) {
		return time.Time{}, false
	}
	segments := strings.Split(strings.TrimSpace(obsKey), ":")
	if timeDimIndex >= len(segments) {
		return time.Time{}, false
	}
	idx, err := strconv.Atoi(strings.TrimSpace(segments[timeDimIndex]))
	if err != nil || idx < 0 || idx >= len(obsDims[timeDimIndex].Values) {
		return time.Time{}, false
	}
	raw := strings.TrimSpace(obsDims[timeDimIndex].Values[idx].ID)
	if raw == "" {
		return time.Time{}, false
	}
	for _, format := range []string{
		DateFormatISODate,
		DateFormatYYYYMM,
		DateFormatYYYY,
		DateFormatQuarterCode,
	} {
		if ts, err := ParseSeriesTime(format, raw); err == nil {
			return ts.UTC(), true
		}
	}
	if ts, err := time.Parse(time.RFC3339, raw); err == nil {
		return ts.UTC(), true
	}
	if len(raw) == 7 && raw[4] == '-' && raw[5] == 'Q' {
		if ts, err := ParseSeriesTime(DateFormatQuarterCode, strings.Replace(raw, "-", "", 1)); err == nil {
			return ts.UTC(), true
		}
	}
	return time.Time{}, false
}

func parseSDMXObservationValue(values []json.RawMessage) (float64, bool) {
	if len(values) == 0 {
		return 0, false
	}
	var f float64
	if err := json.Unmarshal(values[0], &f); err == nil {
		return f, true
	}
	var s string
	if err := json.Unmarshal(values[0], &s); err == nil {
		if strings.TrimSpace(s) == "" {
			return 0, false
		}
		f, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
		if err == nil {
			return f, true
		}
	}
	return 0, false
}
