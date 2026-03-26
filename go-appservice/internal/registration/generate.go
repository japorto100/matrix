// Package registration generiert die homeserver/registration.yaml.
// Einmalig ausführen, dann Tuwunel neu starten.
package registration

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"matrix/go-appservice/internal/config"
	"gopkg.in/yaml.v3"
)

// Registration entspricht dem Tuwunel/Synapse registration.yaml Format.
type Registration struct {
	ID              string     `yaml:"id"`
	URL             string     `yaml:"url"`
	ASToken         string     `yaml:"as_token"`
	HSToken         string     `yaml:"hs_token"`
	SenderLocalpart string     `yaml:"sender_localpart"`
	Namespaces      Namespaces `yaml:"namespaces"`
	RateLimited     bool       `yaml:"rate_limited"`
	Protocols       []string   `yaml:"protocols"`
}

type Namespaces struct {
	Users   []Namespace `yaml:"users"`
	Rooms   []Namespace `yaml:"rooms"`
	Aliases []Namespace `yaml:"aliases"`
}

type Namespace struct {
	Exclusive bool   `yaml:"exclusive"`
	Regex     string `yaml:"regex"`
}

// Generate schreibt die registration.yaml in den konfigurierten Pfad.
func Generate(cfg *config.Config) error {
	reg := Registration{
		ID:              "trading-agent-appservice",
		URL:             cfg.AppserviceURL,
		ASToken:         cfg.ASToken,
		HSToken:         cfg.HSToken,
		SenderLocalpart: "appservice-bot",
		Namespaces: Namespaces{
			Users: []Namespace{
				{
					Exclusive: true,
					// Escaped für YAML: @agent-.*:matrix\.local
					Regex: fmt.Sprintf(`@agent-.*:%s`, escapeRegex(cfg.ServerName)),
				},
			},
			Rooms:   []Namespace{},
			Aliases: []Namespace{},
		},
		RateLimited: false,
		Protocols:   []string{},
	}

	data, err := yaml.Marshal(reg)
	if err != nil {
		return fmt.Errorf("yaml marshal: %w", err)
	}

	// Verzeichnis erstellen falls nötig
	dir := filepath.Dir(cfg.RegistrationPath)
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}

	if err := os.WriteFile(cfg.RegistrationPath, data, 0o600); err != nil {
		return fmt.Errorf("write %s: %w", cfg.RegistrationPath, err)
	}

	slog.Info("registration.yaml written",
		"path", cfg.RegistrationPath,
		"namespace", reg.Namespaces.Users[0].Regex,
	)
	return nil
}

// escapeRegex escaped Punkte in der Server-Domain für Regex.
func escapeRegex(domain string) string {
	result := make([]byte, 0, len(domain)*2)
	for i := 0; i < len(domain); i++ {
		if domain[i] == '.' {
			result = append(result, '\\', '.')
		} else {
			result = append(result, domain[i])
		}
	}
	return string(result)
}
