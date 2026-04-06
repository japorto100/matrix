// Package cache provides a minimal cache adapter abstraction.
// Default: in-memory LRU with per-entry TTL.
// Optional: Redis/Valkey adapter (enabled via MEMORY_REDIS_ENABLED=true or
// MEMORY_CACHE_PROVIDER=redis|valkey).
package cache

import (
	"context"
	"os"
	"strings"
	"sync"
	"time"

	redis "github.com/redis/go-redis/v9"
)

// Adapter is the minimal interface for a key-value cache.
type Adapter interface {
	// Get returns the value for key, or ("", false) if not found / expired.
	Get(ctx context.Context, key string) (string, bool)
	// Set stores value under key with the given TTL.
	Set(ctx context.Context, key, value string, ttl time.Duration)
	// Delete removes key from the cache.
	Delete(ctx context.Context, key string)
	// Ping checks liveness of the cache backend.
	Ping(ctx context.Context) bool
	// BackendName returns a short identifier ("memory", "redis", "valkey").
	BackendName() string
}

// ---------------------------------------------------------------------------
// InMemoryAdapter
// ---------------------------------------------------------------------------

type entry struct {
	value     string
	expiresAt time.Time
}

// InMemoryAdapter is a simple in-memory LRU-style cache with per-entry TTL.
// Access is guarded by a sync.RWMutex; eviction is lazy (on Get/Set).
type InMemoryAdapter struct {
	mu      sync.RWMutex
	entries map[string]entry
	maxSize int
}

// NewInMemoryAdapter creates an InMemoryAdapter with the given capacity.
// If maxSize <= 0, it defaults to 4096.
func NewInMemoryAdapter(maxSize int) *InMemoryAdapter {
	if maxSize <= 0 {
		maxSize = 4096
	}
	return &InMemoryAdapter{
		entries: make(map[string]entry, maxSize),
		maxSize: maxSize,
	}
}

func (a *InMemoryAdapter) Get(_ context.Context, key string) (string, bool) {
	a.mu.RLock()
	e, ok := a.entries[key]
	a.mu.RUnlock()
	if !ok {
		return "", false
	}
	if time.Now().After(e.expiresAt) {
		a.mu.Lock()
		delete(a.entries, key)
		a.mu.Unlock()
		return "", false
	}
	return e.value, true
}

func (a *InMemoryAdapter) Set(_ context.Context, key, value string, ttl time.Duration) {
	if ttl <= 0 {
		ttl = 5 * time.Minute
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	if len(a.entries) >= a.maxSize && a.entries[key].value == "" {
		a.evictOneLocked()
	}
	a.entries[key] = entry{value: value, expiresAt: time.Now().Add(ttl)}
}

func (a *InMemoryAdapter) Delete(_ context.Context, key string) {
	a.mu.Lock()
	delete(a.entries, key)
	a.mu.Unlock()
}

func (a *InMemoryAdapter) Ping(_ context.Context) bool { return true }

func (a *InMemoryAdapter) BackendName() string { return "memory" }

// evictOneLocked removes one expired or (if none expired) the first entry.
// Must be called with a.mu held for write.
func (a *InMemoryAdapter) evictOneLocked() {
	now := time.Now()
	for k, e := range a.entries {
		if now.After(e.expiresAt) {
			delete(a.entries, k)
			return
		}
	}
	for k := range a.entries {
		delete(a.entries, k)
		return
	}
}

// ---------------------------------------------------------------------------
// RedisAdapter (optional)
// ---------------------------------------------------------------------------

// RedisAdapter wraps a go-redis v9 client.
// It is used for both Redis and Valkey via the same RESP-compatible client.
type RedisAdapter struct {
	client      *redis.Client
	backendName string
}

// NewRedisAdapter creates a RedisAdapter.
func NewRedisAdapter(client *redis.Client, backendName string) *RedisAdapter {
	if strings.TrimSpace(backendName) == "" {
		backendName = "redis"
	}
	return &RedisAdapter{
		client:      client,
		backendName: backendName,
	}
}

func (a *RedisAdapter) Get(ctx context.Context, key string) (string, bool) {
	val, err := a.client.Get(ctx, key).Result()
	if err != nil {
		return "", false
	}
	return val, true
}

func (a *RedisAdapter) Set(ctx context.Context, key, value string, ttl time.Duration) {
	_ = a.client.Set(ctx, key, value, ttl).Err()
}

func (a *RedisAdapter) Delete(ctx context.Context, key string) {
	_ = a.client.Del(ctx, key).Err()
}

func (a *RedisAdapter) Ping(ctx context.Context) bool {
	return a.client.Ping(ctx).Err() == nil
}

func (a *RedisAdapter) BackendName() string { return a.backendName }

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

// NewAdapter returns an InMemoryAdapter by default.
// If redisEnabled is true and client is non-nil, it returns a RedisAdapter.
func NewAdapter(redisEnabled bool, client *redis.Client) Adapter {
	if redisEnabled && client != nil {
		return NewRedisAdapter(client, "redis")
	}
	return NewInMemoryAdapter(0)
}

// NewAdapterFromEnv returns an adapter based on local env defaults.
// Supported variables:
//
//	MEMORY_CACHE_PROVIDER=local|redis|valkey
//	CACHE_PROVIDER=local|redis|valkey
//	MEMORY_REDIS_ENABLED=true
//	MEMORY_VALKEY_URL / MEMORY_REDIS_URL
func NewAdapterFromEnv() Adapter {
	provider := strings.ToLower(strings.TrimSpace(os.Getenv("MEMORY_CACHE_PROVIDER")))
	if provider == "" {
		provider = strings.ToLower(strings.TrimSpace(os.Getenv("CACHE_PROVIDER")))
	}
	if provider == "" {
		if strings.EqualFold(strings.TrimSpace(os.Getenv("MEMORY_REDIS_ENABLED")), "true") ||
			strings.TrimSpace(os.Getenv("MEMORY_REDIS_ENABLED")) == "1" {
			if strings.TrimSpace(os.Getenv("MEMORY_VALKEY_URL")) != "" {
				provider = "valkey"
			} else {
				provider = "redis"
			}
		}
	}

	switch provider {
	case "redis", "valkey":
		url := strings.TrimSpace(os.Getenv("MEMORY_VALKEY_URL"))
		if provider == "redis" || url == "" {
			url = strings.TrimSpace(os.Getenv("MEMORY_REDIS_URL"))
		}
		if strings.TrimSpace(url) == "" {
			url = "redis://127.0.0.1:6379/0"
		}
		opts, err := redis.ParseURL(url)
		if err != nil {
			return NewInMemoryAdapter(0)
		}
		client := redis.NewClient(opts)
		return NewRedisAdapter(client, provider)
	default:
		return NewInMemoryAdapter(0)
	}
}
