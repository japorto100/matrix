package http

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"matrix/go-appservice/internal/connectors/ingestion"
	"matrix/go-appservice/internal/storage"
)

// ─── Fake FilesService ──────────────────────────────────────────────

// fakeFilesService implements the filesService interface for unit tests.
// It records calls and returns pre-programmed responses/errors.
type fakeFilesService struct {
	// Canned returns — one per method. Default: zero value → success.
	listResult       *storage.FilesListResult
	listErr          error
	overviewResult   *storage.FilesOverview
	overviewErr      error
	getResult        *storage.FileRecord
	getErr           error
	deleteErr        error
	uploadIntent     *storage.UploadIntent
	uploadIntentErr  error
	markReadyResult  *storage.MarkReadyResult
	markReadyErr     error
	downloadURL      *storage.SignedURL
	downloadURLErr   error
	triggerResponse  *ingestion.IngestResponse
	triggerErr       error
	reindexResponse  *ingestion.IngestResponse
	reindexErr       error

	// Observed inputs
	lastListQuery    storage.FilesListQuery
	lastUploadInput  storage.UploadIntentInput
	lastMarkID       string
	lastMarkUserID   string
	lastMarkResult   storage.UploadResult
	lastMarkAuto     bool
	lastMarkPipeline string
	lastTriggerID    string
	lastTriggerUser  string
	lastTriggerPipe  string
	lastReindexID    string
	lastReindexUser  string
}

func (f *fakeFilesService) List(_ context.Context, q storage.FilesListQuery) (*storage.FilesListResult, error) {
	f.lastListQuery = q
	if f.listErr != nil {
		return nil, f.listErr
	}
	if f.listResult != nil {
		return f.listResult, nil
	}
	return &storage.FilesListResult{Items: []storage.FileRecord{}, Limit: q.Limit, Offset: q.Offset}, nil
}

func (f *fakeFilesService) Overview(_ context.Context, _ string) (*storage.FilesOverview, error) {
	if f.overviewErr != nil {
		return nil, f.overviewErr
	}
	if f.overviewResult != nil {
		return f.overviewResult, nil
	}
	return &storage.FilesOverview{}, nil
}

func (f *fakeFilesService) Get(_ context.Context, _, _ string) (*storage.FileRecord, error) {
	if f.getErr != nil {
		return nil, f.getErr
	}
	return f.getResult, nil
}

func (f *fakeFilesService) Delete(_ context.Context, _, _ string) error {
	return f.deleteErr
}

func (f *fakeFilesService) CreateUploadIntent(_ context.Context, input storage.UploadIntentInput, _ string) (*storage.UploadIntent, error) {
	f.lastUploadInput = input
	if f.uploadIntentErr != nil {
		return nil, f.uploadIntentErr
	}
	return f.uploadIntent, nil
}

func (f *fakeFilesService) MarkReady(_ context.Context, id, userID string, result storage.UploadResult, auto bool, pipeline string) (*storage.MarkReadyResult, error) {
	f.lastMarkID = id
	f.lastMarkUserID = userID
	f.lastMarkResult = result
	f.lastMarkAuto = auto
	f.lastMarkPipeline = pipeline
	if f.markReadyErr != nil {
		return nil, f.markReadyErr
	}
	return f.markReadyResult, nil
}

func (f *fakeFilesService) IssueDownloadURL(_ context.Context, _, _, _ string) (*storage.SignedURL, error) {
	if f.downloadURLErr != nil {
		return nil, f.downloadURLErr
	}
	return f.downloadURL, nil
}

func (f *fakeFilesService) TriggerIngestion(_ context.Context, id, userID, pipeline string) (*ingestion.IngestResponse, error) {
	f.lastTriggerID = id
	f.lastTriggerUser = userID
	f.lastTriggerPipe = pipeline
	if f.triggerErr != nil {
		return nil, f.triggerErr
	}
	return f.triggerResponse, nil
}

func (f *fakeFilesService) Reindex(_ context.Context, id, userID string) (*ingestion.IngestResponse, error) {
	f.lastReindexID = id
	f.lastReindexUser = userID
	if f.reindexErr != nil {
		return nil, f.reindexErr
	}
	return f.reindexResponse, nil
}

