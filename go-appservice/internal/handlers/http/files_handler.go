// Package http — Files API handlers (exec-19 Stufe 3).
//
// These handlers are the HTTP adapter over storage.FilesService. They:
//  1. Parse X-Actor-User-Id header (set by the control-ui BFF)
//  2. Parse query params / JSON bodies into Go types
//  3. Delegate to FilesService for business logic
//  4. Map service errors to HTTP status codes
//  5. Serialise *FileRecord / *FilesListResult / etc. into JSON
//
// The FilesService is protocol-agnostic — it neither sees the http.Request
// nor the ResponseWriter. See internal/storage/files_service.go for the
// business layer. See specs/17-schema-ownership.md for the trust model
// around X-Actor-User-Id.
package http

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"matrix/go-appservice/internal/connectors/ingestion"
	"matrix/go-appservice/internal/contracts"
	"matrix/go-appservice/internal/storage"
)

// filesService is the subset of storage.FilesService consumed by the
// handlers. Defining it here (duck-typing) makes the handlers trivially
// testable with an in-memory fake and avoids importing the concrete type
// in test files.
type filesService interface {
	List(ctx context.Context, query storage.FilesListQuery) (*storage.FilesListResult, error)
	Overview(ctx context.Context, userID string) (*storage.FilesOverview, error)
	Get(ctx context.Context, artifactID, userID string) (*storage.FileRecord, error)
	Delete(ctx context.Context, artifactID, userID string) error
	CreateUploadIntent(ctx context.Context, input storage.UploadIntentInput, gatewayBaseURL string) (*storage.UploadIntent, error)
	MarkReady(ctx context.Context, artifactID, userID string, result storage.UploadResult, autoIngest bool, pipeline string) (*storage.MarkReadyResult, error)
	IssueDownloadURL(ctx context.Context, artifactID, userID, gatewayBaseURL string) (*storage.SignedURL, error)
	TriggerIngestion(ctx context.Context, artifactID, userID, pipeline string) (*ingestion.IngestResponse, error)
	Reindex(ctx context.Context, artifactID, userID string) (*ingestion.IngestResponse, error)
}

// ─── Error mapping ───────────────────────────────────────────────────

// mapFilesError translates FilesService errors to HTTP status + error code.
func mapFilesError(err error) (int, string) {
	switch {
	case errors.Is(err, context.DeadlineExceeded):
		return http.StatusGatewayTimeout, "timeout"
	case errors.Is(err, context.Canceled):
		return http.StatusRequestTimeout, "canceled"
	case errors.Is(err, storage.ErrForbidden):
		return http.StatusForbidden, "forbidden"
	case errors.Is(err, storage.ErrArtifactNotFound):
		return http.StatusNotFound, "artifact_not_found"
	case errors.Is(err, storage.ErrArtifactNotReady):
		return http.StatusConflict, "artifact_not_ready"
	case errors.Is(err, storage.ErrArtifactUploadState):
		return http.StatusConflict, "invalid_upload_state"
	case errors.Is(err, storage.ErrInvalidToken):
		return http.StatusUnauthorized, "invalid_token"
	case errors.Is(err, storage.ErrUnsupportedPipelineForArtifact):
		return http.StatusUnprocessableEntity, "unsupported_pipeline"
	case errors.Is(err, ingestion.ErrPipelineNotImplemented):
		return http.StatusNotImplemented, "pipeline_not_implemented"
	default:
		return http.StatusInternalServerError, "internal_error"
	}
}

func writeFilesError(w http.ResponseWriter, err error) {
	status, code := mapFilesError(err)
	writeJSON(w, status, contracts.APIResponse[any]{
		Success: false,
		Error:   fmt.Sprintf("%s: %v", code, err),
	})
}

// ─── Path helpers ────────────────────────────────────────────────────

// parseFileID extracts {id} from paths like /api/v1/files/{id} or
// /api/v1/files/{id}/url, /api/v1/files/{id}/ingest, etc.
// Returns (id, subResource, ok).
// Example: /api/v1/files/art_abc/url → ("art_abc", "url", true)
func parseFileID(path string) (id, sub string, ok bool) {
	trimmed := strings.TrimPrefix(path, "/api/v1/files/")
	if trimmed == path {
		return "", "", false
	}
	parts := strings.SplitN(strings.Trim(trimmed, "/"), "/", 2)
	if len(parts) == 0 || parts[0] == "" {
		return "", "", false
	}
	if len(parts) == 1 {
		return parts[0], "", true
	}
	return parts[0], parts[1], true
}

// ─── Request bodies ──────────────────────────────────────────────────

