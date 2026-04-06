# Tooling — Lint, Format, Typecheck

**Status:** Aktiv
**Stand:** 06.04.2026 — Konsolidiertes python-backend, golangci-lint v2, biome 2.3, ruff + basedpyright

## Uebersicht

Alle Tooling-Konfigurationen werden 1:1 aus dem Hauptprojekt uebernommen,
um minimale Anpassungen beim spaeteren Portieren zu gewaehrleisten.

---

## Go — .golangci.yml

Identisch mit `D:\tradingview-clones\tradeview-fusion\go-backend\.golangci.yml`.
Datei kommt unter `go-appservice/.golangci.yml`.

```yaml
# Run from go-appservice: golangci-lint run ./...
# golangci-lint v2.9+ config
version: "2"
run:
  timeout: 5m
  modules-download-mode: readonly
linters:
  enable:
    # --- standard baseline ---
    - errcheck
    - govet
    - ineffassign
    - staticcheck
    - unused
    # --- code quality ---
    - gocritic
    - exhaustive
    - revive
    - nolintlint
    - errorlint
    - wrapcheck
    # --- context safety ---
    - fatcontext
    # --- security ---
    - gosec
    # --- observability ---
    - spancheck
    - loggercheck
    # --- database ---
    - sqlclosecheck
    # --- modernization ---
    - modernize
  settings:
    staticcheck:
      checks:
        - "all"
        - "-SA1019"
        - "-ST1000"
        - "-ST1003"
    govet:
      enable:
        - shadow
        - waitgroup
        - hostport
    revive:
      rules:
        - name: exported
          disabled: true
        - name: var-naming
          disabled: true
    exhaustive:
      default-signifies-exhaustive: true
    nolintlint:
      require-explanation: true
      require-specific: true
    gosec:
      excludes:
        - G104
        - G304
    wrapcheck:
      ignore-sigs:
        - .Errorf(
        - errors.New(
        - errors.Unwrap(
        - .Wrap(
        - .Wrapf(
    spancheck:
      checks:
        - end
        - record-error
    loggercheck:
      require-string-key: true
      no-printf-like: true
  exclusions:
    rules:
      - path: _test\.go
        linters:
          - errcheck
          - gocritic
          - wrapcheck
          - gosec
```

### Go Lint ausführen

```powershell
cd go-appservice
golangci-lint run ./...
```

---

## Next.js — biome.json

Identisch mit Hauptprojekt (`D:\tradingview-clones\tradeview-fusion\biome.json`).
Datei kommt unter `nextjs-chat/biome.json`.

```json
{
  "$schema": "https://biomejs.dev/schemas/2.3.15/schema.json",
  "vcs": {
    "enabled": true,
    "clientKind": "git",
    "useIgnoreFile": true
  },
  "files": {
    "ignoreUnknown": true,
    "includes": [
      "src/**",
      "biome.json",
      "package.json",
      "tsconfig.json"
    ]
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "tab",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "complexity": {
        "noForEach": "off",
        "noStaticOnlyClass": "off"
      },
      "correctness": {
        "noUnusedVariables": "warn",
        "noUnusedImports": "warn",
        "useExhaustiveDependencies": "warn"
      },
      "suspicious": {
        "noExplicitAny": "warn",
        "noConsole": "off",
        "noRedeclare": "warn",
        "noArrayIndexKey": "warn"
      },
      "style": {
        "noNonNullAssertion": "off",
        "useConst": "warn",
        "noUnusedTemplateLiteral": "off",
        "useImportType": "warn"
      },
      "security": {
        "noDangerouslySetInnerHtml": "warn"
      },
      "a11y": {
        "recommended": false
      }
    }
  },
  "css": {
    "parser": {
      "cssModules": true,
      "tailwindDirectives": true
    },
    "linter": {
      "enabled": true
    }
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "semicolons": "always",
      "trailingCommas": "all"
    }
  },
  "overrides": [
    {
      "includes": ["src/app/api/**", "src/lib/server/**"],
      "linter": {
        "rules": {
          "suspicious": {
            "noConsole": {
              "level": "warn",
              "options": { "allow": ["error", "warn"] }
            }
          }
        }
      }
    }
  ],
  "assist": {
    "enabled": true,
    "actions": {
      "source": {
        "organizeImports": "on"
      }
    }
  }
}
```

### Biome Befehle

```powershell
cd nextjs-chat
bun run lint          # biome check ./src
bun run lint:fix      # biome check --write ./src
bun run format        # biome format --write ./src
```

---

## Next.js — tsconfig.json