// ─── Helpers ────────────────────────────────────────────────────────

// doRequest is a small helper that runs an http.HandlerFunc against an
// httptest ResponseRecorder and returns it for inspection.
func doRequest(h http.HandlerFunc, method, path string, body any, userID string) *httptest.ResponseRecorder {
	var reader *bytes.Reader
	if body != nil {
		b, _ := json.Marshal(body)
		reader = bytes.NewReader(b)
	} else {
		reader = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, path, reader)
	if userID != "" {
		req.Header.Set("X-Actor-User-Id", userID)
	}
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)
	return rec
}

// ─── FilesListHandler tests ─────────────────────────────────────────

func TestFilesListHandler_ParsesQueryParams(t *testing.T) {
	svc := &fakeFilesService{}
	h := FilesListHandler(svc)
	rec := doRequest(h, http.MethodGet, "/api/v1/files?type=audio&status=ready&limit=25&offset=10&search=song", nil, "alice")
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if svc.lastListQuery.UserID != "alice" {
		t.Errorf("UserID = %q, want alice", svc.lastListQuery.UserID)
	}
	if svc.lastListQuery.MediaType != storage.MediaTypeAudio {
		t.Errorf("MediaType = %q, want audio", svc.lastListQuery.MediaType)
	}
	if svc.lastListQuery.Status != "ready" {
		t.Errorf("Status = %q, want ready", svc.lastListQuery.Status)
	}
	if svc.lastListQuery.Limit != 25 {
		t.Errorf("Limit = %d, want 25", svc.lastListQuery.Limit)
	}
	if svc.lastListQuery.Offset != 10 {
		t.Errorf("Offset = %d, want 10", svc.lastListQuery.Offset)
	}
	if svc.lastListQuery.Search != "song" {
		t.Errorf("Search = %q, want song", svc.lastListQuery.Search)
	}
}

func TestFilesListHandler_LimitClamped(t *testing.T) {
	svc := &fakeFilesService{}
	h := FilesListHandler(svc)
	// Out-of-range → clamped to default 50
	doRequest(h, http.MethodGet, "/api/v1/files?limit=9999", nil, "alice")
	if svc.lastListQuery.Limit != 50 {
		t.Errorf("Limit = %d, want 50 (clamped)", svc.lastListQuery.Limit)
	}
	doRequest(h, http.MethodGet, "/api/v1/files?limit=-5", nil, "alice")
	if svc.lastListQuery.Limit != 50 {
		t.Errorf("Limit = %d, want 50 (negative → default)", svc.lastListQuery.Limit)
	}
}

func TestFilesListHandler_ForbiddenMapsTo403(t *testing.T) {
	svc := &fakeFilesService{listErr: storage.ErrForbidden}
	rec := doRequest(FilesListHandler(svc), http.MethodGet, "/api/v1/files", nil, "")
	if rec.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "forbidden") {
		t.Errorf("body should contain 'forbidden': %s", rec.Body.String())
	}
}

