package http

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"tradeviewfusion/go-backend/internal/requestctx"
	"tradeviewfusion/go-backend/internal/storage"
)

func TestArtifactHandlers_UploadAndDownloadFlow(t *testing.T) {
	t.Parallel()

	service := newTestArtifactService(t)

	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/storage/artifacts/upload-url", ArtifactUploadURLHandler(service, "http://gateway.test"))
	mux.HandleFunc("/api/v1/storage/artifacts/upload/", ArtifactUploadHandler(service))
	mux.HandleFunc("/api/v1/storage/artifacts/", ArtifactMetadataHandler(service))

	createReq := httptest.NewRequest(http.MethodPost, "/api/v1/storage/artifacts/upload-url", bytes.NewBufferString(`{
		"filename":"report.txt",
		"contentType":"text/plain",
		"retentionClass":"analysis"
	}`))
	createRec := httptest.NewRecorder()
	mux.ServeHTTP(createRec, createReq)

	if createRec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d, body=%s", createRec.Code, http.StatusCreated, createRec.Body.String())
	}

	var createResp storageArtifactEnvelope
	if err := json.Unmarshal(createRec.Body.Bytes(), &createResp); err != nil {
		t.Fatalf("decode create response: %v", err)
	}
	if createResp.Data.Upload.Method != http.MethodPut {
		t.Fatalf("upload method = %q, want PUT", createResp.Data.Upload.Method)
	}
	if createResp.Data.Artifact.ID == "" {
		t.Fatal("expected artifact id")
	}

	uploadReq := httptest.NewRequest(http.MethodPut, createResp.Data.Upload.URL, bytes.NewBufferString("hello storage"))
	uploadReq.Header.Set("Content-Type", "text/plain")
	uploadRec := httptest.NewRecorder()
	mux.ServeHTTP(uploadRec, uploadReq)

	if uploadRec.Code != http.StatusCreated {
		t.Fatalf("upload status = %d, want %d, body=%s", uploadRec.Code, http.StatusCreated, uploadRec.Body.String())
	}

	metaReq := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/"+createResp.Data.Artifact.ID, nil)
	metaRec := httptest.NewRecorder()
	mux.ServeHTTP(metaRec, metaReq)

	if metaRec.Code != http.StatusOK {
		t.Fatalf("metadata status = %d, want %d", metaRec.Code, http.StatusOK)
	}
	var metaResp storageArtifactEnvelope
	if err := json.Unmarshal(metaRec.Body.Bytes(), &metaResp); err != nil {
		t.Fatalf("decode metadata response: %v", err)
	}
	if metaResp.Data.Artifact.Status != string(storage.StatusReady) {
		t.Fatalf("artifact status = %q, want %q", metaResp.Data.Artifact.Status, storage.StatusReady)
	}
	if metaResp.Data.Download.URL == "" {
		t.Fatal("expected download url")
	}

	downloadReq := httptest.NewRequest(http.MethodGet, metaResp.Data.Download.URL, nil)
	downloadRec := httptest.NewRecorder()
	mux.ServeHTTP(downloadRec, downloadReq)

	if downloadRec.Code != http.StatusOK {
		t.Fatalf("download status = %d, want %d, body=%s", downloadRec.Code, http.StatusOK, downloadRec.Body.String())
	}
	if body := downloadRec.Body.String(); body != "hello storage" {
		t.Fatalf("download body = %q, want hello storage", body)
	}
}

func newTestArtifactService(t *testing.T) *storage.Service {
	t.Helper()

	baseDir := t.TempDir()
	store, err := storage.NewSQLiteMetadataStore(filepath.Join(baseDir, "artifacts.db"))
	if err != nil {
		t.Fatalf("new metadata store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close metadata store: %v", closeErr)
		}
	})

	service, err := storage.NewService(storage.Config{
		Provider:      storage.ProviderFilesystem,
		BaseDir:       filepath.Join(baseDir, "objects"),
		SigningSecret: "test-signing-secret",
		TTL:           15 * time.Minute,
		Store:         store,
		NowFunc: func() time.Time {
			return time.Unix(1_700_000_000, 0).UTC()
		},
	})
	if err != nil {
		t.Fatalf("new artifact service: %v", err)
	}
	return service
}

type storageArtifactEnvelope struct {
	Success bool                   `json:"success"`
	Data    storageArtifactPayload `json:"data"`
}

