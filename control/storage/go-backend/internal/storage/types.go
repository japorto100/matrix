package storage

import (
	"errors"
	"time"
)

type ProviderKind string

const (
	ProviderFilesystem ProviderKind = "filesystem"
	ProviderS3         ProviderKind = "s3"
	ProviderSeaweedFS  ProviderKind = "seaweedfs"
)

type ArtifactStatus string

const (
	StatusPendingUpload ArtifactStatus = "pending_upload"
	StatusReady         ArtifactStatus = "ready"
	StatusUploadFailed  ArtifactStatus = "upload_failed"
)

type SourceSnapshotStatus string

const (
	SourceSnapshotFetched    SourceSnapshotStatus = "fetched"
	SourceSnapshotNormalized SourceSnapshotStatus = "normalized"
	SourceSnapshotFailed     SourceSnapshotStatus = "failed"
)

type Action string

const (
	ActionUpload   Action = "upload"
	ActionDownload Action = "download"
)

var (
	ErrArtifactNotFound    = errors.New("artifact not found")
	ErrArtifactNotReady    = errors.New("artifact not ready")
	ErrArtifactUploadState = errors.New("artifact not in uploadable state")
	ErrInvalidToken        = errors.New("invalid signed token")
)

type Artifact struct {
	ID             string
	ObjectKey      string
	Filename       string
	ContentType    string
	RetentionClass string
	Status         ArtifactStatus
	SizeBytes      int64
	SHA256Hex      string
	CreatedAt      time.Time
	UpdatedAt      time.Time
	ExpiresAt      time.Time

	DownloadToken string
}

type CreateArtifactInput struct {
	Filename       string
	ContentType    string
	RetentionClass string
	ObjectKey      string
}

type UploadResult struct {
	SizeBytes  int64
	SHA256Hex  string
	UploadedAt time.Time
}

type TokenClaims struct {
	ArtifactID string
	Action     Action
	ExpiresAt  time.Time
}

type SignedURL struct {
	Method    string
	URL       string
	Token     string
	ExpiresAt time.Time
}

type S3Config struct {
	Endpoint        string
	Region          string
	Bucket          string
	AccessKeyID     string
	SecretAccessKey string
	UsePathStyle    bool
	CreateBucket    bool
}

type MetadataStore interface {
	Create(artifact Artifact) error
	Get(id string) (Artifact, error)
	MarkUploaded(id string, result UploadResult) error
}

type SourceSnapshot struct {
	ID             string
	SourceID       string
	SourceClass    string
	FetchMode      string
	SourceURL      string
	ObjectKey      string
	ContentType    string
	ContentLength  int64
	SHA256Hex      string
	ETag           string
	LastModified   string
	ParserVersion  string
	SnapshotStatus SourceSnapshotStatus
	RetentionClass string
	CadenceHint    string
	DatasetName    string
	PartitionKey   string
	TraceID        string
	ErrorClass     string
	FetchedAt      time.Time
	UpdatedAt      time.Time
}
