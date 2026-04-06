// Package seco provides SECO (Swiss State Secretariat for Economic Affairs) sanctions watcher.
// Phase 14d.2. Runtime now prefers the official SECO XML overall list and falls back to the
// normalized OpenSanctions dataset when the official endpoint is transiently unavailable.
// Ref: REFERENCE_SOURCE_STATUS.md
package seco

import (
	"bytes"
	"encoding/json"
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
	DefaultSECOOfficialURL = "https://www.sesam.search.admin.ch/sesam-search-web/downloadXmlGesamtliste.xhtml?lang=en&action=downloadXmlGesamtlisteAction"
	DefaultSECOFallbackURL = "https://data.opensanctions.org/datasets/latest/ch_seco_sanctions/entities.json"
)

func NewSanctionsWatcher(storePath string, httpClient *http.Client) *base.DiffWatcher {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 90 * time.Second}
	}
	url := strings.TrimSpace(getEnv("SECO_SANCTIONS_URL", DefaultSECOOfficialURL))
	recorder := base.NewLocalSnapshotRecorder(base.LocalSnapshotRecorderConfig{
		SourceID:      "seco",
		Subdir:        "seco",
		SourceClass:   "file-snapshot",
		FetchMode:     "conditional-poll",
		StorePath:     storePath,
		DatasetName:   "seco-sanctions",
		CadenceHint:   "daily",
		ParserVersion: "seco-sanctions-json-xml-v1",
	})
	return base.NewDiffWatcher(base.DiffWatcherConfig{
		Name:       "SECO_SANCTIONS",
		URL:        url,
		URLs:       []string{url, DefaultSECOFallbackURL},
		Schedule:   "0 9 * * 1-5",
		Format:     "json",
		IDField:    "id",
		StorePath:  storePath,
		ParseFunc:  parseSECOSanctionsJSON,
		OnFetched:  recorder,
		HTTPClient: httpClient,
	})
}

func parseSECOSanctionsJSON(r io.Reader) ([]map[string]any, error) {
	payload, err := io.ReadAll(r)
	if err != nil {
		return nil, fmt.Errorf("read seco sanctions payload: %w", err)
	}
	trimmed := bytes.TrimSpace(payload)
	if len(trimmed) > 0 && trimmed[0] == '<' {
		return parseSECOSanctionsXML(bytes.NewReader(trimmed))
	}
	var raw any
	if err := json.NewDecoder(bytes.NewReader(trimmed)).Decode(&raw); err != nil {
		return nil, fmt.Errorf("decode seco sanctions json: %w", err)
	}
	switch v := raw.(type) {
	case []any:
		return jsonSliceToMaps(v)
	case map[string]any:
		if arr, ok := v["results"].([]any); ok {
			return jsonSliceToMaps(arr)
		}
		if arr, ok := v["entities"].([]any); ok {
			return jsonSliceToMaps(arr)
		}
		if arr, ok := v["data"].([]any); ok {
			return jsonSliceToMaps(arr)
		}
		return []map[string]any{}, nil
	default:
		return []map[string]any{}, nil
	}
}

type secoXMLList struct {
	XMLName xml.Name        `xml:"swiss-sanctions-list"`
	Targets []secoXMLTarget `xml:"target"`
}

type secoXMLTarget struct {
	SSID       string            `xml:"ssid,attr"`
	Identity   []secoXMLIdentity `xml:"identity"`
	Individual *struct{}         `xml:"individual"`
	Entity     *struct{}         `xml:"entity"`
	Object     *secoXMLObject    `xml:"object"`
}

type secoXMLIdentity struct {
	Main  bool          `xml:"main,attr"`
	Names []secoXMLName `xml:"name"`
}

type secoXMLName struct {
	Parts []secoXMLNamePart `xml:"name-part"`
}

type secoXMLNamePart struct {
	Order int    `xml:"order,attr"`
	Value string `xml:",chardata"`
}

type secoXMLObject struct {
	ObjectType string `xml:"object-type,attr"`
}

func parseSECOSanctionsXML(r io.Reader) ([]map[string]any, error) {
	var list secoXMLList
	if err := xml.NewDecoder(r).Decode(&list); err != nil {
		return nil, fmt.Errorf("decode seco sanctions xml: %w", err)
	}
	result := make([]map[string]any, 0, len(list.Targets))
	for _, target := range list.Targets {
		id := strings.TrimSpace(target.SSID)
		if id == "" {
			continue
		}
		name := secoXMLNameForTarget(target)
		if name == "" {
			name = id
		}
		result = append(result, map[string]any{
			"id":   id,
			"name": name,
			"type": secoXMLTargetType(target),
			"list": "SECO",
		})
	}
	return result, nil
}

func secoXMLNameForTarget(target secoXMLTarget) string {
	for _, identity := range target.Identity {
		if !identity.Main && len(target.Identity) > 1 {
			continue
		}
		if name := secoXMLNameFromIdentity(identity); name != "" {
			return name
		}
	}
	for _, identity := range target.Identity {
		if name := secoXMLNameFromIdentity(identity); name != "" {
			return name
		}
	}
	return ""
}

func secoXMLNameFromIdentity(identity secoXMLIdentity) string {
	for _, name := range identity.Names {
		if value := secoXMLJoinNameParts(name.Parts); value != "" {
			return value
		}
	}
	return ""
}

func secoXMLJoinNameParts(parts []secoXMLNamePart) string {
	if len(parts) == 0 {
		return ""
	}
	ordered := make([]string, len(parts))
	for i, part := range parts {
		ordered[i] = strings.TrimSpace(part.Value)
	}
	return strings.TrimSpace(strings.Join(ordered, " "))
}

func secoXMLTargetType(target secoXMLTarget) string {
	switch {
	case target.Individual != nil:
		return "individual"
	case target.Entity != nil:
		return "entity"
	case target.Object != nil:
		if v := strings.TrimSpace(target.Object.ObjectType); v != "" {
			return v
		}
		return "object"
	default:
		return "target"
	}
}

func jsonSliceToMaps(arr []any) ([]map[string]any, error) {
	result := make([]map[string]any, 0, len(arr))
	for _, item := range arr {
		if m, ok := item.(map[string]any); ok {
			if id := extractID(m); id != "" {
				result = append(result, m)
			} else {
				m["id"] = jsonMapFallbackID(m)
				result = append(result, m)
			}
		}
	}
	return result, nil
}

func extractID(m map[string]any) string {
	for _, k := range []string{"id", "Id", "ID"} {
		if v, ok := m[k]; ok {
			if s, ok := v.(string); ok && strings.TrimSpace(s) != "" {
				return s
			}
		}
	}
	return ""
}

func jsonMapFallbackID(m map[string]any) string {
	if name, ok := m["name"].(string); ok && name != "" {
		return "seco_" + name
	}
	return "seco_unknown"
}

func getEnv(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}
