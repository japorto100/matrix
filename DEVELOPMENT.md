# Go Backend — Developer Reference

> Run all commands from `go-backend/` unless stated otherwise.

## Quick Start

```bash
cd go-backend
go build ./...           # compile everything (catches import errors)
go vet ./...             # built-in static analysis
go test ./...            # full test suite (no -race, fast)
```

---

## Build

```bash
go build ./...                        # all packages
go build ./cmd/gateway/...            # only the gateway binary
go build -v ./...                     # verbose (shows compiled packages)
go build -ldflags "-s -w" ./...       # stripped binary (smaller)
```

---

## Tests

### Standard

```bash
go test ./...                                        # all packages, cached
go test -count=1 ./...                               # force re-run (no cache)
go test -v ./internal/handlers/http/...              # verbose, one package
go test -run TestGeopolitical ./internal/...         # run a specific test by name
```

### Race Detector (always use for concurrent code)

```bash
go test -race -count=1 ./...                         # full suite with race detector
go test -race -count=1 ./internal/connectors/...     # just connectors
go test -race -count=1 -timeout 120s ./internal/...  # explicit timeout (handlers/http needs it)
```

### Shuffle (catches order-dependent test bugs)

```bash
go test -shuffle=on -count=3 ./internal/storage/...  # 3 random orderings
go test -race -shuffle=on -count=1 ./...             # race + shuffle (CI gate)
```

### Coverage

```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out                      # open in browser
go test -covermode=atomic -coverprofile=cov.out ./... # atomic mode for concurrent code
```

### Benchmarks

```bash
go test -bench=. -benchmem ./...                     # all benchmarks
go test -bench=BenchmarkCandle -benchmem ./internal/candle/...
go test -bench=. -benchmem -count=5 ./...            # averaged over 5 runs
# Output columns: ns/op  B/op  allocs/op
```

### Profiling (combine with benchmarks)

```bash
go test -bench=. -cpuprofile=cpu.prof -memprofile=mem.prof ./...
go tool pprof -http=:8080 cpu.prof    # flamegraph in browser
go tool pprof -http=:8080 mem.prof    # heap allocation view
# CLI: go tool pprof cpu.prof → top / list FuncName / web
```

### synctest (Go 1.25+ — deterministic concurrency tests)

`testing/synctest` eliminates real-time waiting in concurrency tests via a **fake clock + goroutine bubble**.

```go
// Example: test a 30-second retry without waiting 30 seconds
func TestRetryBackoff(t *testing.T) {
    synctest.Test(t, func(t *testing.T) {
        called := 0
        go func() {
            retry.Do(ctx, func() error {
                called++
                return errors.New("fail")
            }, retry.WithDelay(30*time.Second))
        }()

        synctest.Wait()             // wait until all goroutines in bubble are blocked
        time.Sleep(30*time.Second)  // fake clock jumps instantly — no real sleep
        synctest.Wait()
        // called == 2, 0ms elapsed
    })
}
```

**Rules:**
- Fake clock advances only when **all goroutines** in the bubble are durably blocked (channel recv, `time.Sleep`, `sync.Cond.Wait`)
- Mutex locking is **NOT** durably blocked — don't rely on fake clock to advance past mutex waits
- Use for: retry backoff, SSE reconnect, timeout detection, rate limiters, OTel flush delays

```bash
go test -race -v -run TestRetry ./...               # runs as a normal test — no special flags needed
```

### Fuzzing (Go 1.18+ — automated input generation)

Fuzzing finds panics and unexpected behavior by automatically generating test inputs. Suitable for parsers, string manipulation, and security-sensitive input handling.

```go
// Example: fuzz a snapshot ID builder
func FuzzLocalSnapshotID(f *testing.F) {
    // Seed corpus — known tricky inputs
    f.Add("ofac", "abc123", int64(1710000000))
    f.Add("", "", int64(0))
    f.Add("seco-sanctions/v2", "deadbeef" + strings.Repeat("x", 64), int64(-1))

    f.Fuzz(func(t *testing.T, sourceID, sha string, ts int64) {
        id := LocalSnapshotID(sourceID, time.Unix(ts, 0), sha)
        // Must not panic. Must be deterministic.
        id2 := LocalSnapshotID(sourceID, time.Unix(ts, 0), sha)
        if id != id2 {
            t.Errorf("non-deterministic: %q != %q", id, id2)
        }
    })
}
```

```bash
# Run fuzzer for a specific duration (suitable for CI or pre-push)
go test -fuzz=FuzzLocalSnapshotID -fuzztime=30s ./internal/connectors/base/
go test -fuzz=FuzzLocalSnapshotID -fuzztime=5m  ./internal/connectors/base/  # deeper session

# Run all fuzz targets for 30s each (CI gate)
go test -fuzz=Fuzz -fuzztime=30s ./internal/...

# Reproduce a specific crash (corpus file auto-saved on failure)
go test -run=FuzzLocalSnapshotID/testdata/fuzz/FuzzLocalSnapshotID/abc123 ./internal/connectors/base/
```

**Good targets for fuzzing in this codebase:**
- `LocalSnapshotID`, `SnapshotFilename`, `NormalizeSnapshotContentType` (string input logic)
- XML/JSON parsers in connectors (OFAC, UN, ACLED, CrisisWatch payloads)
- JWT decode paths (security-sensitive)

