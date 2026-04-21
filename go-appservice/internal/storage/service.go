package storage

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"path"
	"path/filepath"
	"strings"
	"time"
)

type Config struct {
	Provider      ProviderKind
	BaseDir       string
	SigningSecret string
	TTL           time.Duration
	Store         MetadataStore
	S3            S3Config
	NowFunc       func() time.Time
}

type Service struct {
	store    MetadataStore
	provider Provider
	signer   *Signer
	ttl      time.Duration
	nowFunc  func() time.Time
}

func NewService(cfg Config) (*Service, error) {
	if cfg.Store == nil {
		return nil, fmt.Errorf("metadata store required")
	}
	if strings.TrimSpace(cfg.SigningSecret) == "" {
		return nil, fmt.Errorf("signing secret required")
	}
	nowFunc := cfg.NowFunc
	if nowFunc == nil {
		nowFunc = func() time.Time { return time.Now().UTC() }
	}
	ttl := cfg.TTL
	if ttl <= 0 {
		ttl = 15 * time.Minute
	}

	var provider Provider
	switch cfg.Provider {
	case "", ProviderFilesystem:
		fsProvider, err := NewFilesystemProvider(cfg.BaseDir)
		if err != nil {
			return nil, err
		}
		provider = fsProvider
	case ProviderS3, ProviderSeaweedFS, ProviderGarage:
		s3Provider, err := NewS3Provider(context.Background(), cfg.S3)
		if err != nil {
			return nil, err
		}
		provider = s3Provider
	default:
		return nil, fmt.Errorf("unsupported artifact provider %q", cfg.Provider)
	}

	return &Service{
		store:    cfg.Store,
		provider: provider,
		signer:   NewSigner(cfg.SigningSecret),
		ttl:      ttl,
		nowFunc:  nowFunc,
	}, nil
}

func (s *Service) CreateArtifact(ctx context.Context, input CreateArtifactInput) (Artifact, error) {
	now := s.nowFunc().UTC()
	filename := strings.TrimSpace(input.Filename)
	if filename == "" {
		return Artifact{}, fmt.Errorf("filename required")
	}
	contentType := strings.TrimSpace(input.ContentType)
	if contentType == "" {
		contentType = "application/octet-stream"
	}
	retentionClass := strings.TrimSpace(input.RetentionClass)
	if retentionClass == "" {
		retentionClass = "standard"
	}
	userID := strings.TrimSpace(input.UserID)
	artifactID := newArtifactID()
	objectKey := strings.TrimSpace(input.ObjectKey)
	if objectKey == "" {
		objectKey = defaultObjectKey(now, artifactID, filename, userID)
	}

	artifact := Artifact{
		ID:             artifactID,
		UserID:         userID,
		MediaType:      ClassifyMediaType(contentType, filename),
		ObjectKey:      objectKey,
		Filename:       filepath.Base(filename),
		ContentType:    contentType,
		RetentionClass: retentionClass,
		Status:         StatusPendingUpload,
		CreatedAt:      now,
		UpdatedAt:      now,
		ExpiresAt:      now.Add(s.ttl),
	}
	if err := s.store.Create(artifact); err != nil {
		return Artifact{}, fmt.Errorf("create artifact metadata %s: %w", artifact.ID, err)
	}
	return artifact, nil
}

// DeleteArtifact removes the object from the provider and the metadata row.
// Caller must verify ownership (user_id match) before calling.
// exec-19 Stufe 3.
func (s *Service) DeleteArtifact(ctx context.Context, artifactID string) error {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	// Try deleting the object. If the provider lacks a Delete method or the
	// object is already gone, we still proceed to remove the metadata row so
	// orphaned rows do not accumulate.
	if deleter, ok := s.provider.(interface {
		Delete(ctx context.Context, key string) error
	}); ok {
		if delErr := deleter.Delete(ctx, artifact.ObjectKey); delErr != nil {
			// log and continue — metadata cleanup is the priority
			_ = delErr
		}
	}
	if err := s.store.Delete(artifactID); err != nil {
		return fmt.Errorf("delete artifact %s: %w", artifactID, err)
	}
	return nil
}

