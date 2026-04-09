package storage

import (
	"fmt"
	"strings"
)

type ArtifactMetadataStore interface {
	MetadataStore
	Close() error
}

func NewArtifactMetadataStore(provider, sqlitePath, postgresDSN string) (ArtifactMetadataStore, error) {
	switch strings.ToLower(strings.TrimSpace(provider)) {
	case "", "sqlite":
		return NewSQLiteMetadataStore(sqlitePath)
	case "postgres", "postgresql":
		return NewPostgresMetadataStore(postgresDSN)
	default:
		return nil, fmt.Errorf("unsupported artifact metadata provider %q", provider)
	}
}
