package storage

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

func TestS3ProviderPutGet_PathStyleFlow(t *testing.T) {
	t.Parallel()

	var (
		mu      sync.Mutex
		buckets = map[string]map[string][]byte{}
	)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := strings.TrimPrefix(r.URL.Path, "/")
		parts := strings.SplitN(path, "/", 2)
		if len(parts) == 0 || strings.TrimSpace(parts[0]) == "" {
			http.Error(w, "bucket required", http.StatusBadRequest)
			return
		}
		bucket := parts[0]
		key := ""
		if len(parts) == 2 {
			key = parts[1]
		}

		mu.Lock()
		defer mu.Unlock()

		switch r.Method {
		case http.MethodHead:
			if _, ok := buckets[bucket]; !ok {
				http.NotFound(w, r)
				return
			}
			w.WriteHeader(http.StatusOK)
		case http.MethodPut:
			if key == "" {
				if _, ok := buckets[bucket]; !ok {
					buckets[bucket] = map[string][]byte{}
				}
				w.WriteHeader(http.StatusOK)
				return
			}
			if _, ok := buckets[bucket]; !ok {
				http.NotFound(w, r)
				return
			}
			body, err := io.ReadAll(r.Body)
			if err != nil {
				t.Fatalf("read request body: %v", err)
			}
			buckets[bucket][key] = body
			w.WriteHeader(http.StatusOK)
		case http.MethodGet:
			bucketObjects, ok := buckets[bucket]
			if !ok {
				http.NotFound(w, r)
				return
			}
			body, ok := bucketObjects[key]
			if !ok {
				http.NotFound(w, r)
				return
			}
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write(body)
		default:
			http.Error(w, "unsupported method", http.StatusMethodNotAllowed)
		}
	}))
	defer server.Close()

	provider, err := NewS3Provider(context.Background(), S3Config{
		Endpoint:        server.URL,
		Region:          "us-east-1",
		Bucket:          "artifacts",
		AccessKeyID:     "dev-access-key",
		SecretAccessKey: "dev-secret-key",
		UsePathStyle:    true,
		CreateBucket:    true,
	})
	if err != nil {
		t.Fatalf("new s3 provider: %v", err)
	}

	putResult, err := provider.Put(context.Background(), "reports/daily.txt", bytes.NewBufferString("hello seaweed"))
	if err != nil {
		t.Fatalf("put object: %v", err)
	}
	if putResult.SizeBytes != int64(len("hello seaweed")) {
		t.Fatalf("size bytes = %d", putResult.SizeBytes)
	}
	if putResult.SHA256Hex == "" {
		t.Fatal("expected sha256 hash")
	}

	reader, err := provider.Get(context.Background(), "reports/daily.txt")
	if err != nil {
		t.Fatalf("get object: %v", err)
	}
	defer func() { _ = reader.Close() }()

	body, err := io.ReadAll(reader)
	if err != nil {
		t.Fatalf("read object body: %v", err)
	}
	if string(body) != "hello seaweed" {
		t.Fatalf("body = %q, want hello seaweed", string(body))
	}
}
