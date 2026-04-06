// Package cftc provides CFTC Commitment of Traders (COT) bulk fetcher. Phase 14c.1.
// Ref: REFERENCE_SOURCE_STATUS.md, https://www.cftc.gov/MarketReports/CommitmentsofTraders/
package cftc

import (
	"encoding/csv"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"tradeviewfusion/go-backend/internal/connectors/base"
)

const (
	DefaultCOTURL = "https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip"
)

func NewCOTFetcher(storePath string, httpClient *http.Client) *base.BulkFetcher {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 30 * time.Second}
	}
	url := strings.TrimSpace(os.Getenv("CFTC_COT_URL"))
	if url == "" {
		url = DefaultCOTURL
	}
	recorder := base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
		SourceID:      "cftc-cot",
		Subdir:        "cftc",
		SourceClass:   "file-snapshot",
		FetchMode:     "conditional-poll",
		StorePath:     storePath,
		DatasetName:   "cftc-cot",
		CadenceHint:   "weekly",
		ParserVersion: "cftc-cot-csv-zip-v1",
	})
	return base.NewBulkFetcher(base.BulkConfig{
		Name:       "CFTC_COT",
		URL:        url,
		Schedule:   "0 6 * * 1", // weekly Monday 6am
		Format:     base.BulkFormatCSVZIP,
		ParseFunc:  parseCOTCSV,
		OnFetched:  recorder,
		HTTPClient: httpClient,
	})
}

func parseCOTCSV(r io.Reader) ([]any, error) {
	reader := csv.NewReader(r)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("read cftc cot csv: %w", err)
	}
	result := make([]any, 0, len(records))
	for _, row := range records {
		rowCopy := make([]string, len(row))
		copy(rowCopy, row)
		result = append(result, rowCopy)
	}
	return result, nil
}
