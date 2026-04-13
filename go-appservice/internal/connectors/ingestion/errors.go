package ingestion

import "errors"

// ErrJobNotFound is returned by Client.GetJob when the worker responds 404.
var ErrJobNotFound = errors.New("ingestion job not found")

// ErrPipelineNotImplemented is returned when the caller requests a pipeline
// kind that the Python worker does not yet support (image/audio/video/batch
// as of 11.04.2026). Handlers should map this to HTTP 501.
var ErrPipelineNotImplemented = errors.New("ingestion pipeline not implemented")
