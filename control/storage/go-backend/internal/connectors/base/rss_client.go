package base

import (
	"context"
	"fmt"
	"strings"
	"time"
)

type RSSItem struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	URL         string    `json:"url"`
	PublishedAt time.Time `json:"publishedAt,omitzero"`
	Source      string    `json:"source,omitempty"`
}

type RSSConfig struct {
	Name string
	URL  string
}

type RSSClient struct {
	cfg RSSConfig
}

func NewRSSClient(cfg RSSConfig) *RSSClient {
	return &RSSClient{cfg: cfg}
}

func (c *RSSClient) Fetch(ctx context.Context) ([]RSSItem, error) {
	if c == nil {
		return nil, fmt.Errorf("rss client unavailable")
	}
	if strings.TrimSpace(c.cfg.URL) == "" {
		return nil, fmt.Errorf("rss url required")
	}
	_ = ctx
	return nil, fmt.Errorf("rss base scaffold: parser not implemented")
}
