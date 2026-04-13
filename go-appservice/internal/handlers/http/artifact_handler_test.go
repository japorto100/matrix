package http

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"matrix/go-appservice/internal/storage"
)

// fakeArtifactService satisfies the artifactService interface for handler tests.
type fakeArtifactService struct {
	createResult storage.Artifact
	createErr    error
	uploadURL    storage.SignedURL
	uploadURLErr error
	getResult    storage.Artifact
	getErr       error
	uploadErr    error
	downloadArt  storage.Artifact
	downloadBody string
	downloadErr  error
}

func (f *fakeArtifactService) CreateArtifact(_ context.Context, _ storage.CreateArtifactInput) (storage.Artifact, error) {
	return f.createResult, f.createErr
}
func (f *fakeArtifactService) IssueUploadURL(_, _, _ string) (storage.SignedURL, error) {
	return f.uploadURL, f.uploadURLErr
}
func (f *fakeArtifactService) IssueDownloadURL(_, _, _ string) (storage.SignedURL, error) {
	return storage.SignedURL{}, nil
}
func (f *fakeArtifactService) GetArtifact(_, _ string) (storage.Artifact, error) {
	return f.getResult, f.getErr
}
func (f *fakeArtifactService) UploadArtifact(_ context.Context, _, _, _, _ string, _ io.ReadCloser) error {
	return f.uploadErr
}
func (f *fakeArtifactService) OpenDownload(_ context.Context, _, _, _ string) (storage.Artifact, io.ReadCloser, error) {
	if f.downloadErr != nil {
		return storage.Artifact{}, nil, f.downloadErr
	}
	return f.downloadArt, io.NopCloser(strings.NewReader(f.downloadBody)), nil
}

func TestArtifactUploadURLHandler_Success(t *testing.T) {
	svc := &fakeArtifactService{
		createResult: storage.Artifact{ID: "art_new", Filename: "doc.pdf", Status: storage.StatusPendingUpload},
		uploadURL: storage.SignedURL{
			Method: "PUT", URL: "http://signed.example/upload?token=abc", Token: "abc",
		},
	}
	h := ArtifactUploadURLHandler(svc, "http://localhost:8090")
	req := httptest.NewRequest(http.MethodPost, "/api/v1/storage/artifacts/upload-url",
		strings.NewReader(`{"filename":"doc.pdf","contentType":"application/pdf"}`))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Actor-User-Id", "alice")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != http.StatusCreated {
		t.Errorf("status = %d, want 201", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "art_new") {
		t.Errorf("body should contain artifact ID: %s", rec.Body.String())
	}
}

func TestArtifactUploadURLHandler_MethodNotAllowed(t *testing.T) {
	h := ArtifactUploadURLHandler(&fakeArtifactService{}, "http://localhost:8090")
	req := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/upload-url", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestArtifactMetadataHandler_GetSuccess(t *testing.T) {
	svc := &fakeArtifactService{
		getResult: storage.Artifact{
			ID: "art_1", Filename: "doc.pdf", Status: storage.StatusReady,
			DownloadToken: "dl-token",
		},
	}
	h := ArtifactMetadataHandler(svc)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/art_1", nil)
	req.Header.Set("X-Actor-User-Id", "alice")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "doc.pdf") {
		t.Errorf("body should contain filename: %s", rec.Body.String())
	}
}

func TestArtifactMetadataHandler_NotFound(t *testing.T) {
	svc := &fakeArtifactService{getErr: storage.ErrArtifactNotFound}
	h := ArtifactMetadataHandler(svc)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/nope", nil)
	req.Header.Set("X-Actor-User-Id", "alice")
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want 404", rec.Code)
	}
}

func TestArtifactMetadataHandler_Forbidden(t *testing.T) {
	svc := &fakeArtifactService{getErr: storage.ErrForbidden}
	h := ArtifactMetadataHandler(svc)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/art_1", nil)
	req.Header.Set("X-Actor-User-Id", "bob")
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rec.Code)
	}
}

func TestArtifactUploadHandler_InvalidToken(t *testing.T) {
	svc := &fakeArtifactService{uploadErr: storage.ErrInvalidToken}
	h := ArtifactUploadHandler(svc)
	req := httptest.NewRequest(http.MethodPut, "/api/v1/storage/artifacts/upload/art_1?token=bad", nil)
	req.Header.Set("X-Actor-User-Id", "alice")
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", rec.Code)
	}
}

func TestArtifactDownloadHandler_Success(t *testing.T) {
	svc := &fakeArtifactService{
		downloadArt:  storage.Artifact{ID: "art_1", Filename: "doc.pdf", ContentType: "application/pdf"},
		downloadBody: "PDF-CONTENT",
	}
	h := ArtifactDownloadHandler(svc)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/art_1/download?token=valid", nil)
	req.Header.Set("X-Actor-User-Id", "alice")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if rec.Header().Get("Content-Type") != "application/pdf" {
		t.Errorf("Content-Type = %q", rec.Header().Get("Content-Type"))
	}
	if rec.Body.String() != "PDF-CONTENT" {
		t.Errorf("body = %q", rec.Body.String())
	}
}