type storageArtifactPayload struct {
	Artifact storageArtifactDTO `json:"artifact"`
	Upload   storageLinkDTO     `json:"upload"`
	Download storageLinkDTO     `json:"download"`
}

type storageArtifactDTO struct {
	ID     string `json:"id"`
	Status string `json:"status"`
}

type storageLinkDTO struct {
	Method string `json:"method"`
	URL    string `json:"url"`
}

func TestArtifactUploadHandler_RejectsInvalidToken(t *testing.T) {
	t.Parallel()

	service := newTestArtifactService(t)
	req := httptest.NewRequest(http.MethodPut, "/api/v1/storage/artifacts/upload/art_123?token=bad", bytes.NewBufferString("hello"))
	rec := httptest.NewRecorder()

	ArtifactUploadHandler(service)(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusUnauthorized)
	}
}

func TestArtifactService_OpenDownloadRequiresReadyArtifact(t *testing.T) {
	t.Parallel()

	service := newTestArtifactService(t)
	created, err := service.CreateArtifact(context.Background(), storage.CreateArtifactInput{
		Filename:       "report.txt",
		ContentType:    "text/plain",
		RetentionClass: "analysis",
	})
	if err != nil {
		t.Fatalf("create artifact: %v", err)
	}

	if _, _, err := service.OpenDownload(context.Background(), created.ID, "bad"); err == nil {
		t.Fatal("expected invalid token to fail")
	}
}

func TestArtifactDownloadHandler_SetsContentHeaders(t *testing.T) {
	t.Parallel()

	service := newTestArtifactService(t)
	created, err := service.CreateArtifact(context.Background(), storage.CreateArtifactInput{
		Filename:       "report.txt",
		ContentType:    "text/plain",
		RetentionClass: "analysis",
	})
	if err != nil {
		t.Fatalf("create artifact: %v", err)
	}

	uploadURL, err := service.IssueUploadURL(created.ID, "http://gateway.test")
	if err != nil {
		t.Fatalf("issue upload url: %v", err)
	}
	if uploadErr := service.UploadArtifact(context.Background(), created.ID, uploadURL.Token, "text/plain", io.NopCloser(bytes.NewBufferString("abc"))); uploadErr != nil {
		t.Fatalf("upload artifact: %v", uploadErr)
	}

	meta, err := service.GetArtifact(created.ID)
	if err != nil {
		t.Fatalf("get artifact: %v", err)
	}
	downloadReq := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/"+created.ID+"/download?token="+meta.DownloadToken, nil)
	downloadRec := httptest.NewRecorder()
	ArtifactDownloadHandler(service)(downloadRec, downloadReq)

	if got := downloadRec.Header().Get("Content-Type"); got != "text/plain" {
		t.Fatalf("content-type = %q, want text/plain", got)
	}
	if got := downloadRec.Header().Get("Content-Disposition"); got == "" {
		t.Fatal("expected content-disposition header")
	}
}

func TestArtifactHandlers_SupportMultipleArtifactTypes(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name        string
		filename    string
		contentType string
		body        string
	}{
		{name: "pdf", filename: "report.pdf", contentType: "application/pdf", body: "%PDF-1.7 sample"},
		{name: "audio", filename: "clip.mp3", contentType: "audio/mpeg", body: "ID3-audio"},
		{name: "video", filename: "sample.mp4", contentType: "video/mp4", body: "....ftypisom"},
		{name: "parquet", filename: "dataset.parquet", contentType: "application/vnd.apache.parquet", body: "PAR1-data"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			service := newTestArtifactService(t)
			mux := http.NewServeMux()
			mux.HandleFunc("/api/v1/storage/artifacts/upload-url", ArtifactUploadURLHandler(service, "http://gateway.test"))
			mux.HandleFunc("/api/v1/storage/artifacts/upload/", ArtifactUploadHandler(service))
			mux.HandleFunc("/api/v1/storage/artifacts/", ArtifactMetadataHandler(service))

			createReq := httptest.NewRequest(http.MethodPost, "/api/v1/storage/artifacts/upload-url", bytes.NewBufferString(`{
				"filename":"`+tc.filename+`",
				"contentType":"`+tc.contentType+`",
				"retentionClass":"analysis"
			}`))
			createRec := httptest.NewRecorder()
			mux.ServeHTTP(createRec, createReq)
			if createRec.Code != http.StatusCreated {
				t.Fatalf("create status = %d, body=%s", createRec.Code, createRec.Body.String())
			}

			var createResp storageArtifactEnvelope
			if err := json.Unmarshal(createRec.Body.Bytes(), &createResp); err != nil {
				t.Fatalf("decode create response: %v", err)
			}

			uploadReq := httptest.NewRequest(http.MethodPut, createResp.Data.Upload.URL, bytes.NewBufferString(tc.body))
			uploadReq.Header.Set("Content-Type", tc.contentType)
			uploadRec := httptest.NewRecorder()
			mux.ServeHTTP(uploadRec, uploadReq)
			if uploadRec.Code != http.StatusCreated {
				t.Fatalf("upload status = %d, body=%s", uploadRec.Code, uploadRec.Body.String())
			}

			metaReq := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/"+createResp.Data.Artifact.ID, nil)
			metaRec := httptest.NewRecorder()
			mux.ServeHTTP(metaRec, metaReq)
			if metaRec.Code != http.StatusOK {
				t.Fatalf("metadata status = %d", metaRec.Code)
			}
		})
	}
}

