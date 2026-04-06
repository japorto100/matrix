package http

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"path/filepath"
	"strings"

	"tradeviewfusion/go-backend/internal/contracts"
	"tradeviewfusion/go-backend/internal/requestctx"
	"tradeviewfusion/go-backend/internal/storage"
)

type artifactService interface {
	CreateArtifact(ctx context.Context, input storage.CreateArtifactInput) (storage.Artifact, error)
	IssueUploadURL(artifactID, baseURL string) (storage.SignedURL, error)
	IssueDownloadURL(artifactID, baseURL string) (storage.SignedURL, error)
	GetArtifact(artifactID string) (storage.Artifact, error)
	UploadArtifact(ctx context.Context, artifactID, token, contentType string, body io.ReadCloser) error
	OpenDownload(ctx context.Context, artifactID, token string) (storage.Artifact, io.ReadCloser, error)
}

type artifactPayload struct {
	Artifact artifactDTO `json:"artifact"`
	Upload   linkDTO     `json:"upload,omitzero"`
	Download linkDTO     `json:"download,omitzero"`
}

type artifactDTO struct {
	ID             string `json:"id"`
	Filename       string `json:"filename"`
	ContentType    string `json:"contentType"`
	RetentionClass string `json:"retentionClass"`
	Status         string `json:"status"`
	SizeBytes      int64  `json:"sizeBytes,omitempty"`
	SHA256Hex      string `json:"sha256Hex,omitempty"`
}

type linkDTO struct {
	Method string `json:"method"`
	URL    string `json:"url"`
}

type artifactUploadURLRequest struct {
	Filename       string `json:"filename"`
	ContentType    string `json:"contentType"`
	RetentionClass string `json:"retentionClass"`
}

func ArtifactUploadURLHandler(service artifactService, gatewayBaseURL string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		var req artifactUploadURLRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, contracts.APIResponse[any]{Success: false, Error: fmt.Sprintf("invalid request: %v", err)})
			return
		}
		artifact, err := service.CreateArtifact(r.Context(), storage.CreateArtifactInput{
			Filename:       req.Filename,
			ContentType:    req.ContentType,
			RetentionClass: req.RetentionClass,
		})
		if err != nil {
			writeJSON(w, http.StatusBadRequest, contracts.APIResponse[any]{Success: false, Error: err.Error()})
			return
		}
		uploadURL, err := service.IssueUploadURL(artifact.ID, gatewayBaseURL)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, contracts.APIResponse[any]{Success: false, Error: "failed to issue upload url"})
			return
		}
		writeJSON(w, http.StatusCreated, contracts.APIResponse[artifactPayload]{
			Success: true,
			Data: artifactPayload{
				Artifact: artifactToDTO(artifact),
				Upload:   linkToDTO(uploadURL),
			},
		})
	}
}

func ArtifactUploadHandler(service artifactService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			w.Header().Set("Allow", http.MethodPut)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		artifactID, action := parseArtifactPath(r.URL.Path)
		if artifactID == "" || action != "upload" {
			writeJSON(w, http.StatusNotFound, contracts.APIResponse[any]{Success: false, Error: "artifact upload route not found"})
			return
		}
		if err := service.UploadArtifact(r.Context(), artifactID, r.URL.Query().Get("token"), r.Header.Get("Content-Type"), r.Body); err != nil {
			statusCode := http.StatusBadGateway
			errorClass := "storage_error"
			switch {
			case errors.Is(err, context.DeadlineExceeded):
				statusCode = http.StatusGatewayTimeout
				errorClass = "timeout"
			case errors.Is(err, context.Canceled):
				statusCode = http.StatusRequestTimeout
				errorClass = "canceled"
			case errors.Is(err, storage.ErrInvalidToken):
				statusCode = http.StatusUnauthorized
				errorClass = "invalid_token"
			case errors.Is(err, storage.ErrArtifactUploadState):
				statusCode = http.StatusConflict
				errorClass = "invalid_state"
			case errors.Is(err, storage.ErrArtifactNotFound):
				statusCode = http.StatusNotFound
				errorClass = "not_found"
			}
			logArtifactAudit(r.Context(), artifactID, "upload", "failure", statusCode, errorClass, err)
			writeJSON(w, statusCode, contracts.APIResponse[any]{Success: false, Error: err.Error()})
			return
		}
		artifact, err := service.GetArtifact(artifactID)
		if err != nil {
			logArtifactAudit(r.Context(), artifactID, "upload", "failure", http.StatusBadGateway, "metadata_lookup_failed", err)
			writeJSON(w, http.StatusBadGateway, contracts.APIResponse[any]{Success: false, Error: "artifact upload completed but metadata lookup failed"})
			return
		}
		logArtifactAudit(r.Context(), artifact.ID, "upload", "success", http.StatusCreated, "", nil)
		writeJSON(w, http.StatusCreated, contracts.APIResponse[artifactPayload]{
			Success: true,
			Data: artifactPayload{
				Artifact: artifactToDTO(artifact),
			},
		})
	}
}

