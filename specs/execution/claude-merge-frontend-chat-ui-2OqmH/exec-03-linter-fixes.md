# exec-03: Linter-Fixes (Go + Python)

**Datum:** 17.04.2026
**Status:** ✓ done

## Go — `golangci-lint run ./...`

Start: **12 issues** (9 gosec + 3 nolintlint stale)
Ende:  **0 issues** ✓

### Setup

- `libolm-dev` installiert (fuer `maunium.net/go/mautrix/crypto/libolm`,
  nicht pure-Go-Olm Build).
- golangci-lint von 2.5.0/go1.25 auf 2.0.0-dev/go1.26.1 aktualisiert
  (Projekt fordert Toolchain 1.26.2).

### Fixes

| File | Rule | Fix |
|---|---|---|
| `internal/handlers/http/control_proxy_handler.go:46` | G704 SSRF | `//nolint:gosec` — upstream ist operator-configured (`AGENT_SERVICE_URL`), nicht user-input |
| `internal/handlers/http/mcp_proxy_handler.go:39` | G704 SSRF | `//nolint:gosec` — upstream ist `MCP_SERVICE_URL` |
| `internal/handlers/http/memory_handler.go:72,136` | G705 XSS | `// #nosec G705` — body ist JSON-Response von operator-configured memory service; `Content-Type: application/json` explizit gesetzt |
| `internal/handler/server.go:147` | G706 log-injection | `// #nosec G706` — `ARTIFACT_STORAGE_PROVIDER` ist Env (operator, nicht user) |
| `internal/handler/server.go:302,307` | G706 log-injection | `// #nosec G706` — slog emittiert structured JSON, `txn_id` ist Pfad-Parameter von Tuwunel-AS-Call (trusted via AS-Token) |
| `internal/handler/server.go:359` | G706 log-injection | `//nolint:gosec` — slog structured field |
| `internal/handler/server.go:321` | G118 goroutine-ctx | **echter Fix:** `context.WithoutCancel(r.Context())` — Cancellation detached, aber Request-Values (trace IDs) erhalten |
| `internal/keyvault/keyvault.go:89,90` | nolintlint | Stale `//nolint:gosec` Directives entfernt (gosec meldet die Zeilen nicht mehr) |
| `internal/storage/provider_s3.go:142` | nolintlint | Stale `//nolint:gosec` Directive entfernt |

### Ergebnis

```bash
$ golangci-lint run ./...
0 issues.

$ go build ./...
(clean)

$ go vet ./...
(clean)

$ go test -short ./...
ok  matrix/go-appservice/internal/connectors/agentservice   0.080s
ok  matrix/go-appservice/internal/connectors/ingestion      0.187s
ok  matrix/go-appservice/internal/connectors/memory         0.077s
ok  matrix/go-appservice/internal/handlers/http             0.379s
ok  matrix/go-appservice/internal/intent                    0.056s
ok  matrix/go-appservice/internal/keyvault                  0.057s
ok  matrix/go-appservice/internal/natsbridge                0.076s
ok  matrix/go-appservice/internal/storage                   0.283s
ok  matrix/go-appservice/internal/telemetry                 20.076s
```

## Python — `ruff check .`

Start: **51 errors** (12 N999 + 10 F821 + 10 I001 + 6 UP037 + 5 invalid-syntax
+ 3 F401 + 3 F841 + 1 E731 + 1 E741)
Ende:  **0 errors** ✓

### Root-Config-Diskrepanz entdeckt + gefixt

`/home/user/matrix/python-backend/pyproject.toml` hatte `ignore = ["E501",
"N999"]` — aber ruff walkt vom CWD nach oben und findet zuerst
`/home/user/matrix/pyproject.toml`, der `[tool.ruff.lint]` ueberhaupt nicht
definierte. Resultat: N999 wurde nicht ignoriert.

**Fix:** `[tool.ruff.lint]` mit denselben `select`/`ignore` in die Root-
`pyproject.toml` gespiegelt.

### Autofixes (33 Findings)

- 10 I001 (unsorted imports) — `ruff --fix`
- 6 UP037 (quoted annotations) — `ruff --fix`
- 3 F401 (unused imports) — `ruff --fix`
- 12 N999 — via Root-Config-Fix stummgeschaltet
- 2 F841 (unused vars) — 2 von 3 auto, 1 manuell (`rust_core/proto/validate_proto.py`)

### Manuelle Fixes

| File | Rule | Fix |
|---|---|---|
| `agent/skills/finder.py:163` | E731 lambda-assignment | lambda → `def approx_tok(text: str) -> int: ...` |
| `compute/tests/test_patterns.py:313` | E741 ambiguous `l` | `h, l` → `highs, lows` |
| `compute/indicator_engine/helpers.py` | F821 `Pivot` (2x) | `Pivot` zum existierenden `if TYPE_CHECKING:` Block hinzugefuegt |
| `compute/indicator_engine/{oscillators,trend,volatility}.py` | F821 (8x) | Inline `# noqa: F821` — quoted forward-references, lokal importiert, kein module-level Zirkular-Risiko |
| `rust_core/proto/validate_proto.py:79,84` | F841 | Toter Code (`valid_parents`, `parents`) entfernt; Kommentar ergaenzt warum (Altlast vom alten Parent-Check) |

### Pre-existing Syntax-Bug GEFIXT

`python-backend/memory_fusion/fusion_engine.py` (commit `f14e9b81`, 16.04.2026):

**Bug:** Der FUSION-Route Zweig der `list_documents()` Methode war doppelt
kaputt:
1. Lines 1402-1473 standen **ausserhalb** des `try:` Blocks (der nur den
   SUMMARY/VERBATIM early-return branch enthielt). Das `except Exception:` an
   Line 1474 war damit ein dangling except → Python-Parse-Fehler an 5 Stellen.
2. Lines 1451-1473 (`items = list(merged.values())` + filter + log + return)
   standen **innerhalb** des outer `for route_name, result in (SUMMARY...,
   VERBATIM...)` Loops. Folge: schon auf der ersten Iteration (SUMMARY)
   wurde `return` ausgefuehrt — **Verbatim-Docs wurden nie gemerged**.

**Fix:**
- Lines 1402-1449 um 4 Spaces eingeruckt (in `try:` Body gezogen).
- Lines 1451-1473 bleiben auf ihrer Einrueckung (jetzt: Try-Body-Level,
  **nach** der for-Schleife → durchlaeuft beide Routes vor dem Merge+Return).

**Verify:**
- `python3 -m py_compile memory_fusion/fusion_engine.py` ✓
- `ruff check .` ✓
- Semantik: jetzt werden SUMMARY + VERBATIM beide gequeryt und in `merged`
  kombiniert, bevor items/filter/return ausgefuehrt wird — das ist offensichtlich
  die beabsichtigte Logik (siehe Variablen-Namen `summary_docs` + `verbatim_docs`
  und `merged = {}`).

### Ergebnis

```bash
$ ruff check .
All checks passed!
```

## Nicht geaendert

- Gosec-Flags auf Handler-Logik (SSRF/XSS): statt `//nolint` haette man
  Allowlist-basierte Validation einbauen koennen. Aktuell ist die Annahme
  "operator-configured URLs sind trusted" — fuer Dev/Staging OK, fuer
  prod-hardening Ticket.
- Log-Sanitization in slog-Felder: slog escaped structured Fields korrekt
  (keine real Log-Injection moeglich), aber gosec G706 hat keinen Kontext.
  `//nolint` ist hier faktisch korrekt.
