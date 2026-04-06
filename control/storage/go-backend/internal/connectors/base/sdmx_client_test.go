package base

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestSDMXClientBuildSeriesPath_UsesOrderedDimensionsAndQueryOptions(t *testing.T) {
	client := NewSDMXClient(SDMXConfig{
		HTTPClient:             NewClient(Config{BaseURL: "https://example.test"}),
		DataflowID:             "EXR",
		Provider:               SDMXProviderECB,
		DimensionOrder:         []string{"FREQ", "CURRENCY", "CURRENCY_DENOM", "EXR_TYPE", "EXR_SUFFIX"},
		DimensionAtObservation: "AllDimensions",
	})

	path, q, err := client.BuildSeriesPath(
		map[string]string{
			"CURRENCY":       "USD",
			"FREQ":           "D",
			"CURRENCY_DENOM": "EUR",
			"EXR_TYPE":       "SP00",
			"EXR_SUFFIX":     "A",
		},
		"2024-01-01",
		"2024-03-01",
	)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if path != "/data/EXR/D.USD.EUR.SP00.A" {
		t.Fatalf("unexpected path %q", path)
	}
	if got := q.Get("format"); got != "jsondata" {
		t.Fatalf("expected format=jsondata, got %q", got)
	}
	if got := q.Get("dimensionAtObservation"); got != "AllDimensions" {
		t.Fatalf("expected dimensionAtObservation, got %q", got)
	}
}

func TestSDMXClientBuildSeriesPath_FillsMissingDimensionsWithWildcards(t *testing.T) {
	client := NewSDMXClient(SDMXConfig{
		DataflowID:     "DF_TEST",
		Provider:       SDMXProviderOECD,
		DimensionOrder: []string{"A", "B", "C", "D", "E"},
	})
	path, _, err := client.BuildSeriesPath(map[string]string{"A": "X", "C": "Z"}, "", "")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if path != "/data/DF_TEST/X...Z...." {
		t.Fatalf("unexpected wildcard path %q", path)
	}
}

func TestParseSDMXJSONSingleSeries_ECBStylePayload(t *testing.T) {
	body := `{
		"dataSets":[{"series":{"0:0:0:0:0":{"observations":{"0":[1.0956,0,0,null],"1":[1.0919,0,0,null],"2":[1.0940,0,0,null]}}}}],
		"structure":{
			"dimensions":{
				"observation":[
					{"id":"TIME_PERIOD","values":[{"id":"2024-01-02"},{"id":"2024-01-03"},{"id":"2024-01-04"}]}
				]
			}
		}
	}`
	points, err := ParseSDMXJSONSingleSeries(strings.NewReader(body))
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(points) != 3 {
		t.Fatalf("expected 3 points, got %d", len(points))
	}
	if !points[0].Time.Before(points[1].Time) {
		t.Fatalf("expected ascending order")
	}
	if points[0].Value != 1.0956 || points[2].Value != 1.0940 {
		t.Fatalf("unexpected values %+v", points)
	}
}

func TestSDMXClientGetSeries_FetchesAndParses(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/data/EXR/D.USD.EUR.SP00.A" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		if got := r.URL.Query().Get("format"); got != "jsondata" {
			t.Fatalf("expected format=jsondata, got %q", got)
		}
		_, _ = w.Write([]byte(`{
			"dataSets":[{"series":{"0:0:0:0:0":{"observations":{"0":[1.1],"1":[1.2]}}}}],
			"structure":{"dimensions":{"observation":[{"id":"TIME_PERIOD","values":[{"id":"2024-01-01"},{"id":"2024-01-02"}]}]}}
		}`))
	}))
	defer server.Close()

	client := NewSDMXClient(SDMXConfig{
		HTTPClient:     NewClient(Config{BaseURL: server.URL, Timeout: 2 * time.Second}),
		DataflowID:     "EXR",
		Provider:       SDMXProviderECB,
		DimensionOrder: []string{"FREQ", "CURRENCY", "CURRENCY_DENOM", "EXR_TYPE", "EXR_SUFFIX"},
	})
	points, err := client.GetSeries(context.Background(), map[string]string{
		"FREQ":           "D",
		"CURRENCY":       "USD",
		"CURRENCY_DENOM": "EUR",
		"EXR_TYPE":       "SP00",
		"EXR_SUFFIX":     "A",
	}, "", "")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(points) != 2 {
		t.Fatalf("expected 2 points, got %d", len(points))
	}
	if points[1].Value != 1.2 {
		t.Fatalf("unexpected last value %f", points[1].Value)
	}
}