func ArtifactMetadataHandler(service artifactService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "/download") {
			ArtifactDownloadHandler(service)(w, r)
			return
		}
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		artifactID, action := parseArtifactPath(r.URL.Path)
		if artifactID == "" || action != "" {
			writeJSON(w, http.StatusNotFound, contracts.APIResponse[any]{Success: false, Error: "artifact route not found"})
			return
		}
		artifact, err := service.GetArtifact(artifactID)
		if err != nil {
			statusCode := http.StatusBadGateway
			if errors.Is(err, storage.ErrArtifactNotFound) {
				statusCode = http.StatusNotFound
			}
			writeJSON(w, statusCode, contracts.APIResponse[any]{Success: false, Error: err.Error()})
			return
		}
		payload := artifactPayload{Artifact: artifactToDTO(artifact)}
		if artifact.DownloadToken != "" {
			payload.Download = linkDTO{
				Method: http.MethodGet,
				URL:    "/api/v1/storage/artifacts/" + artifact.ID + "/download?token=" + artifact.DownloadToken,
			}
		}
		writeJSON(w, http.StatusOK, contracts.APIResponse[artifactPayload]{Success: true, Data: payload})
	}
}

func ArtifactDownloadHandler(service artifactService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeJSON(w, http.StatusMethodNotAllowed, contracts.APIResponse[any]{Success: false, Error: "method not allowed"})
			return
		}
		artifactID, action := parseArtifactPath(r.URL.Path)
		if artifactID == "" || action != "download" {
			writeJSON(w, http.StatusNotFound, contracts.APIResponse[any]{Success: false, Error: "artifact download route not found"})
			return
		}
		artifact, reader, err := service.OpenDownload(r.Context(), artifactID, r.URL.Query().Get("token"))
		if err != nil {
			statusCode := http.StatusBadGateway
			errorClass := "storage_error"
			switch {
			case errors.Is(err, context.DeadlineExceeded):
				statusCode = http.StatusGatewayTimeout
				errorClass = "timeout"
			case errors.Is(err, context.Canceled):
				statusCode = http.StatusRequestTimeout
				errorClass = "canceled"
			case errors.Is(err, storage.ErrInvalidToken):
				statusCode = http.StatusUnauthorized
				errorClass = "invalid_token"
			case errors.Is(err, storage.ErrArtifactNotReady):
				statusCode = http.StatusConflict
				errorClass = "not_ready"
			case errors.Is(err, storage.ErrArtifactNotFound):
				statusCode = http.StatusNotFound
				errorClass = "not_found"
			}
			logArtifactAudit(r.Context(), artifactID, "download", "failure", statusCode, errorClass, err)
			writeJSON(w, statusCode, contracts.APIResponse[any]{Success: false, Error: err.Error()})
			return
		}
		defer func() { _ = reader.Close() }()

		w.Header().Set("Content-Type", artifact.ContentType)
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", filepath.Base(artifact.Filename)))
		w.WriteHeader(http.StatusOK)
		_, _ = io.Copy(w, reader)
		logArtifactAudit(r.Context(), artifact.ID, "download", "success", http.StatusOK, "", nil)
	}
}

func parseArtifactPath(path string) (artifactID string, action string) {
	trimmed := strings.TrimPrefix(path, "/api/v1/storage/artifacts/")
	trimmed = strings.TrimSpace(trimmed)
	if trimmed == "" {
		return "", ""
	}
	parts := strings.Split(trimmed, "/")
	if len(parts) == 1 {
		return strings.TrimSpace(parts[0]), ""
	}
	if len(parts) == 2 && strings.TrimSpace(parts[0]) == "upload" {
		return strings.TrimSpace(parts[1]), "upload"
	}
	if len(parts) == 2 {
		return strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
	}
	return "", ""
}

func artifactToDTO(artifact storage.Artifact) artifactDTO {
	return artifactDTO{
		ID:             artifact.ID,
		Filename:       artifact.Filename,
		ContentType:    artifact.ContentType,
		RetentionClass: artifact.RetentionClass,
		Status:         string(artifact.Status),
		SizeBytes:      artifact.SizeBytes,
		SHA256Hex:      artifact.SHA256Hex,
	}
}

func linkToDTO(link storage.SignedURL) linkDTO {
	return linkDTO{
		Method: link.Method,
		URL:    link.URL,
	}
}

func logArtifactAudit(ctx context.Context, artifactID, action, outcome string, statusCode int, errorClass string, err error) {
	attrs := []any{
		"kind", "artifact_action",
		"requestId", requestctx.RequestID(ctx),
		"artifactId", strings.TrimSpace(artifactID),
		"action", action,
		"outcome", outcome,
		"status", statusCode,
	}
	if strings.TrimSpace(errorClass) != "" {
		attrs = append(attrs, "errorClass", errorClass)
	}
	if err != nil {
		attrs = append(attrs, "error", err.Error())
	}
	slog.InfoContext(ctx, "artifact_action", attrs...)
}
