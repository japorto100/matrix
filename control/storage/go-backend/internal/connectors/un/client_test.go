package un

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"tradeviewfusion/go-backend/internal/connectors/gct"

	"github.com/thrasher-corp/gocryptotrader/currency"
	"github.com/thrasher-corp/gocryptotrader/exchanges/asset"
)

func TestGetSeries_FetchesAndParses(t *testing.T) {
	var gotPath string
	var gotFormat string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotFormat = r.URL.Query().Get("format")
		_, _ = w.Write([]byte(`{
			"dataSets":[{"series":{"0:0:0":{"observations":{"0":[12.5],"1":[13.75]}}}}],
			"structure":{"dimensions":{"observation":[{"id":"TIME_PERIOD","values":[{"id":"2023"},{"id":"2024"}]}]}}
		}`))
	}))
	defer server.Close()

	client := NewClient(Config{BaseURL: server.URL, RequestTimeout: 2 * time.Second})
	assetItem, _ := asset.New("macro")
	points, err := client.GetSeries(
		context.Background(),
		currency.NewPair(currency.NewCode("UN_DF_UNData_UNFCC__A.EN_ATM_PFCE.DNK.Gg_CO2"), currency.NewCode("USD")),
		assetItem,
		10,
	)
	if err != nil {
		t.Fatalf("GetSeries: %v", err)
	}
	if gotPath != "/data/DF_UNDATA_UNFCC/A.EN_ATM_PFCE.DNK.GG_CO2" {
		t.Fatalf("unexpected path %q", gotPath)
	}
	if gotFormat != "json" {
		t.Fatalf("expected format=json, got %q", gotFormat)
	}
	if len(points) != 2 {
		t.Fatalf("expected 2 points, got %d", len(points))
	}
	if points[0].Value != 13.75 {
		t.Fatalf("expected latest-first value 13.75, got %f", points[0].Value)
	}
}

func TestGetSeries_InvalidSymbolReturnsBadRequest(t *testing.T) {
	client := NewClient(Config{})
	assetItem, _ := asset.New("macro")
	_, err := client.GetSeries(
		context.Background(),
		currency.NewPair(currency.NewCode("UN_ONLYDATAFLOW"), currency.NewCode("USD")),
		assetItem,
		10,
	)
	if err == nil {
		t.Fatal("expected invalid symbol error")
	}
	var reqErr *gct.RequestError
	if !errors.As(err, &reqErr) {
		t.Fatalf("expected RequestError, got %T", err)
	}
	if reqErr.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", reqErr.StatusCode)
	}
}
