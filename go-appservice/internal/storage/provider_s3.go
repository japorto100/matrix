package storage

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

type S3Provider struct {
	client       *s3.Client
	bucket       string
	createBucket bool
}

func NewS3Provider(ctx context.Context, cfg S3Config) (*S3Provider, error) {
	bucket := strings.TrimSpace(cfg.Bucket)
	if bucket == "" {
		return nil, fmt.Errorf("s3 bucket required")
	}
	endpoint := strings.TrimSpace(cfg.Endpoint)
	if endpoint == "" {
		return nil, fmt.Errorf("s3 endpoint required")
	}
	region := strings.TrimSpace(cfg.Region)
	if region == "" {
		region = "us-east-1"
	}
	accessKeyID := strings.TrimSpace(cfg.AccessKeyID)
	secretAccessKey := strings.TrimSpace(cfg.SecretAccessKey)
	if accessKeyID == "" || secretAccessKey == "" {
		return nil, fmt.Errorf("s3 access credentials required")
	}

	awsCfg, err := awsconfig.LoadDefaultConfig(
		ctx,
		awsconfig.WithRegion(region),
		awsconfig.WithCredentialsProvider(
			aws.NewCredentialsCache(credentials.NewStaticCredentialsProvider(accessKeyID, secretAccessKey, "")),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("load s3 config: %w", err)
	}

	client := s3.NewFromConfig(awsCfg, func(o *s3.Options) {
		o.UsePathStyle = cfg.UsePathStyle
		o.BaseEndpoint = aws.String(endpoint)
	})
	provider := &S3Provider{
		client:       client,
		bucket:       bucket,
		createBucket: cfg.CreateBucket,
	}
	if provider.createBucket {
		if err := provider.ensureBucket(ctx); err != nil {
			return nil, err
		}
	}
	return provider, nil
}

func (p *S3Provider) Put(ctx context.Context, objectKey string, body io.Reader) (UploadResult, error) {
	key := strings.TrimSpace(objectKey)
	if key == "" {
		return UploadResult{}, fmt.Errorf("object key required")
	}

	tmpFile, err := os.CreateTemp("", "artifact-s3-*.tmp")
	if err != nil {
		return UploadResult{}, fmt.Errorf("create temp upload file: %w", err)
	}
	defer func() {
		_ = tmpFile.Close()
		_ = os.Remove(tmpFile.Name())
	}()

	hash := sha256.New()
	sizeBytes, err := io.Copy(io.MultiWriter(tmpFile, hash), body)
	if err != nil {
		return UploadResult{}, fmt.Errorf("buffer s3 upload body: %w", err)
	}
	if _, err := tmpFile.Seek(0, io.SeekStart); err != nil {
		return UploadResult{}, fmt.Errorf("rewind s3 upload body: %w", err)
	}

	if _, err := p.client.PutObject(ctx, &s3.PutObjectInput{
		Bucket:        aws.String(p.bucket),
		Key:           aws.String(key),
		Body:          tmpFile,
		ContentLength: aws.Int64(sizeBytes),
	}); err != nil {
		return UploadResult{}, fmt.Errorf("put s3 object: %w", err)
	}

	return UploadResult{
		SizeBytes:  sizeBytes,
		SHA256Hex:  hex.EncodeToString(hash.Sum(nil)),
		UploadedAt: time.Now().UTC(),
	}, nil
}

func (p *S3Provider) Get(ctx context.Context, objectKey string) (io.ReadCloser, error) {
	key := strings.TrimSpace(objectKey)
	if key == "" {
		return nil, fmt.Errorf("object key required")
	}

	output, err := p.client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(p.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, fmt.Errorf("get s3 object: %w", err)
	}
	return output.Body, nil
}

// ListObjects returns object info under a prefix (up to maxKeys). Implements
// the ObjectLister capability interface. exec-19 Stufe 3.
//
// For per-user isolation, the caller should pass `users/{user_id}/` as prefix.
// The maxKeys cap is clamped to [1, 1000] (S3 API limit).
func (p *S3Provider) ListObjects(ctx context.Context, prefix string, maxKeys int) ([]ObjectInfo, error) {
	if maxKeys <= 0 {
		maxKeys = 100
	}
	if maxKeys > 1000 {
		maxKeys = 1000
	}
	// After the clamp [1, 1000] the cast to int32 can never overflow —
	// satisfies gosec G115.
	maxKeys32 := int32(maxKeys) //nolint:gosec // clamped above
	output, err := p.client.ListObjectsV2(ctx, &s3.ListObjectsV2Input{
		Bucket:  aws.String(p.bucket),
		Prefix:  aws.String(strings.TrimSpace(prefix)),
		MaxKeys: aws.Int32(maxKeys32),
	})
	if err != nil {
		return nil, fmt.Errorf("list s3 objects: %w", err)
	}
	result := make([]ObjectInfo, 0, len(output.Contents))
	for _, obj := range output.Contents {
		info := ObjectInfo{}
		if obj.Key != nil {
			info.Key = *obj.Key
		}
		if obj.Size != nil {
			info.SizeBytes = *obj.Size
		}
		if obj.LastModified != nil {
			info.LastModified = obj.LastModified.UTC()
		}
		if obj.ETag != nil {
			info.ETag = strings.Trim(*obj.ETag, `"`)
		}
		result = append(result, info)
	}
	return result, nil
}

// Delete removes a single object. Implements the optional Delete
// capability used by FilesService.DeleteArtifact.
func (p *S3Provider) Delete(ctx context.Context, objectKey string) error {
	key := strings.TrimSpace(objectKey)
	if key == "" {
		return fmt.Errorf("object key required")
	}
	_, err := p.client.DeleteObject(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(p.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("delete s3 object: %w", err)
	}
	return nil
}

func (p *S3Provider) ensureBucket(ctx context.Context) error {
	if _, err := p.client.HeadBucket(ctx, &s3.HeadBucketInput{
		Bucket: aws.String(p.bucket),
	}); err == nil {
		return nil
	}
	if _, err := p.client.CreateBucket(ctx, &s3.CreateBucketInput{
		Bucket: aws.String(p.bucket),
	}); err != nil {
		return fmt.Errorf("create s3 bucket %q: %w", p.bucket, err)
	}
	return nil
}