Identisch mit Hauptprojekt. Datei kommt unter `nextjs-chat/tsconfig.json`.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "dom", "dom.iterable"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "tsBuildInfoFile": ".next/cache/tsbuildinfo.json",
    "noUncheckedIndexedAccess": true,
    "noFallthroughCasesInSwitch": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": [
    "next-env.d.ts",
    "src/**/*.ts",
    "src/**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": [
    ".next",
    "node_modules",
    "scripts"
  ]
}
```

---

## Python — pyproject.toml (`python-backend/`)

Konsolidierter `python-backend/pyproject.toml` enthaelt alle Subpackages
(agent, bridge, voice, mock, memory_engine, context, shared).
Vollstaendige Dependency-Liste siehe `agent-ui/05-backend-abhaengigkeiten.md`
und `03-python-agent-bridge.md` (NATS Consumer).

### Ruff Config (`python-backend/pyproject.toml`)

```toml
[tool.ruff]
exclude = [".venv", ".venv/**", "data/"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501", "N999"]  # E501: line length, N999: false positive (verzeichnis-name)
```

### Typecheck (basedpyright)

```toml
[dependency-groups]
dev = [
    "ruff>=0.13.0",
    "basedpyright>=1.34.0",
    "pytest>=8.3",
    "pytest-asyncio>=0.23",
]
```

```powershell
cd python-backend
uv run ruff check .         # Lint
uv run ruff format .        # Format
uv run basedpyright .       # Typecheck
uv run pytest               # Tests
```

---

## package.json Scripts (Next.js)

Analog zum Hauptprojekt:

```json
{
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "biome check ./src",
    "lint:fix": "biome check --write ./src",
    "lint:ci": "biome ci ./src",
    "lint:unsafe": "biome check --write --unsafe ./src",
    "format": "biome format --write ./src",
    "typecheck": "bunx tsc --noEmit",
    "test:unit": "bun test src/lib src/features",
    "test:frontend": "bun run typecheck && bun run lint:ci && bun run test:unit"
  }
}
```

---

## .gitignore (Auszug — siehe `.gitignore` im Repo-Root)

```gitignore
# Go
go-appservice/bin/
go-appservice/*.exe
go-appservice/data/

# Python
python-backend/.venv/
python-backend/__pycache__/
python-backend/data/
**/__pycache__/
**/*.pyc

# Next.js
nextjs-chat/.next/
nextjs-chat/node_modules/
nextjs-chat/.env.local
agent-chat/.next/
agent-chat/node_modules/

# Homeserver
homeserver/data/
homeserver/tuwunel
homeserver/tuwunel.exe

# Tools (binaries)
tools/*.exe
tools/tuwunel
tools/dendrite-src/
tools/zendrite-src/

# Secrets — niemals committen
**/.env
**/.env.local
**/registration.yaml

# Logs
logs/
*.log
```

---

## CI (lokal, kein GitHub Actions fuer diese Phase)

```powershell
# Alle Checks in einem Schritt
function Invoke-AllChecks {
    Write-Host "── Go ─────────────────────────────────────" -ForegroundColor Blue
    Push-Location go-appservice
    go vet -tags goolm ./...
    golangci-lint run --build-tags goolm ./...
    go test -tags goolm ./...
    Pop-Location

    Write-Host "── Python ──────────────────────────────────" -ForegroundColor Green
    Push-Location python-backend
    uv run ruff check .
    uv run basedpyright .
    uv run pytest
    Pop-Location

    Write-Host "── Next.js (matrix-chat) ───────────────────" -ForegroundColor Magenta
    Push-Location nextjs-chat
    bun run typecheck
    bun run lint:ci
    bun run test:unit
    Pop-Location

    Write-Host "── Next.js (agent-chat) ────────────────────" -ForegroundColor Cyan
    Push-Location agent-chat
    bun run typecheck
    bun run lint:ci
    Pop-Location

    Write-Host "All checks passed" -ForegroundColor Green
}

Invoke-AllChecks
```

---

## Tools-Binaries (Download-Befehle)

Alle Binaries liegen in `D:\matrix\tools\` (gitignored). Download-Befehle:

```powershell
# nats-server.exe
Invoke-WebRequest 'https://github.com/nats-io/nats-server/releases/download/v2.10.27/nats-server-v2.10.27-windows-amd64.zip' -OutFile tools/nats-server.zip -UseBasicParsing
Expand-Archive tools/nats-server.zip -DestinationPath tools/nats-tmp -Force
Move-Item tools/nats-tmp/nats-server-v2.10.27-windows-amd64/nats-server.exe tools/nats-server.exe
Remove-Item -Recurse tools/nats-tmp, tools/nats-server.zip

# cloudflared.exe (kein Account)
Invoke-WebRequest 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile tools/cloudflared.exe -UseBasicParsing

# bore.exe (kein Account)
Invoke-WebRequest 'https://github.com/ekzhang/bore/releases/download/v0.6.0/bore-v0.6.0-x86_64-pc-windows-msvc.zip' -OutFile tools/bore.zip -UseBasicParsing
Expand-Archive tools/bore.zip -DestinationPath tools/bore-tmp -Force
Move-Item tools/bore-tmp/bore.exe tools/bore.exe
Remove-Item -Recurse tools/bore-tmp, tools/bore.zip

# ngrok.exe (Account noetig: ngrok.com)
Invoke-WebRequest 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile tools/ngrok.zip -UseBasicParsing
Expand-Archive tools/ngrok.zip -DestinationPath tools/ -Force
Remove-Item tools/ngrok.zip

# Tuwunel v1.5.1 (Linux Binary, in WSL1 nutzen)
curl -L "https://github.com/matrix-construct/tuwunel/releases/download/v1.5.1/v1.5.1-release-all-x86_64-v2-linux-gnu-tuwunel.zst" -o tools/tuwunel.zst
zstd -d tools/tuwunel.zst -o tools/tuwunel
rm tools/tuwunel.zst
```
