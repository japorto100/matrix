// Package un provides UN SDMX connector and UN Security Council Consolidated List sanctions watcher.
// Phase 14a.2 (SDMX), 14d.2 (Sanctions).
// Ref: REFERENCE_SOURCE_STATUS.md, https://scsanctions.un.org/resources/xml/en/consolidated.xml
package un

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

const DefaultSanctionsURL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

// UNConsolidatedList is a minimal struct for UN Security Council Consolidated List XML.
// Structure: root has INDIVIDUALS and ENTITIES; each has records with DATAID (reference number).
// Root element name may vary (CONSOLIDATED_LIST, LIST, etc.); decoder matches child elements.
type UNConsolidatedList struct {
	XMLName     xml.Name      `xml:"CONSOLIDATED_LIST"`
	Individuals UNIndividuals `xml:"INDIVIDUALS"`
	Entities    UNEntities    `xml:"ENTITIES"`
}

type UNIndividuals struct {
	Individual []UNRecord `xml:"INDIVIDUAL"`
}

type UNEntities struct {
	Entity []UNRecord `xml:"ENTITY"`
}

type UNRecord struct {
	DataID     string `xml:"DATAID"`
	FirstName  string `xml:"FIRST_NAME"`
	SecondName string `xml:"SECOND_NAME"`
	ThirdName  string `xml:"THIRD_NAME"`
	FourthName string `xml:"FOURTH_NAME"`
	// Entity may use FIRST_NAME or NAME
	UNType string `xml:"UN_LIST_TYPE"`
	Name   string `xml:"NAME"`
}

func NewSanctionsWatcher(storePath string, httpClient *http.Client) *base.DiffWatcher {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 90 * time.Second}
	}
	url := strings.TrimSpace(getEnv("UN_SANCTIONS_URL", DefaultSanctionsURL))
	recorder := base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
		SourceID:      "un-sanctions",
		Subdir:        "un",
		SourceClass:   "file-snapshot",
		FetchMode:     "conditional-poll",
		StorePath:     storePath,
		DatasetName:   "un-sanctions",
		CadenceHint:   "daily",
		ParserVersion: "un-sanctions-xml-v1",
	})
	return base.NewDiffWatcher(base.DiffWatcherConfig{
		Name:       "UN_SANCTIONS",
		URL:        url,
		Schedule:   "0 9 * * *",
		Format:     "xml",
		IDField:    "reference_number",
		StorePath:  storePath,
		ParseFunc:  parseUNSanctionsXML,
		OnFetched:  recorder,
		HTTPClient: httpClient,
	})
}

func parseUNSanctionsXML(r io.Reader) ([]map[string]any, error) {
	var list UNConsolidatedList
	if err := xml.NewDecoder(r).Decode(&list); err != nil {
		return nil, fmt.Errorf("decode un sanctions xml: %w", err)
	}
	result := make([]map[string]any, 0, len(list.Individuals.Individual)+len(list.Entities.Entity))
	for _, e := range list.Individuals.Individual {
		name := strings.TrimSpace(e.FirstName + " " + e.SecondName + " " + e.ThirdName + " " + e.FourthName)
		if name == "" {
			name = e.DataID
		}
		result = append(result, map[string]any{
			"reference_number": e.DataID,
			"name":             name,
			"type":             "individual",
			"list":             "UN",
		})
	}
	for _, e := range list.Entities.Entity {
		name := strings.TrimSpace(e.Name)
		if name == "" {
			name = strings.TrimSpace(e.FirstName)
		}
		if name == "" {
			name = e.DataID
		}
		result = append(result, map[string]any{
			"reference_number": e.DataID,
			"name":             name,
			"type":             "entity",
			"list":             "UN",
		})
	}
	return result, nil
}

func getEnv(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}