func TestFilesListHandler_MethodNotAllowed(t *testing.T) {
	svc := &fakeFilesService{}
	rec := doRequest(FilesListHandler(svc), http.MethodPost, "/api/v1/files", nil, "alice")
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

// ─── FilesItemHandler routing tests ─────────────────────────────────

func TestFilesItemHandler_GetDispatch(t *testing.T) {
	svc := &fakeFilesService{
		getResult: &storage.FileRecord{ID: "a1", Name: "doc.pdf"},
	}
	h := FilesItemHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodGet, "/api/v1/files/a1", nil, "alice")
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"id":"a1"`) {
		t.Errorf("body should contain id a1: %s", rec.Body.String())
	}
}

func TestFilesItemHandler_DeleteDispatch(t *testing.T) {
	svc := &fakeFilesService{}
	h := FilesItemHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodDelete, "/api/v1/files/a1", nil, "alice")
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}

func TestFilesItemHandler_DownloadURLDispatch(t *testing.T) {
	svc := &fakeFilesService{
		downloadURL: &storage.SignedURL{
			Method: "GET", URL: "http://signed.example/doc.pdf?token=abc",
			ExpiresAt: time.Now().Add(15 * time.Minute),
		},
	}
	h := FilesItemHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodGet, "/api/v1/files/a1/url", nil, "alice")
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "signed.example") {
		t.Errorf("body should contain signed URL: %s", rec.Body.String())
	}
}

func TestFilesItemHandler_MarkReadyDispatch(t *testing.T) {
	svc := &fakeFilesService{
		markReadyResult: &storage.MarkReadyResult{MarkedReady: true, IngestTriggered: true, IngestJobID: "j1"},
	}
	h := FilesItemHandler(svc, "http://localhost:8090")
	body := filesMarkReadyRequest{
		SizeBytes:  4096,
		SHA256Hex:  "deadbeef",
		AutoIngest: true,
	}
	rec := doRequest(h, http.MethodPost, "/api/v1/files/a1/mark-ready", body, "alice")
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if svc.lastMarkID != "a1" {
		t.Errorf("lastMarkID = %q, want a1", svc.lastMarkID)
	}
	if svc.lastMarkUserID != "alice" {
		t.Errorf("lastMarkUserID = %q, want alice", svc.lastMarkUserID)
	}
	if !svc.lastMarkAuto {
		t.Error("lastMarkAuto should be true")
	}
	if svc.lastMarkResult.SizeBytes != 4096 {
		t.Errorf("lastMarkResult.SizeBytes = %d, want 4096", svc.lastMarkResult.SizeBytes)
	}
	if svc.lastMarkResult.SHA256Hex != "deadbeef" {
		t.Errorf("lastMarkResult.SHA256Hex = %q, want deadbeef", svc.lastMarkResult.SHA256Hex)
	}
}

// TestFilesItemHandler_MarkReadyPartialSuccessReturns207 — Fix #5: when
// mark-ready succeeds but auto-ingest fails, the API returns 207 Multi-Status.
func TestFilesItemHandler_MarkReadyPartialSuccessReturns207(t *testing.T) {
	svc := &fakeFilesService{
		markReadyResult: &storage.MarkReadyResult{
			MarkedReady: true,
			IngestError: "ingestion worker unreachable",
		},
	}
	h := FilesItemHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodPost, "/api/v1/files/a1/mark-ready", filesMarkReadyRequest{AutoIngest: true}, "alice")
	if rec.Code != http.StatusMultiStatus {
		t.Errorf("status = %d, want 207 (partial success)", rec.Code)
	}
}

func TestFilesItemHandler_TriggerIngestDispatch(t *testing.T) {
	svc := &fakeFilesService{
		triggerResponse: &ingestion.IngestResponse{JobID: "job-42", Status: "pending"},
	}
	h := FilesItemHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodPost, "/api/v1/files/a1/ingest", filesTriggerIngestRequest{Pipeline: "document"}, "alice")
	if rec.Code != http.StatusAccepted {
		t.Errorf("status = %d, want 202", rec.Code)
	}
	if svc.lastTriggerPipe != "document" {
		t.Errorf("lastTriggerPipe = %q, want document", svc.lastTriggerPipe)
	}
}

func TestFilesItemHandler_ReindexDispatch(t *testing.T) {
	svc := &fakeFilesService{
		reindexResponse: &ingestion.IngestResponse{JobID: "job-new", Status: "pending"},
	}
	h := FilesItemHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodPost, "/api/v1/files/a1/reindex", nil, "alice")
	if rec.Code != http.StatusAccepted {
		t.Errorf("status = %d, want 202", rec.Code)
	}
	if svc.lastReindexID != "a1" {
		t.Errorf("lastReindexID = %q, want a1", svc.lastReindexID)
	}
}

// ─── Error mapping tests ────────────────────────────────────────────

func TestFilesItemHandler_ErrorMapping(t *testing.T) {
	cases := []struct {
		name       string
		svcErr     error
		wantStatus int
	}{
		{"forbidden", storage.ErrForbidden, http.StatusForbidden},
		{"not found", storage.ErrArtifactNotFound, http.StatusNotFound},
		{"not ready", storage.ErrArtifactNotReady, http.StatusConflict},
		{"upload state", storage.ErrArtifactUploadState, http.StatusConflict},
		{"invalid token", storage.ErrInvalidToken, http.StatusUnauthorized},
		{"unsupported pipeline", storage.ErrUnsupportedPipelineForArtifact, http.StatusUnprocessableEntity},
		{"pipeline not implemented", ingestion.ErrPipelineNotImplemented, http.StatusNotImplemented},
		{"deadline", context.DeadlineExceeded, http.StatusGatewayTimeout},
		{"canceled", context.Canceled, http.StatusRequestTimeout},
		{"unknown", errors.New("boom"), http.StatusInternalServerError},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			svc := &fakeFilesService{getErr: tc.svcErr}
			h := FilesItemHandler(svc, "http://localhost:8090")
			rec := doRequest(h, http.MethodGet, "/api/v1/files/a1", nil, "alice")
			if rec.Code != tc.wantStatus {
				t.Errorf("err=%q: status = %d, want %d", tc.name, rec.Code, tc.wantStatus)
			}
		})
	}
}

// ─── Upload Intent handler ──────────────────────────────────────────

func TestFilesUploadIntentHandler_Success(t *testing.T) {
	svc := &fakeFilesService{
		uploadIntent: &storage.UploadIntent{
			Artifact:     storage.Artifact{ID: "art_new", Filename: "doc.pdf"},
			UploadURL:    "http://signed.example/upload",
			UploadMethod: "PUT",
			Token:        "token-abc",
			ExpiresAt:    time.Now().Add(15 * time.Minute),
		},
	}
	h := FilesUploadIntentHandler(svc, "http://localhost:8090")
	body := filesUploadIntentRequest{
		Filename:    "doc.pdf",
		ContentType: "application/pdf",
		AutoIngest:  true,
	}
	rec := doRequest(h, http.MethodPost, "/api/v1/files/upload-intent", body, "alice")
	if rec.Code != http.StatusCreated {
		t.Errorf("status = %d, want 201", rec.Code)
	}
	if svc.lastUploadInput.UserID != "alice" {
		t.Errorf("UserID = %q, want alice", svc.lastUploadInput.UserID)
	}
	if svc.lastUploadInput.Filename != "doc.pdf" {
		t.Errorf("Filename = %q, want doc.pdf", svc.lastUploadInput.Filename)
	}
	if !svc.lastUploadInput.AutoIngest {
		t.Error("AutoIngest should be true")
	}
}

func TestFilesUploadIntentHandler_MissingFilenameReturns400(t *testing.T) {
	svc := &fakeFilesService{}
	h := FilesUploadIntentHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodPost, "/api/v1/files/upload-intent", filesUploadIntentRequest{ContentType: "x"}, "alice")
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", rec.Code)
	}
}

func TestFilesUploadIntentHandler_MethodNotAllowed(t *testing.T) {
	svc := &fakeFilesService{}
	h := FilesUploadIntentHandler(svc, "http://localhost:8090")
	rec := doRequest(h, http.MethodGet, "/api/v1/files/upload-intent", nil, "alice")
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

// ─── parseFileID unit tests ─────────────────────────────────────────

func TestParseFileID(t *testing.T) {
	cases := []struct {
		path    string
		wantID  string
		wantSub string
		wantOK  bool
	}{
		{"/api/v1/files/a1", "a1", "", true},
		{"/api/v1/files/a1/", "a1", "", true},
		{"/api/v1/files/a1/url", "a1", "url", true},
		{"/api/v1/files/a1/mark-ready", "a1", "mark-ready", true},
		{"/api/v1/files/upload-intent", "upload-intent", "", true},
		{"/api/v1/files/overview", "overview", "", true},
		{"/api/v1/files/", "", "", false},
		{"/api/v1/files", "", "", false},
		{"/something/else", "", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			gotID, gotSub, gotOK := parseFileID(tc.path)
			if gotID != tc.wantID || gotSub != tc.wantSub || gotOK != tc.wantOK {
				t.Errorf("parseFileID(%q) = (%q, %q, %v), want (%q, %q, %v)",
					tc.path, gotID, gotSub, gotOK, tc.wantID, tc.wantSub, tc.wantOK)
			}
		})
	}
}
