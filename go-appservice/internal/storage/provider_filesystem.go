package storage

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type ObjectStore interface {
	Put(ctx context.Context, objectKey string, body io.Reader) (UploadResult, error)
	Get(ctx context.Context, objectKey string) (io.ReadCloser, error)
}

type Provider = ObjectStore

type FilesystemProvider struct {
	baseDir string
}

func NewFilesystemProvider(baseDir string) (*FilesystemProvider, error) {
	trimmed := filepath.Clean(baseDir)
	if trimmed == "." || trimmed == "" {
		return nil, fmt.Errorf("filesystem base dir required")
	}
	if err := os.MkdirAll(trimmed, 0o750); err != nil {
		return nil, fmt.Errorf("create filesystem provider dir: %w", err)
	}
	return &FilesystemProvider{baseDir: trimmed}, nil
}

func (p *FilesystemProvider) Put(_ context.Context, objectKey string, body io.Reader) (UploadResult, error) {
	targetPath, err := p.pathForKey(objectKey)
	if err != nil {
		return UploadResult{}, err
	}
	if mkdirErr := os.MkdirAll(filepath.Dir(targetPath), 0o750); mkdirErr != nil {
		return UploadResult{}, fmt.Errorf("create object dir: %w", mkdirErr)
	}

	tmpFile, err := os.CreateTemp(filepath.Dir(targetPath), "artifact-*.tmp")
	if err != nil {
		return UploadResult{}, fmt.Errorf("create temp object: %w", err)
	}
	defer func() {
		_ = tmpFile.Close()
		_ = os.Remove(tmpFile.Name())
	}()

	hash := sha256.New()
	written, err := io.Copy(io.MultiWriter(tmpFile, hash), body)
	if err != nil {
		return UploadResult{}, fmt.Errorf("write object: %w", err)
	}
	if err := tmpFile.Sync(); err != nil {
		return UploadResult{}, fmt.Errorf("sync object: %w", err)
	}
	if err := tmpFile.Close(); err != nil {
		return UploadResult{}, fmt.Errorf("close temp object: %w", err)
	}
	if err := os.Rename(tmpFile.Name(), targetPath); err != nil {
		return UploadResult{}, fmt.Errorf("move object into place: %w", err)
	}

	return UploadResult{
		SizeBytes:  written,
		SHA256Hex:  hex.EncodeToString(hash.Sum(nil)),
		UploadedAt: time.Now().UTC(),
	}, nil
}

func (p *FilesystemProvider) Get(_ context.Context, objectKey string) (io.ReadCloser, error) {
	targetPath, err := p.pathForKey(objectKey)
	if err != nil {
		return nil, err
	}
	file, err := os.Open(targetPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, ErrArtifactNotFound
		}
		return nil, fmt.Errorf("open object: %w", err)
	}
	return file, nil
}

func (p *FilesystemProvider) pathForKey(objectKey string) (string, error) {
	trimmed := strings.TrimSpace(objectKey)
	if trimmed == "" {
		return "", fmt.Errorf("object key required")
	}
	clean := filepath.Clean(filepath.FromSlash(trimmed))
	if clean == "." || clean == "" || strings.HasPrefix(clean, "..") {
		return "", fmt.Errorf("invalid object key")
	}
	return filepath.Join(p.baseDir, clean), nil
}