// Store exposes the underlying metadata store for read-only file listing.
// Used by FilesService to join artifacts with ingestion jobs.
func (s *Service) Store() MetadataStore {
	return s.store
}

// Provider exposes the underlying blob provider so callers can
// type-assert to optional capability interfaces (e.g. ObjectLister for
// S3). exec-19 Stufe 3.
func (s *Service) Provider() Provider {
	return s.provider
}

// IssueUploadURL signs a token bound to the artifact owner. The userID
// parameter MUST match the artifact's owning user; otherwise the function
// errors — this prevents a handler bug from silently issuing tokens on
// behalf of the wrong user. exec-19 Phase 2 (A).
func (s *Service) IssueUploadURL(artifactID, userID, baseURL string) (SignedURL, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return SignedURL{}, fmt.Errorf("load artifact %s for upload url: %w", artifactID, err)
	}
	if artifact.Status != StatusPendingUpload {
		return SignedURL{}, ErrArtifactUploadState
	}
	if err := s.assertOwnership(artifact, userID); err != nil {
		return SignedURL{}, err
	}
	return s.issueSignedURL(artifact.ID, userID, ActionUpload, baseURL, "/api/v1/storage/artifacts/upload/"+artifact.ID)
}

func (s *Service) IssueDownloadURL(artifactID, userID, baseURL string) (SignedURL, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return SignedURL{}, fmt.Errorf("load artifact %s for download url: %w", artifactID, err)
	}
	if artifact.Status != StatusReady {
		return SignedURL{}, ErrArtifactNotReady
	}
	if err := s.assertOwnership(artifact, userID); err != nil {
		return SignedURL{}, err
	}
	return s.issueSignedURL(artifact.ID, userID, ActionDownload, baseURL, "/api/v1/storage/artifacts/"+artifact.ID+"/download")
}

func (s *Service) GetArtifact(artifactID, userID string) (Artifact, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return Artifact{}, fmt.Errorf("load artifact %s: %w", artifactID, err)
	}
	if err := s.assertOwnership(artifact, userID); err != nil {
		return Artifact{}, err
	}
	if artifact.Status == StatusReady {
		token, err := s.signer.Issue(TokenClaims{
			ArtifactID: artifact.ID,
			UserID:     userID,
			Action:     ActionDownload,
			ExpiresAt:  s.nowFunc().UTC().Add(s.ttl),
		}, s.nowFunc().UTC())
		if err != nil {
			return Artifact{}, err
		}
		artifact.DownloadToken = token
	}
	return artifact, nil
}

// UploadArtifact verifies the token's UserID matches the request user (passed
// via requestUserID). Even if an attacker obtains a signed upload URL and
// replays it, they cannot succeed unless they can also impersonate the
// original user at the HTTP handler layer.
func (s *Service) UploadArtifact(ctx context.Context, artifactID, requestUserID, token, contentType string, body io.ReadCloser) error {
	defer func() {
		if body != nil {
			_ = body.Close()
		}
	}()
	claims, err := s.signer.Verify(token, s.nowFunc().UTC())
	if err != nil || claims.ArtifactID != artifactID || claims.Action != ActionUpload {
		return ErrInvalidToken
	}
	// exec-19 Phase 2 (A): token must be bound to the request user. A token
	// with an empty UserID is rejected — new call-sites always set it.
	if claims.UserID == "" || claims.UserID != requestUserID {
		return ErrInvalidToken
	}
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return fmt.Errorf("load artifact %s for upload: %w", artifactID, err)
	}
	if ownErr := s.assertOwnership(artifact, requestUserID); ownErr != nil {
		return ownErr
	}
	if artifact.Status != StatusPendingUpload {
		return ErrArtifactUploadState
	}
	if providedType := strings.TrimSpace(contentType); providedType != "" && artifact.ContentType != "" && !strings.EqualFold(providedType, artifact.ContentType) {
		return fmt.Errorf("upload content type mismatch: got %q want %q", providedType, artifact.ContentType)
	}
	result, putErr := s.provider.Put(ctx, artifact.ObjectKey, body)
	if putErr != nil {
		return fmt.Errorf("store artifact object %s: %w", artifact.ObjectKey, putErr)
	}
	if result.UploadedAt.IsZero() {
		result.UploadedAt = s.nowFunc().UTC()
	}
	if err := s.store.MarkUploaded(artifactID, result); err != nil {
		return fmt.Errorf("mark artifact %s uploaded: %w", artifactID, err)
	}
	return nil
}