func TestArtifactUploadHandler_RejectsDuplicateUpload(t *testing.T) {
	t.Parallel()

	service := newTestArtifactService(t)
	created, err := service.CreateArtifact(context.Background(), storage.CreateArtifactInput{
		Filename:       "report.txt",
		ContentType:    "text/plain",
		RetentionClass: "analysis",
	})
	if err != nil {
		t.Fatalf("create artifact: %v", err)
	}
	uploadURL, err := service.IssueUploadURL(created.ID, "http://gateway.test")
	if err != nil {
		t.Fatalf("issue upload url: %v", err)
	}

	firstReq := httptest.NewRequest(http.MethodPut, uploadURL.URL, bytes.NewBufferString("first"))
	firstReq.Header.Set("Content-Type", "text/plain")
	firstRec := httptest.NewRecorder()
	ArtifactUploadHandler(service)(firstRec, firstReq)
	if firstRec.Code != http.StatusCreated {
		t.Fatalf("first upload status = %d, body=%s", firstRec.Code, firstRec.Body.String())
	}

	secondReq := httptest.NewRequest(http.MethodPut, uploadURL.URL, bytes.NewBufferString("second"))
	secondReq.Header.Set("Content-Type", "text/plain")
	secondRec := httptest.NewRecorder()
	ArtifactUploadHandler(service)(secondRec, secondReq)
	if secondRec.Code != http.StatusConflict {
		t.Fatalf("second upload status = %d, want %d, body=%s", secondRec.Code, http.StatusConflict, secondRec.Body.String())
	}
}

func TestArtifactUploadHandler_InterruptedUploadReturnsBadGateway(t *testing.T) {
	t.Parallel()

	service := newTestArtifactService(t)
	created, err := service.CreateArtifact(context.Background(), storage.CreateArtifactInput{
		Filename:       "report.txt",
		ContentType:    "text/plain",
		RetentionClass: "analysis",
	})
	if err != nil {
		t.Fatalf("create artifact: %v", err)
	}
	uploadURL, err := service.IssueUploadURL(created.ID, "http://gateway.test")
	if err != nil {
		t.Fatalf("issue upload url: %v", err)
	}

	req := httptest.NewRequest(http.MethodPut, uploadURL.URL, nil)
	req.Header.Set("Content-Type", "text/plain")
	req.Body = &failingReadCloser{err: errors.New("interrupted upload")}
	rec := httptest.NewRecorder()

	ArtifactUploadHandler(service)(rec, req)

	if rec.Code != http.StatusBadGateway {
		t.Fatalf("status = %d, want %d, body=%s", rec.Code, http.StatusBadGateway, rec.Body.String())
	}

	artifact, err := service.GetArtifact(created.ID)
	if err != nil {
		t.Fatalf("get artifact: %v", err)
	}
	if artifact.Status != storage.StatusPendingUpload {
		t.Fatalf("artifact status = %q, want %q", artifact.Status, storage.StatusPendingUpload)
	}
}

func TestArtifactUploadHandler_TimeoutReturnsGatewayTimeout(t *testing.T) {
	t.Parallel()

	req := httptest.NewRequest(http.MethodPut, "/api/v1/storage/artifacts/upload/art_123?token=test", bytes.NewBufferString("hello"))
	req.Header.Set("Content-Type", "text/plain")
	rec := httptest.NewRecorder()

	ArtifactUploadHandler(stubArtifactService{uploadErr: context.DeadlineExceeded})(rec, req)

	if rec.Code != http.StatusGatewayTimeout {
		t.Fatalf("status = %d, want %d, body=%s", rec.Code, http.StatusGatewayTimeout, rec.Body.String())
	}
}

