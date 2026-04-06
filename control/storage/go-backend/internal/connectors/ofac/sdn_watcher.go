// Package ofac provides OFAC SDN list diff watcher. Phase 14d.1.
// Ref: REFERENCE_SOURCE_STATUS.md, https://www.treasury.gov/ofac/downloads
package ofac

import (
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"tradeviewfusion/go-backend/internal/connectors/base"
)

const (
	DefaultSDNURL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
)

func sdnURL() string {
	if v := strings.TrimSpace(os.Getenv("OFAC_SDN_URL")); v != "" {
		return v
	}
	return DefaultSDNURL
}

// SDNList is a minimal struct for OFAC SDN XML.
type SDNList struct {
	XMLName xml.Name `xml:"sdnList"`
	Entries []struct {
		UID      string `xml:"uid"`
		LastName string `xml:"lastName"`
		SDNType  string `xml:"sdnType"`
	} `xml:"sdnEntry"`
}

func NewSDNWatcher(storePath string, httpClient *http.Client) *base.DiffWatcher {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 60 * time.Second}
	}
	recorder := base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
		SourceID:      "ofac",
		Subdir:        "ofac",
		SourceClass:   "file-snapshot",
		FetchMode:     "conditional-poll",
		StorePath:     storePath,
		DatasetName:   "ofac-sdn",
		CadenceHint:   "daily",
		ParserVersion: "ofac-sdn-xml-v1",
	})
	return base.NewDiffWatcher(base.DiffWatcherConfig{
		Name:       "OFAC_SDN",
		URL:        sdnURL(),
		Schedule:   "0 8 * * *",
		Format:     "xml",
		IDField:    "uid",
		StorePath:  storePath,
		ParseFunc:  parseSDNXML,
		OnFetched:  recorder,
		HTTPClient: httpClient,
	})
}

func parseSDNXML(r io.Reader) ([]map[string]any, error) {
	var list SDNList
	if err := xml.NewDecoder(r).Decode(&list); err != nil {
		return nil, fmt.Errorf("decode ofac sdn xml: %w", err)
	}
	result := make([]map[string]any, 0, len(list.Entries))
	for _, e := range list.Entries {
		result = append(result, map[string]any{
			"uid":      e.UID,
			"lastName": e.LastName,
			"sdnType":  e.SDNType,
		})
	}
	return result, nil
}