type filesUploadIntentRequest struct {
	Filename       string `json:"filename"`
	ContentType    string `json:"content_type"`
	RetentionClass string `json:"retention_class,omitempty"`
	SizeBytes      int64  `json:"size_bytes,omitempty"`
	AutoIngest     bool   `json:"auto_ingest,omitempty"`
	IngestPipeline string `json:"ingest_pipeline,omitempty"`
}

type filesMarkReadyRequest struct {
	SizeBytes      int64  `json:"size_bytes,omitempty"`
	SHA256Hex      string `json:"sha256_hex,omitempty"`
	AutoIngest     bool   `json:"auto_ingest,omitempty"`
	IngestPipeline string `json:"ingest_pipeline,omitempty"`
}

type filesTriggerIngestRequest struct {
	Pipeline string `json:"pipeline,omitempty"` // empty = auto-detect by media type
}

// ─── FilesListHandler — GET /api/v1/files ────────────────────────────

// FilesListHandler returns a filtered, paginated list of files owned by
// the requesting user. Query params:
//
//	?user (fallback if X-Actor-User-Id missing)
//	?type=document|image|audio|video|data|other
//	?status=ready|pending_upload|upload_failed|orphan
//	?search=foo (filename substring, case-insensitive)
//	?limit=50 (1..500)
//	?offset=0
func FilesListHandler(service filesService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		userID := actorUserID(r)
		q := r.URL.Query()
		limit := clampInt(parseInt(q.Get("limit"), 50), 1, 500, 50)
		offset := max(parseInt(q.Get("offset"), 0), 0)
		query := storage.FilesListQuery{
			UserID:    userID,
			MediaType: storage.MediaType(strings.TrimSpace(q.Get("type"))),
			Status:    strings.TrimSpace(q.Get("status")),
			Search:    strings.TrimSpace(q.Get("search")),
			Limit:     limit,
			Offset:    offset,
		}
		result, err := service.List(r.Context(), query)
		if err != nil {
			writeFilesError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, contracts.APIResponse[*storage.FilesListResult]{
			Success: true,
			Data:    result,
		})
	}
}

// ─── FilesOverviewHandler — GET /api/v1/files/overview ───────────────

func FilesOverviewHandler(service filesService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		userID := actorUserID(r)
		result, err := service.Overview(r.Context(), userID)
		if err != nil {
			writeFilesError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, contracts.APIResponse[*storage.FilesOverview]{
			Success: true,
			Data:    result,
		})
	}
}

// ─── FilesUploadIntentHandler — POST /api/v1/files/upload-intent ─────

func FilesUploadIntentHandler(service filesService, gatewayBaseURL string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		var req filesUploadIntentRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, contracts.APIResponse[any]{
				Success: false, Error: fmt.Sprintf("invalid request: %v", err),
			})
			return
		}
		if strings.TrimSpace(req.Filename) == "" {
			writeJSON(w, http.StatusBadRequest, contracts.APIResponse[any]{
				Success: false, Error: "filename required",
			})
			return
		}
		userID := actorUserID(r)
		input := storage.UploadIntentInput{
			UserID:         userID,
			Filename:       req.Filename,
			ContentType:    req.ContentType,
			RetentionClass: req.RetentionClass,
			SizeBytes:      req.SizeBytes,
			AutoIngest:     req.AutoIngest,
			IngestPipeline: req.IngestPipeline,
		}
		intent, err := service.CreateUploadIntent(r.Context(), input, gatewayBaseURL)
		if err != nil {
			writeFilesError(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, contracts.APIResponse[*storage.UploadIntent]{
			Success: true,
			Data:    intent,
		})
	}
}

// ─── Per-file route multiplexer ──────────────────────────────────────