func TestArtifactHandlers_AuditLogsSuccessAndFailure(t *testing.T) {
	t.Parallel()

	var logBuffer bytes.Buffer
	original := slog.Default()
	logger := slog.New(slog.NewJSONHandler(&logBuffer, nil))
	slog.SetDefault(logger)
	t.Cleanup(func() { slog.SetDefault(original) })

	service := newTestArtifactService(t)
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/storage/artifacts/upload-url", ArtifactUploadURLHandler(service, "http://gateway.test"))
	mux.HandleFunc("/api/v1/storage/artifacts/upload/", ArtifactUploadHandler(service))
	mux.HandleFunc("/api/v1/storage/artifacts/", ArtifactMetadataHandler(service))

	createReq := httptest.NewRequest(http.MethodPost, "/api/v1/storage/artifacts/upload-url", bytes.NewBufferString(`{
		"filename":"report.txt",
		"contentType":"text/plain",
		"retentionClass":"analysis"
	}`))
	createReq.Header.Set("X-Request-ID", "req-success")
	createRec := httptest.NewRecorder()
	mux.ServeHTTP(createRec, createReq)

	var createResp storageArtifactEnvelope
	if err := json.Unmarshal(createRec.Body.Bytes(), &createResp); err != nil {
		t.Fatalf("decode create response: %v", err)
	}

	uploadReq := httptest.NewRequest(http.MethodPut, createResp.Data.Upload.URL, bytes.NewBufferString("hello audit"))
	uploadReq.Header.Set("Content-Type", "text/plain")
	uploadReq = uploadReq.WithContext(requestctx.WithRequestID(uploadReq.Context(), "req-success"))
	uploadRec := httptest.NewRecorder()
	ArtifactUploadHandler(service)(uploadRec, uploadReq)

	badReq := httptest.NewRequest(http.MethodGet, "/api/v1/storage/artifacts/"+createResp.Data.Artifact.ID+"/download?token=bad", nil)
	badReq = badReq.WithContext(requestctx.WithRequestID(badReq.Context(), "req-failure"))
	badRec := httptest.NewRecorder()
	ArtifactDownloadHandler(service)(badRec, badReq)

	logs := logBuffer.String()
	if !strings.Contains(logs, `"msg":"artifact_action"`) {
		t.Fatalf("expected artifact_action log, got %s", logs)
	}
	if !strings.Contains(logs, `"outcome":"success"`) {
		t.Fatalf("expected success audit log, got %s", logs)
	}
	if !strings.Contains(logs, `"outcome":"failure"`) {
		t.Fatalf("expected failure audit log, got %s", logs)
	}
	if !strings.Contains(logs, `"requestId":"req-success"`) {
		t.Fatalf("expected requestId req-success in audit log, got %s", logs)
	}
	if !strings.Contains(logs, `"requestId":"req-failure"`) {
		t.Fatalf("expected requestId req-failure in audit log, got %s", logs)
	}
}

type failingReadCloser struct {
	err    error
	closed bool
}

func (r *failingReadCloser) Read(_ []byte) (int, error) {
	if r.err == nil {
		r.err = errors.New("read failed")
	}
	return 0, r.err
}

func (r *failingReadCloser) Close() error {
	r.closed = true
	return nil
}

type stubArtifactService struct {
	uploadErr error
}

func (s stubArtifactService) CreateArtifact(context.Context, storage.CreateArtifactInput) (storage.Artifact, error) {
	return storage.Artifact{}, errors.New("not implemented")
}

func (s stubArtifactService) IssueUploadURL(string, string) (storage.SignedURL, error) {
	return storage.SignedURL{}, errors.New("not implemented")
}

func (s stubArtifactService) IssueDownloadURL(string, string) (storage.SignedURL, error) {
	return storage.SignedURL{}, errors.New("not implemented")
}

func (s stubArtifactService) GetArtifact(string) (storage.Artifact, error) {
	return storage.Artifact{}, errors.New("not implemented")
}

func (s stubArtifactService) UploadArtifact(context.Context, string, string, string, io.ReadCloser) error {
	return s.uploadErr
}

func (s stubArtifactService) OpenDownload(context.Context, string, string) (storage.Artifact, io.ReadCloser, error) {
	return storage.Artifact{}, nil, errors.New("not implemented")
}
