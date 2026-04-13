// Package config lädt Konfiguration aus Environment Variables.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

// Config enthält alle Konfigurationswerte des Appservice.
type Config struct {
	// Matrix Homeserver
	HomeserverURL string
	ServerName    string

	// Appservice HTTP Server
	AppserviceURL  string
	AppservicePort string

	// Tokens für Matrix Auth
	ASToken string // Appservice → Homeserver
	HSToken string // Homeserver → Appservice (verifizieren)

	// Bot-User-ID des Appservices selbst
	BotUserID string

	// NATS für Event-Weiterleitung
	NATSUrl string

	// Logging
	LogLevel string

	// Pfad zur registration.yaml (für --generate-registration)
	RegistrationPath string

	// Agent-Namespace Prefix (z.B. "agent-" → @agent-trading:matrix.local)
	AgentPrefix string

	// E2EE (Option C: Go übernimmt Crypto, Python bekommt Klartext)
	E2EEEnabled       bool   // MATRIX_E2EE_ENABLED=false (Standard: deaktiviert für Tests)
	CryptoDBPath      string // MATRIX_CRYPTO_DB_PATH=./data/crypto.sqlite3 (SQLite fallback only)
	CryptoPickleKey   string // MATRIX_CRYPTO_PICKLE_KEY=<zufälliger Key>
	KeyBackupPassword string // MATRIX_KEY_BACKUP_PASSWORD — Passphrase für lokales Megolm Key Backup

	// Mention-Filter: In Gruppenräumen nur Messages weiterleiten die den Agent betreffen
	MentionOnlyInGroups bool // MENTION_ONLY_IN_GROUPS=true

	// MCP Server (gemountet im Agent Service unter /mcp)
	MCPServiceURL string // MCP_SERVICE_URL=http://127.0.0.1:8094

	// Agent Service (Python, Port 8094)
	AgentServiceURL string // AGENT_SERVICE_URL=http://127.0.0.1:8094

	// Memory Service (Python, Port 8093)
	MemoryServiceURL string // MEMORY_SERVICE_URL=http://127.0.0.1:8093

	// exec-05c: Agent-Isolation + Hybrid E2EE
	DeleteKeysAfterDecrypt bool   // MATRIX_DELETE_KEYS_AFTER_DECRYPT=false — Forward Secrecy (Keys löschen nach Decrypt)
	DeleteKeysAfterHours   int    // MATRIX_DELETE_KEYS_AFTER_HOURS=0 — Kompromiss: Keys X Stunden behalten (0=sofort wenn enabled)
	NATSSubjectRouting     bool   // NATS_SUBJECT_ROUTING_ENABLED=false — Per-Agent NATS Subject Routing
	AgentCapabilities      string // MATRIX_AGENT_CAPABILITIES=gateway — "gateway" (Go entschlüsselt) oder "native" (Agent entschlüsselt)

	// exec-16: Key Encryption (shared mit Python — identisches AES-256-GCM Format)
	KeyEncryptionSecret string // KEY_ENCRYPTION_SECRET — 64 hex chars (32 bytes)
	KeyVaultBackend     string // KEY_VAULT_BACKEND — "aesgcm" (default) oder "hpke-mlkem"

	// exec-19 Stufe 2B + 3: shared PG DSN for all Go-owned schemas
	// (storage.artifact_metadata, matrix_crypto). Resolved from a
	// fallback chain so the env var name can evolve without breaking
	// existing deployments: POSTGRES_URL → HINDSIGHT_DB_URL → DATABASE_URL.
	PostgresDSN string
}

// Load lädt Config aus .env.{environment} + Environment.
// Shell-Env hat Vorrang vor Datei-Werte (wie im Hauptprojekt).
// Reihenfolge: .env.development oder .env.production (je nach GO_ENV), dann .env als Fallback.
func Load() *Config {
	env := getenv("GO_ENV", "development")
	// Spezifische Env-Datei zuerst, dann generischer Fallback
	_ = godotenv.Load(".env." + env)
	_ = godotenv.Load(".env") // Fallback für Abwärtskompatibilität

	return &Config{
		HomeserverURL:    getenv("MATRIX_HOMESERVER_URL", "http://localhost:8448"),
		ServerName:       getenv("MATRIX_SERVER_NAME", "matrix.local"),
		AppserviceURL:    getenv("MATRIX_APPSERVICE_URL", "http://localhost:29318"),
		AppservicePort:   getenv("MATRIX_APPSERVICE_PORT", "29318"),
		ASToken:          mustenv("MATRIX_AS_TOKEN"),
		HSToken:          mustenv("MATRIX_HS_TOKEN"),
		BotUserID:        getenv("MATRIX_BOT_USER_ID", "@appservice-bot:matrix.local"),
		NATSUrl:          getenv("NATS_URL", "nats://localhost:4222"),
		LogLevel:         getenv("LOG_LEVEL", "info"),
		RegistrationPath: getenv("REGISTRATION_PATH", "../homeserver/registration.yaml"),
		AgentPrefix:      getenv("MATRIX_AGENT_PREFIX", "agent-"),
		E2EEEnabled:      getenv("MATRIX_E2EE_ENABLED", "false") == "true",
		CryptoDBPath:     getenv("MATRIX_CRYPTO_DB_PATH", "./data/crypto.sqlite3"),
		CryptoPickleKey:   getenv("MATRIX_CRYPTO_PICKLE_KEY", "changeme-use-random-32-chars"),
		KeyBackupPassword: getenv("MATRIX_KEY_BACKUP_PASSWORD", ""),
		MentionOnlyInGroups: getenv("MENTION_ONLY_IN_GROUPS", "true") == "true",
		MCPServiceURL:       getenv("MCP_SERVICE_URL", "http://127.0.0.1:8094"),
		AgentServiceURL:     getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8094"),
		MemoryServiceURL:       getenv("MEMORY_SERVICE_URL", "http://127.0.0.1:8093"),
		DeleteKeysAfterDecrypt: getenv("MATRIX_DELETE_KEYS_AFTER_DECRYPT", "false") == "true",
		DeleteKeysAfterHours:   getenvInt("MATRIX_DELETE_KEYS_AFTER_HOURS", 0),
		NATSSubjectRouting:     getenv("NATS_SUBJECT_ROUTING_ENABLED", "false") == "true",
		AgentCapabilities:      getenv("MATRIX_AGENT_CAPABILITIES", "gateway"),
		KeyEncryptionSecret:    getenv("KEY_ENCRYPTION_SECRET", ""),
		KeyVaultBackend:        getenv("KEY_VAULT_BACKEND", "aesgcm"),
		PostgresDSN:            resolvePostgresDSN(),
	}
}

// resolvePostgresDSN checks env vars in priority order so the canonical
// name can evolve (exec-18 plans to standardise on DATABASE_URL).
func resolvePostgresDSN() string {
	for _, key := range []string{"POSTGRES_URL", "HINDSIGHT_DB_URL", "DATABASE_URL"} {
		if v := strings.TrimSpace(os.Getenv(key)); v != "" {
			return v
		}
	}
	return ""
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getenvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}

func mustenv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		panic(fmt.Sprintf("required env var not set: %s\nSee .env.example", key))
	}
	return v
}
