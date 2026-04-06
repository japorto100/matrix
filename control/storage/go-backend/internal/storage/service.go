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
	case ProviderS3, ProviderSeaweedFS:
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
	artifactID := newArtifactID()
	objectKey := strings.TrimSpace(input.ObjectKey)
	if objectKey == "" {
		objectKey = defaultObjectKey(now, artifactID, filename)
	}

	artifact := Artifact{
		ID:             artifactID,
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

func (s *Service) IssueUploadURL(artifactID, baseURL string) (SignedURL, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return SignedURL{}, fmt.Errorf("load artifact %s for upload url: %w", artifactID, err)
	}
	if artifact.Status != StatusPendingUpload {
		return SignedURL{}, ErrArtifactUploadState
	}
	return s.issueSignedURL(artifact.ID, ActionUpload, baseURL, "/api/v1/storage/artifacts/upload/"+artifact.ID)
}

func (s *Service) IssueDownloadURL(artifactID, baseURL string) (SignedURL, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return SignedURL{}, fmt.Errorf("load artifact %s for download url: %w", artifactID, err)
	}
	if artifact.Status != StatusReady {
		return SignedURL{}, ErrArtifactNotReady
	}
	return s.issueSignedURL(artifact.ID, ActionDownload, baseURL, "/api/v1/storage/artifacts/"+artifact.ID+"/download")
}

func (s *Service) GetArtifact(artifactID string) (Artifact, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return Artifact{}, fmt.Errorf("load artifact %s: %w", artifactID, err)
	}
	if artifact.Status == StatusReady {
		token, err := s.signer.Issue(TokenClaims{
			ArtifactID: artifact.ID,
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

func (s *Service) UploadArtifact(ctx context.Context, artifactID, token, contentType string, body io.ReadCloser) error {
	defer func() {
		if body != nil {
			_ = body.Close()
		}
	}()
	claims, err := s.signer.Verify(token, s.nowFunc().UTC())
	if err != nil || claims.ArtifactID != artifactID || claims.Action != ActionUpload {
		return ErrInvalidToken
	}
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return fmt.Errorf("load artifact %s for upload: %w", artifactID, err)
	}
	if artifact.Status != StatusPendingUpload {
		return ErrArtifactUploadState
	}
	if providedType := strings.TrimSpace(contentType); providedType != "" && artifact.ContentType != "" && !strings.EqualFold(providedType, artifact.ContentType) {
		return fmt.Errorf("upload content type mismatch: got %q want %q", providedType, artifact.ContentType)
	}
	result, err := s.provider.Put(ctx, artifact.ObjectKey, body)
	if err != nil {
		return fmt.Errorf("store artifact object %s: %w", artifact.ObjectKey, err)
	}
	if result.UploadedAt.IsZero() {
		result.UploadedAt = s.nowFunc().UTC()
	}
	if err := s.store.MarkUploaded(artifactID, result); err != nil {
		return fmt.Errorf("mark artifact %s uploaded: %w", artifactID, err)
	}
	return nil
}

func (s *Service) OpenDownload(ctx context.Context, artifactID, token string) (Artifact, io.ReadCloser, error) {
	claims, err := s.signer.Verify(token, s.nowFunc().UTC())
	if err != nil || claims.ArtifactID != artifactID || claims.Action != ActionDownload {
		return Artifact{}, nil, ErrInvalidToken
	}
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return Artifact{}, nil, fmt.Errorf("load artifact %s for download: %w", artifactID, err)
	}
	if artifact.Status != StatusReady {
		return Artifact{}, nil, ErrArtifactNotReady
	}
	reader, err := s.provider.Get(ctx, artifact.ObjectKey)
	if err != nil {
		return Artifact{}, nil, fmt.Errorf("open artifact object %s: %w", artifact.ObjectKey, err)
	}
	return artifact, reader, nil
}

func (s *Service) issueSignedURL(artifactID string, action Action, baseURL, routePath string) (SignedURL, error) {
	now := s.nowFunc().UTC()
	expiresAt := now.Add(s.ttl)
	token, err := s.signer.Issue(TokenClaims{
		ArtifactID: artifactID,
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

func defaultObjectKey(now time.Time, artifactID, filename string) string {
	ext := path.Ext(filename)
	return fmt.Sprintf("%04d/%02d/%02d/%s%s", now.Year(), now.Month(), now.Day(), artifactID, ext)
}

func newArtifactID() string {
	buf := make([]byte, 8)
	if _, err := rand.Read(buf); err != nil {
		return fmt.Sprintf("art_%d", time.Now().UTC().UnixNano())
	}
	return "art_" + strings.ToLower(hex.EncodeToString(buf))
}
