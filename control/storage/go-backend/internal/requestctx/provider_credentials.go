package requestctx

import (
	"context"

	baseconnectors "tradeviewfusion/go-backend/internal/connectors/base"
)

type providerCredentialsContextKey struct{}

func WithProviderCredentials(ctx context.Context, creds baseconnectors.CredentialStore) context.Context {
	return context.WithValue(ctx, providerCredentialsContextKey{}, creds.Normalized())
}

func ProviderCredentials(ctx context.Context) baseconnectors.CredentialStore {
	creds, _ := ctx.Value(providerCredentialsContextKey{}).(baseconnectors.CredentialStore)
	if creds == nil {
		return baseconnectors.CredentialStore{}
	}
	return creds
}

func ProviderCredential(ctx context.Context, provider string) (baseconnectors.CredentialSet, bool) {
	return ProviderCredentials(ctx).Get(provider)
}
