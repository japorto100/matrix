package storage

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"os"
	"strings"
	"testing"
	"time"
)

// Integration tests against a real SeaweedFS S3 endpoint. Skips cleanly if
// unreachable so CI without a live devstack still runs the unit tests.
//
// Requires:
//   ARTIFACT_STORAGE_S3_ENDPOINT (default http://127.0.0.1:8333)
//   ARTIFACT_STORAGE_S3_BUCKET   (default matrix-artifacts)
//   ARTIFACT_STORAGE_S3_ACCESS_KEY_ID
//   ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY
// or a seaweedfs with the go-appservice/.env.development defaults.

func newTestS3Provider(t *testing.T) *S3Provider {
	t.Helper()
	endpoint := envOr("ARTIFACT_STORAGE_S3_ENDPOINT", "http://127.0.0.1:8333")

	// Fast pre-check: raw TCP dial. If SeaweedFS is down, skip before
	// AWS SDK wastes time on 3 retries with backoff (~6s per call).
	host := strings.TrimPrefix(strings.TrimPrefix(endpoint, "http://"), "https://")
	if idx := strings.Index(host, "/"); idx > 0 {
		host = host[:idx]
	}
	dialer := &net.Dialer{Timeout: 500 * time.Millisecond}
	conn, dialErr := dialer.Dial("tcp", host)
	if dialErr != nil {
		t.Skipf("SeaweedFS unreachable at %s: %v", host, dialErr)
	}
	_ = conn.Close()

	cfg := S3Config{
		Endpoint:        endpoint,
		Region:          envOr("ARTIFACT_STORAGE_S3_REGION", "us-east-1"),
		Bucket:          envOr("ARTIFACT_STORAGE_S3_BUCKET", "matrix-artifacts-test"),
		AccessKeyID:     envOr("ARTIFACT_STORAGE_S3_ACCESS_KEY_ID", "seaweedfs"),
		SecretAccessKey: envOr("ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY", "seaweedfs-secret"),
		UsePathStyle:    true,
		CreateBucket:    true,
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	provider, err := NewS3Provider(ctx, cfg)
	if err != nil {
		t.Skipf("NewS3Provider failed (%s): %v", endpoint, err)
	}
	return provider
}

func envOr(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

// uniquePrefix generates a prefix so parallel test runs + reruns don't collide
// with each other's objects.
func uniquePrefix(t *testing.T) string {
	t.Helper()
	return fmt.Sprintf("test/%s-%d/", t.Name(), time.Now().UnixNano())
}

func TestS3ProviderPutThenList(t *testing.T) {
	provider := newTestS3Provider(t)
	ctx := context.Background()
	prefix := uniquePrefix(t)

	// Upload 3 objects under the prefix
	for i := range 3 {
		key := fmt.Sprintf("%sfile-%d.txt", prefix, i)
		body := bytes.NewReader(fmt.Appendf(nil, "hello-%d", i))
		if _, err := provider.Put(ctx, key, body); err != nil {
			t.Fatalf("Put %s: %v", key, err)
		}
	}
	// Cleanup on teardown
	t.Cleanup(func() {
		for i := range 3 {
			_ = provider.Delete(ctx, fmt.Sprintf("%sfile-%d.txt", prefix, i))
		}
	})

	// List them back
	objs, err := provider.ListObjects(ctx, prefix, 100)
	if err != nil {
		t.Fatalf("ListObjects: %v", err)
	}
	if len(objs) != 3 {
		t.Fatalf("len(objs) = %d, want 3. Objects: %+v", len(objs), objs)
	}
	seen := make(map[string]bool)
	for _, o := range objs {
		seen[o.Key] = true
		if o.SizeBytes <= 0 {
			t.Errorf("object %s has SizeBytes = %d, want > 0", o.Key, o.SizeBytes)
		}
		if o.LastModified.IsZero() {
			t.Errorf("object %s LastModified is zero", o.Key)
		}
	}
	for i := range 3 {
		key := fmt.Sprintf("%sfile-%d.txt", prefix, i)
		if !seen[key] {
			t.Errorf("key %s not in listing", key)
		}
	}
}

func TestS3ProviderListEmpty(t *testing.T) {
	provider := newTestS3Provider(t)
	ctx := context.Background()
	prefix := uniquePrefix(t) // unique, nothing ever uploaded here

	objs, err := provider.ListObjects(ctx, prefix, 10)
	if err != nil {
		t.Fatalf("ListObjects empty: %v", err)
	}
	if len(objs) != 0 {
		t.Errorf("len(objs) = %d, want 0", len(objs))
	}
}

func TestS3ProviderListMaxKeys(t *testing.T) {
	provider := newTestS3Provider(t)
	ctx := context.Background()
	prefix := uniquePrefix(t)

	// Upload 5 objects
	for i := range 5 {
		key := fmt.Sprintf("%sobj-%d", prefix, i)
		_, err := provider.Put(ctx, key, bytes.NewReader([]byte("x")))
		if err != nil {
			t.Fatalf("Put: %v", err)
		}
	}
	t.Cleanup(func() {
		for i := range 5 {
			_ = provider.Delete(ctx, fmt.Sprintf("%sobj-%d", prefix, i))
		}
	})

	// Ask for only 2
	objs, err := provider.ListObjects(ctx, prefix, 2)
	if err != nil {
		t.Fatalf("ListObjects maxKeys=2: %v", err)
	}
	if len(objs) != 2 {
		t.Errorf("len(objs) = %d, want 2", len(objs))
	}
}

func TestS3ProviderListPrefixIsolation(t *testing.T) {
	provider := newTestS3Provider(t)
	ctx := context.Background()

	userA := fmt.Sprintf("users/test-a-%d/", time.Now().UnixNano())
	userB := fmt.Sprintf("users/test-b-%d/", time.Now().UnixNano())

	for _, key := range []string{userA + "doc.pdf", userA + "song.mp3"} {
		if _, err := provider.Put(ctx, key, bytes.NewReader([]byte("x"))); err != nil {
			t.Fatalf("Put %s: %v", key, err)
		}
	}
	for _, key := range []string{userB + "other.txt"} {
		if _, err := provider.Put(ctx, key, bytes.NewReader([]byte("x"))); err != nil {
			t.Fatalf("Put %s: %v", key, err)
		}
	}
	t.Cleanup(func() {
		for _, key := range []string{
			userA + "doc.pdf", userA + "song.mp3", userB + "other.txt",
		} {
			_ = provider.Delete(ctx, key)
		}
	})

	// User A sees exactly 2 objects
	objsA, err := provider.ListObjects(ctx, userA, 100)
	if err != nil {
		t.Fatalf("ListObjects userA: %v", err)
	}
	if len(objsA) != 2 {
		t.Errorf("userA len = %d, want 2", len(objsA))
	}
	for _, o := range objsA {
		if !strings.HasPrefix(o.Key, userA) {
			t.Errorf("userA listing returned cross-user key %q", o.Key)
		}
	}

	// User B sees exactly 1
	objsB, err := provider.ListObjects(ctx, userB, 100)
	if err != nil {
		t.Fatalf("ListObjects userB: %v", err)
	}
	if len(objsB) != 1 {
		t.Errorf("userB len = %d, want 1", len(objsB))
	}
}

func TestS3ProviderDelete(t *testing.T) {
	provider := newTestS3Provider(t)
	ctx := context.Background()
	prefix := uniquePrefix(t)
	key := prefix + "to-delete.txt"

	if _, err := provider.Put(ctx, key, bytes.NewReader([]byte("bye"))); err != nil {
		t.Fatalf("Put: %v", err)
	}
	// verify present
	objs, _ := provider.ListObjects(ctx, prefix, 10)
	if len(objs) != 1 {
		t.Fatalf("before delete: len = %d, want 1", len(objs))
	}
	// delete
	if err := provider.Delete(ctx, key); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	// verify gone
	objs, _ = provider.ListObjects(ctx, prefix, 10)
	if len(objs) != 0 {
		t.Errorf("after delete: len = %d, want 0", len(objs))
	}
}

func TestS3ProviderDeleteIdempotent(t *testing.T) {
	provider := newTestS3Provider(t)
	ctx := context.Background()
	// Deleting a non-existent key should not error on S3 (it's idempotent
	// by spec). SeaweedFS follows this.
	if err := provider.Delete(ctx, "test/nonexistent/thing.txt"); err != nil {
		t.Errorf("Delete non-existent: %v (S3 DELETE is idempotent)", err)
	}
}
