// Matrix Appservice — Einstiegspunkt
// Registriert einen mautrix-go Appservice bei Tuwunel.
// Empfängt Matrix-Events und leitet sie via NATS an den Python Agent weiter.
// Virtuelle Agent-User-IDs: @agent-*:matrix.local (kontrolliert via Namespace)
//
// Starten:
//
//	go run -tags goolm ./cmd/appservice/...
//
// Registration generieren:
//
//	go run -tags goolm ./cmd/appservice/... --generate-registration
package main

import (
	"context"
	"flag"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"matrix/go-appservice/internal/config"
	"matrix/go-appservice/internal/handler"
	"matrix/go-appservice/internal/natsbridge"
	"matrix/go-appservice/internal/registration"
)

func main() {
	os.Exit(run())
}

// run enthält die eigentliche Logik — defer-Aufrufe werden garantiert ausgeführt.
func run() int {
	generateReg := flag.Bool("generate-registration", false, "Generiert homeserver/registration.yaml und beendet sich")
	flag.Parse()

	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	cfg := config.Load()

	if *generateReg {
		if err := registration.Generate(cfg); err != nil {
			slog.Error("registration generation failed", "error", err)
			return 1
		}
		slog.Info("registration.yaml generated — restart Tuwunel to apply")
		return 0
	}

	natsBridge, err := natsbridge.New(cfg.NATSUrl)
	if err != nil {
		slog.Error("NATS connect failed", "error", err, "url", cfg.NATSUrl)
		return 1
	}
	defer natsBridge.Close()

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	srv, err := handler.NewServer(cfg, natsBridge)
	if err != nil {
		slog.Error("server init failed", "error", err)
		return 1
	}

	slog.Info("Matrix Appservice starting",
		"appservice_url", cfg.AppserviceURL,
		"homeserver", cfg.HomeserverURL,
		"server_name", cfg.ServerName,
		"bot_user_id", cfg.BotUserID,
	)

	if err := srv.Start(ctx); err != nil {
		slog.Error("server error", "error", err)
		return 1
	}

	<-ctx.Done()
	slog.Info("shutting down")
	srv.Stop()
	return 0
}