// FilesItemHandler dispatches /api/v1/files/{id}[/sub] based on sub-path
// and HTTP method. One handler instead of many because the Go stdlib
// mux needs distinct patterns — keeping routing in code is simpler.
//
// Sub-routes handled:
//
//	(none)         GET    → Get
//	(none)         DELETE → Delete
//	url            GET    → IssueDownloadURL
//	mark-ready     POST   → MarkReady
//	ingest         POST   → TriggerIngestion
//	reindex        POST   → Reindex
func FilesItemHandler(service filesService, gatewayBaseURL string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, sub, ok := parseFileID(r.URL.Path)
		if !ok || id == "" {
			writeJSON(w, http.StatusNotFound, contracts.APIResponse[any]{Success: false, Error: "not found"})
			return
		}

		// Handle "/api/v1/files/upload-intent" — POST creates a new intent.
		// That path shares the /api/v1/files/ prefix but is NOT a per-id
		// route, so we dispatch it here.
		if id == "upload-intent" && sub == "" {
			FilesUploadIntentHandler(service, gatewayBaseURL)(w, r)
			return
		}
		// Handle "/api/v1/files/overview"
		if id == "overview" && sub == "" {
			FilesOverviewHandler(service)(w, r)
			return
		}

		userID := actorUserID(r)
		switch sub {
		case "":
			switch r.Method {
			case http.MethodGet:
				filesGet(w, r, service, id, userID)
			case http.MethodDelete:
				filesDelete(w, r, service, id, userID)
			default:
				w.Header().Set("Allow", "GET, DELETE")
				writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			}
		case "url":
			if r.Method != http.MethodGet {
				w.Header().Set("Allow", http.MethodGet)
				writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
				return
			}
			filesDownloadURL(w, r, service, id, userID, gatewayBaseURL)
		case "mark-ready":
			if r.Method != http.MethodPost {
				w.Header().Set("Allow", http.MethodPost)
				writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
				return
			}
			filesMarkReady(w, r, service, id, userID)
		case "ingest":
			if r.Method != http.MethodPost {
				w.Header().Set("Allow", http.MethodPost)
				writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
				return
			}
			filesTriggerIngest(w, r, service, id, userID)
		case "reindex":
			if r.Method != http.MethodPost {
				w.Header().Set("Allow", http.MethodPost)
				writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
				return
			}
			filesReindex(w, r, service, id, userID)
		default:
			writeJSON(w, http.StatusNotFound, contracts.APIResponse[any]{Success: false, Error: "unknown sub-resource"})
		}
	}
}

// ─── Per-sub-route handler internals ─────────────────────────────────

func filesGet(w http.ResponseWriter, r *http.Request, service filesService, id, userID string) {
	rec, err := service.Get(r.Context(), id, userID)
	if err != nil {
		writeFilesError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, contracts.APIResponse[*storage.FileRecord]{
		Success: true, Data: rec,
	})
}

func filesDelete(w http.ResponseWriter, r *http.Request, service filesService, id, userID string) {
	if err := service.Delete(r.Context(), id, userID); err != nil {
		writeFilesError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, contracts.APIResponse[any]{
		Success: true,
	})
}

func filesDownloadURL(w http.ResponseWriter, r *http.Request, service filesService, id, userID, gatewayBaseURL string) {
	signed, err := service.IssueDownloadURL(r.Context(), id, userID, gatewayBaseURL)
	if err != nil {
		writeFilesError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, contracts.APIResponse[*storage.SignedURL]{
		Success: true, Data: signed,
	})
}

func filesMarkReady(w http.ResponseWriter, r *http.Request, service filesService, id, userID string) {
	var req filesMarkReadyRequest
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, contracts.APIResponse[any]{
			Success: false, Error: fmt.Sprintf("invalid request: %v", err),
		})
		return
	}
	result, err := service.MarkReady(r.Context(), id, userID, storage.UploadResult{
		SizeBytes:  req.SizeBytes,
		SHA256Hex:  req.SHA256Hex,
		UploadedAt: time.Now().UTC(),
	}, req.AutoIngest, req.IngestPipeline)
	if err != nil {
		writeFilesError(w, err)
		return
	}
	// exec-19 Review Fix #5: MarkedReady=true + IngestError!="" → 207 Multi-Status
	status := http.StatusOK
	if result.MarkedReady && result.IngestError != "" {
		status = http.StatusMultiStatus
	}
	writeJSON(w, status, contracts.APIResponse[*storage.MarkReadyResult]{
		Success: true, Data: result,
	})
}

func filesTriggerIngest(w http.ResponseWriter, r *http.Request, service filesService, id, userID string) {
	var req filesTriggerIngestRequest
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, contracts.APIResponse[any]{
			Success: false, Error: fmt.Sprintf("invalid request: %v", err),
		})
		return
	}
	resp, err := service.TriggerIngestion(r.Context(), id, userID, req.Pipeline)
	if err != nil {
		writeFilesError(w, err)
		return
	}
	writeJSON(w, http.StatusAccepted, contracts.APIResponse[*ingestion.IngestResponse]{
		Success: true, Data: resp,
	})
}

func filesReindex(w http.ResponseWriter, r *http.Request, service filesService, id, userID string) {
	resp, err := service.Reindex(r.Context(), id, userID)
	if err != nil {
		writeFilesError(w, err)
		return
	}
	writeJSON(w, http.StatusAccepted, contracts.APIResponse[*ingestion.IngestResponse]{
		Success: true, Data: resp,
	})
}

// parseInt is a forgiving integer parser for query params.
func parseInt(s string, fallback int) int {
	if s == "" {
		return fallback
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return fallback
	}
	return n
}
