# Building go-appservice

## Always use `-tags goolm`

This project uses `mautrix-go` for Matrix E2E encryption. mautrix-go ships
**two** parallel crypto backends selected by build tag:

| Tag          | Backend      | Implementation             | C deps          |
|--------------|--------------|----------------------------|-----------------|
| (default)    | `libolm`     | CGO bindings to `libolm`   | `olm/olm.h` + native lib |
| `goolm`      | `goolm`      | Pure Go (Vodozemac-style)  | none            |

Our `internal/crypto/machine.go` is wired for `goolm`. We **always** build with
`-tags goolm` to avoid the CGO dependency on `libolm`, which is not installed
on most Windows dev boxes.

### Correct commands

```bash
# Build
go build -tags goolm ./...
go build -tags goolm -o ./tmp/appservice.exe ./cmd/appservice

# Test
go test  -tags goolm ./...
HINDSIGHT_DB_URL="postgresql://postgres@127.0.0.1:5433/hindsight_dev" \
  go test -tags goolm -count=1 ./internal/storage/...
```

### Wrong commands (and why they fail)

```bash
go build ./...          # pulls in mautrix/crypto/libolm → C header error
go test  ./...          # same
```

The error looks like:

```
D:\DevCache\go\pkg\mod\maunium.net\go\mautrix@v0.22.0\crypto\libolm\error.go:4:11:
fatal error: olm/olm.h: No such file or directory
```

**This is not a real build failure** — it's the wrong backend being compiled.
Add `-tags goolm` to fix.

### Why we can't force the tag automatically

Build tags are controlled by the compiler invocation, not the source tree. A
`//go:build !goolm` stub file would never be reached — the libolm sub-package
fails to compile **before** our own files are visited, because Go resolves
transitive deps first.

The only defenses are:
- Every build script passes `-tags goolm` (scripts/dev-stack2.ps1:238 already does)
- CI jobs pass `-tags goolm`
- Developers know about this file

If you want to verify a new clone is set up correctly:

```bash
go build -tags goolm ./cmd/appservice  # should succeed silently
```

## Integration tests need Postgres

Storage integration tests connect to a real Postgres instance. They skip
cleanly if unreachable:

```bash
# DevStack startet PG auf :5433 (./scripts/dev-stack2.ps1 -SkipXxx fuer andere)
HINDSIGHT_DB_URL="postgresql://postgres@127.0.0.1:5433/hindsight_dev" \
  go test -tags goolm -count=1 ./internal/storage/...
```

Without `HINDSIGHT_DB_URL` or `POSTGRES_DSN`, the Postgres tests skip (SKIP,
not FAIL). Unit tests (`TestClassifyMediaType`, etc.) run in any environment.
