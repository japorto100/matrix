package base

import (
	"context"
	"encoding/json"
	"strings"
	"time"

	"tradeviewfusion/go-backend/internal/cache"
)

const DefaultAPIHotCacheTTL = 5 * time.Minute

type JSONHotCache struct {
	adapter cache.Adapter
	ttl     time.Duration
	prefix  string
}

func NewJSONHotCache(prefix string, ttl time.Duration) *JSONHotCache {
	if ttl < 0 {
		ttl = 0
	}
	if ttl == 0 {
		ttl = DefaultAPIHotCacheTTL
	}
	return &JSONHotCache{
		adapter: cache.NewAdapterFromEnv(),
		ttl:     ttl,
		prefix:  strings.TrimSpace(prefix),
	}
}

func (c *JSONHotCache) Get(ctx context.Context, key string, target any) bool {
	if c == nil || c.adapter == nil || c.ttl <= 0 {
		return false
	}
	raw, ok := c.adapter.Get(ctx, c.cacheKey(key))
	if !ok || strings.TrimSpace(raw) == "" {
		return false
	}
	if err := json.Unmarshal([]byte(raw), target); err != nil {
		c.adapter.Delete(ctx, c.cacheKey(key))
		return false
	}
	return true
}

func (c *JSONHotCache) Set(ctx context.Context, key string, value any) {
	if c == nil || c.adapter == nil || c.ttl <= 0 {
		return
	}
	raw, err := json.Marshal(value)
	if err != nil {
		return
	}
	c.adapter.Set(ctx, c.cacheKey(key), string(raw), c.ttl)
}

func (c *JSONHotCache) cacheKey(key string) string {
	key = strings.TrimSpace(key)
	if c.prefix == "" {
		return key
	}
	return c.prefix + ":" + key
}

func StableCacheKey(parts ...string) string {
	normalized := make([]string, 0, len(parts))
	for _, part := range parts {
		normalized = append(normalized, strings.TrimSpace(part))
	}
	return strings.Join(normalized, "|")
}
