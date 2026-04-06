package base

import (
	"context"
	"fmt"
	"strings"
)

type TranslationRequest struct {
	SourceName string            `json:"sourceName"`
	Language   string            `json:"language,omitempty"`
	Text       string            `json:"text"`
	Metadata   map[string]string `json:"metadata,omitempty"`
}

type TranslationBridge interface {
	Submit(ctx context.Context, req TranslationRequest) error
}

type NoopTranslationBridge struct{}

func (NoopTranslationBridge) Submit(ctx context.Context, req TranslationRequest) error {
	_ = ctx
	if strings.TrimSpace(req.Text) == "" {
		return fmt.Errorf("translation request text required")
	}
	return nil
}
