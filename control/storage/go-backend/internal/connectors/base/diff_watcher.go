package base

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type DiffWatcherConfig struct {
	Name       string
	URL        string
	URLs       []string
	Schedule   string
	Format     string
	IDField    string
	StorePath  string
	ParseFunc  func(io.Reader) ([]map[string]any, error)
	OnFetched  func(context.Context, FetchSnapshot) error
	NowFunc    func() time.Time
	HTTPClient *http.Client
}

type DiffResult struct {
	Added   []map[string]any `json:"added,omitempty"`
	Removed []map[string]any `json:"removed,omitempty"`
	Changed []map[string]any `json:"changed,omitempty"`
}

type FetchSnapshot struct {
	WatcherName   string
	SourceURL     string
	ContentType   string
	ContentLength int64
	ETag          string
	LastModified  string
	SHA256Hex     string
	FetchedAt     time.Time
	Payload       []byte
}

type DiffWatcher struct {
	cfg DiffWatcherConfig
}

func NewDiffWatcher(cfg DiffWatcherConfig) *DiffWatcher {
	return &DiffWatcher{cfg: cfg}
}

func (w *DiffWatcher) URL() string {
	if w == nil {
		return ""
	}
	if len(w.cfg.URLs) > 0 {
		return strings.TrimSpace(w.cfg.URLs[0])
	}
	return w.cfg.URL
}

func (w *DiffWatcher) URLs() []string {
	if w == nil {
		return nil
	}
	if len(w.cfg.URLs) > 0 {
		result := make([]string, 0, len(w.cfg.URLs))
		for _, raw := range w.cfg.URLs {
			if trimmed := strings.TrimSpace(raw); trimmed != "" {
				result = append(result, trimmed)
			}
		}
		return result
	}
	if trimmed := strings.TrimSpace(w.cfg.URL); trimmed != "" {
		return []string{trimmed}
	}
	return nil
}

func (w *DiffWatcher) HTTPClient() *http.Client {
	if w == nil {
		return nil
	}
	return w.cfg.HTTPClient
}

func (w *DiffWatcher) CheckForUpdates(ctx context.Context) (*DiffResult, error) {
	if w == nil {
		return nil, fmt.Errorf("diff watcher unavailable")
	}
	urls := w.URLs()
	if len(urls) == 0 {
		return nil, fmt.Errorf("diff watcher url required")
	}
	if w.cfg.ParseFunc == nil {
		return nil, fmt.Errorf("diff watcher parse func required")
	}
	client := w.cfg.HTTPClient
	if client == nil {
		client = http.DefaultClient
	}
	nowFunc := w.cfg.NowFunc
	if nowFunc == nil {
		nowFunc = func() time.Time { return time.Now().UTC() }
	}
	var (
		fresh   []map[string]any
		lastErr error
	)
	for _, sourceURL := range urls {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, sourceURL, nil)
		if err != nil {
			lastErr = fmt.Errorf("diff watcher request %s: %w", sourceURL, err)
			continue
		}
		req.Header.Set("Accept", "application/json, application/xml, text/csv, */*")
		resp, err := client.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("diff watcher fetch %s: %w", sourceURL, err)
			continue
		}
		if resp.StatusCode >= http.StatusBadRequest {
			_ = resp.Body.Close()
			lastErr = fmt.Errorf("diff watcher %s: %d", sourceURL, resp.StatusCode)
			continue
		}
		payload, err := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		if err != nil {
			lastErr = fmt.Errorf("diff watcher read %s: %w", sourceURL, err)
			continue
		}
		if w.cfg.OnFetched != nil {
			sum := sha256.Sum256(payload)
			recordErr := w.cfg.OnFetched(ctx, FetchSnapshot{
				WatcherName:   w.cfg.Name,
				SourceURL:     sourceURL,
				ContentType:   strings.TrimSpace(resp.Header.Get("Content-Type")),
				ContentLength: int64(len(payload)),
				ETag:          strings.TrimSpace(resp.Header.Get("ETag")),
				LastModified:  strings.TrimSpace(resp.Header.Get("Last-Modified")),
				SHA256Hex:     hex.EncodeToString(sum[:]),
				FetchedAt:     nowFunc(),
				Payload:       append([]byte(nil), payload...),
			})
			if recordErr != nil {
				lastErr = fmt.Errorf("diff watcher record %s: %w", sourceURL, recordErr)
				continue
			}
		}
		fresh, err = w.cfg.ParseFunc(bytes.NewReader(payload))
		if err != nil {
			lastErr = fmt.Errorf("diff watcher parse %s: %w", sourceURL, err)
			continue
		}
		lastErr = nil
		break
	}
	if lastErr != nil {
		return nil, lastErr
	}
	freshMap := sliceToMap(fresh, w.cfg.IDField)
	var prevMap map[string]map[string]any
	if strings.TrimSpace(w.cfg.StorePath) != "" {
		if data, err := os.ReadFile(w.cfg.StorePath); err == nil {
			var prev []map[string]any
			if json.Unmarshal(data, &prev) == nil {
				prevMap = sliceToMap(prev, w.cfg.IDField)
			}
		}
	}
	if prevMap == nil {
		prevMap = make(map[string]map[string]any)
	}
	added, removed, changed := computeDiff(prevMap, freshMap)
	if strings.TrimSpace(w.cfg.StorePath) != "" {
		dir := filepath.Dir(w.cfg.StorePath)
		if dir != "" {
			_ = os.MkdirAll(dir, 0o750)
		}
		if data, err := json.MarshalIndent(fresh, "", "  "); err == nil {
			_ = os.WriteFile(w.cfg.StorePath, data, 0o600)
		}
	}
	return &DiffResult{Added: added, Removed: removed, Changed: changed}, nil
}

func sliceToMap(items []map[string]any, idField string) map[string]map[string]any {
	result := make(map[string]map[string]any, len(items))
	for _, item := range items {
		id := ""
		if idField != "" {
			if v, ok := item[idField]; ok {
				id = fmt.Sprint(v)
			}
		}
		if id == "" {
			id = fmt.Sprintf("%v", item)
		}
		result[id] = item
	}
	return result
}

func computeDiff(prev, fresh map[string]map[string]any) (added, removed, changed []map[string]any) {
	for id, item := range fresh {
		if _, exists := prev[id]; !exists {
			added = append(added, item)
		} else if !mapsEqual(prev[id], item) {
			changed = append(changed, item)
		}
	}
	for id, item := range prev {
		if _, exists := fresh[id]; !exists {
			removed = append(removed, item)
		}
	}
	return added, removed, changed
}

func mapsEqual(a, b map[string]any) bool {
	ja, _ := json.Marshal(a)
	jb, _ := json.Marshal(b)
	return string(ja) == string(jb)
}
