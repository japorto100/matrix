package base

import "strings"

type CredentialStore map[string]CredentialSet

func (s CredentialStore) Normalized() CredentialStore {
	if len(s) == 0 {
		return nil
	}
	out := make(CredentialStore, len(s))
	for provider, creds := range s {
		name := strings.ToLower(strings.TrimSpace(provider))
		if name == "" || creds.IsEmpty() {
			continue
		}
		out[name] = creds
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func (s CredentialStore) Get(provider string) (CredentialSet, bool) {
	if len(s) == 0 {
		return CredentialSet{}, false
	}
	creds, ok := s[strings.ToLower(strings.TrimSpace(provider))]
	return creds, ok
}

func (s CredentialStore) Redacted() CredentialStore {
	if len(s) == 0 {
		return nil
	}
	out := make(CredentialStore, len(s))
	for provider, creds := range s {
		out[strings.ToLower(strings.TrimSpace(provider))] = creds.Redacted()
	}
	return out
}

type CredentialSet struct {
	Key        string `json:"key,omitempty"`
	Secret     string `json:"secret,omitempty"`
	Passphrase string `json:"passphrase,omitempty"`
	ClientID   string `json:"clientId,omitempty"`
	SubAccount string `json:"subAccount,omitempty"`
}

func (c CredentialSet) IsEmpty() bool {
	return strings.TrimSpace(c.Key) == "" &&
		strings.TrimSpace(c.Secret) == "" &&
		strings.TrimSpace(c.Passphrase) == "" &&
		strings.TrimSpace(c.ClientID) == "" &&
		strings.TrimSpace(c.SubAccount) == ""
}

func (c CredentialSet) HasSecrets() bool {
	return strings.TrimSpace(c.Key) != "" ||
		strings.TrimSpace(c.Secret) != "" ||
		strings.TrimSpace(c.Passphrase) != ""
}

func (c CredentialSet) Redacted() CredentialSet {
	return CredentialSet{
		Key:        redactCredentialValue(c.Key),
		Secret:     redactCredentialValue(c.Secret),
		Passphrase: redactCredentialValue(c.Passphrase),
		ClientID:   strings.TrimSpace(c.ClientID),
		SubAccount: strings.TrimSpace(c.SubAccount),
	}
}

func redactCredentialValue(value string) string {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return ""
	}
	if len(trimmed) <= 4 {
		return "****"
	}
	return trimmed[:2] + "..." + trimmed[len(trimmed)-2:]
}