---

## Code Quality

### golangci-lint (comprehensive linter suite)

```bash
golangci-lint run ./...           # full lint run
golangci-lint run --fix ./cmd/... ./internal/...     # auto-fix safe issues (modernize, gofmt, etc.)
golangci-lint run --new-from-rev=HEAD~1 ./...        # only new issues vs last commit (fast in CI)
golangci-lint run ./internal/connectors/...          # narrow scope
```

Config: `.golangci.yml` — active linters:

| Category | Linters |
|----------|---------|
| Standard | `errcheck`, `govet`, `ineffassign`, `staticcheck`, `unused` |
| Code quality | `gocritic`, `exhaustive`, `revive`, `nolintlint` |
| Error handling | `errorlint` (errors.Is/As), `wrapcheck` (external pkg wrapping) |
| Security | `gosec` (SQL injection, hardcoded secrets, weak crypto) |
| Observability | `spancheck` (OTel span.End()), `loggercheck` (slog key-value) |
| Database | `sqlclosecheck` (rows.Close()) |
| Modernization | `modernize` (interface{} → any, slices.Contains, etc.) |

`govet` analyzers enabled: `shadow`, `waitgroup` (Go 1.25), `hostport` (Go 1.25).

### govulncheck (call-graph-aware CVE scanner)

```bash
govulncheck ./...                                    # scan all packages
govulncheck -show verbose ./...                      # include details
govulncheck -json ./... | jq '.findings[].osv.id'   # just CVE IDs
```

Install once: `go install golang.org/x/vuln/cmd/govulncheck@latest`

### go vet (built-in analyzers)

```bash
go vet ./...
go vet -shadow ./...                                 # variable shadowing
```

### staticcheck (included in golangci-lint, also standalone)

```bash
staticcheck ./...
```

---

## Module Management

```bash
go mod tidy                          # add missing / remove unused deps
go mod verify                        # check module checksums
go mod graph | head -20              # dependency graph
go list -m all | grep nats           # find a specific dep

# Upgrade a dependency
go get github.com/redis/go-redis/v9@latest
go mod tidy

# Upgrade Go toolchain (e.g., to fix CVEs)
go get toolchain@go1.26.1
go mod tidy

# Audit submodule (GCT)
cd go-crypto-trader && git log --oneline -10        # recent upstream commits
cd .. && git submodule update --remote go-crypto-trader
go mod tidy                                          # always after GCT update
```

---

## SQLite Notes (current storage layer)

- **WAL + busy_timeout**: `NewSQLiteMetadataStore` sets WAL journal mode and 5s busy timeout via URI DSN — no changes needed per-caller.
- **Per-source DB files**: Each data source (OFAC, UN, SECO, EU…) gets its own `{baseName}_meta.db` to avoid `SQLITE_BUSY` from parallel goroutines.
- **Single connection**: `db.SetMaxOpenConns(1)` on every SQLite handle — SQLite is not safe for concurrent writes even within one process.
- **Migration**: `TODO(postgres): replace with pgxpool + sqlc when METADATA_STORE_DRIVER=postgres`.

---

## Database (future: PostgreSQL + sqlc)

```bash
# When METADATA_STORE_DRIVER=postgres is wired:
go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest
sqlc generate                        # regenerate type-safe DB layer from .sql files
```

Files will live in:
- `go-backend/internal/db/` — sqlc-generated code
- `go-backend/internal/repository/` — repository adapters

---

## OpenTelemetry

Set `OTEL_ENABLED=true` in `.env` to activate tracing + metrics export.
Collector endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:5081` (gRPC).

```bash
# Local observability (without Docker)
.\scripts\dev-stack.ps1 -Observability   # downloads openobserve.exe → UI at :5080
```

FlightRecorder (production incident traces, no restart needed):

```go
// go-backend/internal/observability/ (planned)
// Opt-in via FLIGHT_RECORDER_ENABLED=true
recorder := trace.NewFlightRecorder()
recorder.Start()
// On incident: recorder.WriteTo(file) → go tool trace flight.trace
```

---

## Common One-Liners

```bash
# Find all TODO comments
grep -r "TODO\|FIXME\|HACK" --include="*.go" .

# Check for interface{} (should be any in new code)
grep -rn "interface{}" --include="*.go" ./internal/ ./cmd/

# List all HTTP routes
grep -rn "mux.HandleFunc\|Handle(" --include="*.go" ./internal/app/

# Count test functions
grep -rn "^func Test" --include="*.go" . | wc -l

# Run linter on only changed files (fast)
git diff --name-only HEAD | grep '\.go$' | xargs golangci-lint run
```

---

## CI Gate (mirrors `lefthook.yml` pre-push)

```bash
go build ./...
go vet ./...
golangci-lint run ./...
go test -race -shuffle=on -count=1 -timeout 120s ./...
govulncheck ./...

# Once FuzzXxx functions exist — add to CI:
# go test -fuzz=Fuzz -fuzztime=30s ./internal/connectors/base/ ./...
```

> `synctest` tests need no special flag — they run as normal tests within `go test -race ./...`.