func (s *Service) OpenDownload(ctx context.Context, artifactID, requestUserID, token string) (Artifact, io.ReadCloser, error) {
	claims, err := s.signer.Verify(token, s.nowFunc().UTC())
	if err != nil || claims.ArtifactID != artifactID || claims.Action != ActionDownload {
		return Artifact{}, nil, ErrInvalidToken
	}
	if claims.UserID == "" || claims.UserID != requestUserID {
		return Artifact{}, nil, ErrInvalidToken
	}
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return Artifact{}, nil, fmt.Errorf("load artifact %s for download: %w", artifactID, err)
	}
	if ownErr := s.assertOwnership(artifact, requestUserID); ownErr != nil {
		return Artifact{}, nil, ownErr
	}
	if artifact.Status != StatusReady {
		return Artifact{}, nil, ErrArtifactNotReady
	}
	reader, getErr := s.provider.Get(ctx, artifact.ObjectKey)
	if getErr != nil {
		return Artifact{}, nil, fmt.Errorf("open artifact object %s: %w", artifact.ObjectKey, getErr)
	}
	return artifact, reader, nil
}

// assertOwnership is a defense-in-depth ownership check inside the Service
// layer. The authoritative gate is FilesService.checkOwnership (exec-19
// Review Fix #6) but we keep this here because legacy call-sites in
// artifact_handler.go still call Service methods directly. Behavior:
// - empty artifact.UserID: allowed (legacy row, caller's responsibility)
// - empty request userID: forbidden
// - mismatch: forbidden
//
// NOTE: FilesService does NOT call this — it uses its own checkOwnership
// which is the single source of truth for the Files API. Service's
// ownership check is reached only via direct artifact_handler.go paths
// (upload URL issue, upload proxy, download proxy).
func (s *Service) assertOwnership(artifact Artifact, userID string) error {
	if artifact.UserID == "" {
		return nil // legacy artifact, no owner recorded
	}
	if strings.TrimSpace(userID) == "" {
		return ErrForbidden
	}
	if artifact.UserID != userID {
		return ErrForbidden
	}
	return nil
}

func (s *Service) issueSignedURL(artifactID, userID string, action Action, baseURL, routePath string) (SignedURL, error) {
	now := s.nowFunc().UTC()
	expiresAt := now.Add(s.ttl)
	token, err := s.signer.Issue(TokenClaims{
		ArtifactID: artifactID,
		UserID:     userID,
		Action:     action,
		ExpiresAt:  expiresAt,
	}, now)
	if err != nil {
		return SignedURL{}, err
	}
	method := "GET"
	if action == ActionUpload {
		method = "PUT"
	}
	return SignedURL{
		Method:    method,
		Token:     token,
		ExpiresAt: expiresAt,
		URL:       strings.TrimRight(baseURL, "/") + routePath + "?token=" + token,
	}, nil
}

// defaultObjectKey now includes a user_id prefix so S3 listings can be
// filtered per user via prefix scans. Anonymous uploads (empty userID) go
// into the shared `anonymous/` prefix.
func defaultObjectKey(now time.Time, artifactID, filename, userID string) string {
	ext := path.Ext(filename)
	prefix := strings.TrimSpace(userID)
	if prefix == "" {
		prefix = "anonymous"
	}
	return fmt.Sprintf("users/%s/%04d/%02d/%02d/%s%s",
		prefix, now.Year(), now.Month(), now.Day(), artifactID, ext)
}

func newArtifactID() string {
	buf := make([]byte, 8)
	if _, err := rand.Read(buf); err != nil {
		return fmt.Sprintf("art_%d", time.Now().UTC().UnixNano())
	}
	return "art_" + strings.ToLower(hex.EncodeToString(buf))
}
