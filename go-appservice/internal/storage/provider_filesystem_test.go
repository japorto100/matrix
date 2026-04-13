package storage

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFilesystemProviderPutGetRoundtrip(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	p, err := NewFilesystemProvider(dir)
	if err != nil {
		t.Fatalf("NewFilesystemProvider: %v", err)
	}

	content := "hello filesystem provider"
	result, err := p.Put(t.Context(), "test/doc.txt", strings.NewReader(content))
	if err != nil {
		t.Fatalf("Put: %v", err)
	}
	if result.SizeBytes != int64(len(content)) {
		t.Errorf("SizeBytes = %d, want %d", result.SizeBytes, len(content))
	}
	if result.SHA256Hex == "" {
		t.Error("SHA256Hex should not be empty")
	}

	reader, err := p.Get(t.Context(), "test/doc.txt")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	defer func() { _ = reader.Close() }()
	body, err := io.ReadAll(reader)
	if err != nil {
		t.Fatalf("ReadAll: %v", err)
	}
	if string(body) != content {
		t.Errorf("body = %q, want %q", string(body), content)
	}
}

func TestFilesystemProviderGetNotFound(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	p, _ := NewFilesystemProvider(dir)

	_, err := p.Get(t.Context(), "nonexistent/file.txt")
	if err == nil {
		t.Error("Get nonexistent should fail")
	}
}

func TestFilesystemProviderPathTraversal(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	p, _ := NewFilesystemProvider(dir)

	attackKeys := []string{
		"../../etc/passwd",
		"..\\..\\windows\\system32\\config\\sam",
		"../secret.txt",
		"",
		"   ",
	}
	for _, key := range attackKeys {
		_, err := p.Put(t.Context(), key, bytes.NewReader([]byte("x")))
		if err == nil {
			t.Errorf("Put(%q) should have been rejected (path traversal)", key)
		}
		_, err = p.Get(t.Context(), key)
		if err == nil {
			t.Errorf("Get(%q) should have been rejected (path traversal)", key)
		}
	}
}

func TestFilesystemProviderSHA256Correctness(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	p, _ := NewFilesystemProvider(dir)

	result1, _ := p.Put(t.Context(), "a.txt", strings.NewReader("hello"))
	result2, _ := p.Put(t.Context(), "b.txt", strings.NewReader("hello"))
	result3, _ := p.Put(t.Context(), "c.txt", strings.NewReader("world"))

	if result1.SHA256Hex != result2.SHA256Hex {
		t.Error("same content should produce same SHA256")
	}
	if result1.SHA256Hex == result3.SHA256Hex {
		t.Error("different content should produce different SHA256")
	}
}

func TestFilesystemProviderCreatesSubdirs(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()
	p, _ := NewFilesystemProvider(dir)

	_, err := p.Put(t.Context(), "deep/nested/path/file.txt", strings.NewReader("hi"))
	if err != nil {
		t.Fatalf("Put deep path: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, "deep", "nested", "path", "file.txt")); err != nil {
		t.Errorf("file should exist at deep path: %v", err)
	}
}

func TestFilesystemProviderEmptyBaseDir(t *testing.T) {
	t.Parallel()
	if _, err := NewFilesystemProvider(""); err == nil {
		t.Error("empty base dir should fail")
	}
}
