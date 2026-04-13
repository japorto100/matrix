package storage

import (
	"bytes"
	"context"
	"io"
	"strings"
	"testing"
	"time"
)

// fakeProvider is a minimal in-memory ObjectStore for service_test.
type fakeProvider struct {
	objects map[string][]byte
}

func newFakeProvider() *fakeProvider {
	return &fakeProvider{objects: make(map[string][]byte)}
}

func (p *fakeProvider) Put(_ context.Context, key string, body io.Reader) (UploadResult, error) {
	data, err := io.ReadAll(body)
	if err != nil {
		return UploadResult{}, err
	}
	p.objects[key] = data
	return UploadResult{
		SizeBytes:  int64(len(data)),
		SHA256Hex:  "fakehash",
		UploadedAt: time.Now().UTC(),
	}, nil
}

func (p *fakeProvider) Get(_ context.Context, key string) (io.ReadCloser, error) {
	data, ok := p.objects[key]
	if !ok {
		return nil, ErrArtifactNotFound
	}
	return io.NopCloser(bytes.NewReader(data)), nil
}

func TestServiceCreateArtifact(t *testing.T) {
	store := newFakeStore()
	provider := newFakeProvider()
	svc, err := NewService(Config{
		Provider:      ProviderFilesystem,
		BaseDir:       t.TempDir(),
		SigningSecret: "test-secret-32-chars-minimum-ok!",
		Store:         store,
	})
	if err != nil {
		t.Fatalf("NewService: %v", err)
	}
	// Override provider with fake
	svc.provider = provider

	artifact, err := svc.CreateArtifact(context.Background(), CreateArtifactInput{
		UserID:      "alice",
		Filename:    "report.pdf",
		ContentType: "application/pdf",
	})
	if err != nil {
		t.Fatalf("CreateArtifact: %v", err)
	}
	if artifact.ID == "" {
		t.Error("artifact ID should not be empty")
	}
	if artifact.UserID != "alice" {
		t.Errorf("UserID = %q, want alice", artifact.UserID)
	}
	if artifact.Status != StatusPendingUpload {
		t.Errorf("Status = %q, want pending_upload", artifact.Status)
	}
	if artifact.MediaType != MediaTypeDocument {
		t.Errorf("MediaType = %q, want document", artifact.MediaType)
	}
	if !strings.Contains(artifact.ObjectKey, "alice") {
		t.Errorf("ObjectKey should contain user prefix: %q", artifact.ObjectKey)
	}
}

func TestServiceIssueUploadURL(t *testing.T) {
	store := newFakeStore()
	svc, _ := NewService(Config{
		Provider:      ProviderFilesystem,
		BaseDir:       t.TempDir(),
		SigningSecret: "test-secret-32-chars-minimum-ok!",
		Store:         store,
	})
	svc.provider = newFakeProvider()

	artifact, _ := svc.CreateArtifact(context.Background(), CreateArtifactInput{
		UserID: "alice", Filename: "doc.pdf", ContentType: "application/pdf",
	})

	signed, err := svc.IssueUploadURL(artifact.ID, "alice", "http://localhost:8090")
	if err != nil {
		t.Fatalf("IssueUploadURL: %v", err)
	}
	if signed.Method != "PUT" {
		t.Errorf("Method = %q, want PUT", signed.Method)
	}
	if !strings.Contains(signed.URL, "token=") {
		t.Errorf("URL should contain token: %q", signed.URL)
	}
	if signed.Token == "" {
		t.Error("Token should not be empty")
	}
}

func TestServiceIssueUploadURL_WrongUser(t *testing.T) {
	store := newFakeStore()
	svc, _ := NewService(Config{
		Provider: ProviderFilesystem, BaseDir: t.TempDir(),
		SigningSecret: "test-secret-32-chars-minimum-ok!", Store: store,
	})
	svc.provider = newFakeProvider()

	artifact, _ := svc.CreateArtifact(context.Background(), CreateArtifactInput{
		UserID: "alice", Filename: "doc.pdf", ContentType: "application/pdf",
	})

	_, err := svc.IssueUploadURL(artifact.ID, "bob", "http://localhost:8090")
	if err == nil {
		t.Error("bob should not get upload URL for alice's artifact")
	}
}

func TestServiceGetArtifact(t *testing.T) {
	store := newFakeStore()
	svc, _ := NewService(Config{
		Provider: ProviderFilesystem, BaseDir: t.TempDir(),
		SigningSecret: "test-secret-32-chars-minimum-ok!", Store: store,
	})
	svc.provider = newFakeProvider()

	created, _ := svc.CreateArtifact(context.Background(), CreateArtifactInput{
		UserID: "alice", Filename: "doc.pdf", ContentType: "application/pdf",
	})

	got, err := svc.GetArtifact(created.ID, "alice")
	if err != nil {
		t.Fatalf("GetArtifact: %v", err)
	}
	if got.ID != created.ID {
		t.Errorf("ID = %q, want %q", got.ID, created.ID)
	}
}

func TestServiceGetArtifact_WrongUser(t *testing.T) {
	store := newFakeStore()
	svc, _ := NewService(Config{
		Provider: ProviderFilesystem, BaseDir: t.TempDir(),
		SigningSecret: "test-secret-32-chars-minimum-ok!", Store: store,
	})
	svc.provider = newFakeProvider()

	created, _ := svc.CreateArtifact(context.Background(), CreateArtifactInput{
		UserID: "alice", Filename: "doc.pdf", ContentType: "application/pdf",
	})

	_, err := svc.GetArtifact(created.ID, "bob")
	if err == nil {
		t.Error("bob should not see alice's artifact")
	}
}

func TestServiceDeleteArtifact(t *testing.T) {
	store := newFakeStore()
	svc, _ := NewService(Config{
		Provider: ProviderFilesystem, BaseDir: t.TempDir(),
		SigningSecret: "test-secret-32-chars-minimum-ok!", Store: store,
	})
	svc.provider = newFakeProvider()

	created, _ := svc.CreateArtifact(context.Background(), CreateArtifactInput{
		UserID: "alice", Filename: "doc.pdf", ContentType: "application/pdf",
	})

	if err := svc.DeleteArtifact(context.Background(), created.ID); err != nil {
		t.Fatalf("DeleteArtifact: %v", err)
	}
	_, err := svc.GetArtifact(created.ID, "alice")
	if err == nil {
		t.Error("artifact should be gone after delete")
	}
}
