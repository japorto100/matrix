# Tooling — Lint, Format, Typecheck

## Übersicht

Alle Tooling-Konfigurationen werden 1:1 aus dem Hauptprojekt übernommen,
um minimale Anpassungen beim späteren Portieren zu gewährleisten.

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

## Python — pyproject.toml (Root + Agent Bridge)

Angepasst aus dem Hauptprojekt. Nur was für die Matrix-Integration relevant ist.

### python-agent-bridge/pyproject.toml

Vollständiger Inhalt in `specs/03-python-agent-bridge.md`.

### Ruff Config (aus Hauptprojekt)

```toml
[tool.ruff]
exclude = [".venv", ".venv/**"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # Line length — Biome/Black übernimmt
```

### Typecheck (basedpyright / ty)

```toml
# pyproject.toml Root
[dependency-groups]
dev = [
    "ruff>=0.13.0",
    "basedpyright>=1.34.0",
    "pytest>=8.3",
    "pytest-asyncio>=0.23",
]
```

```powershell
cd python-agent-bridge
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

## .gitignore

```gitignore
# Go
go-appservice/bin/
go-appservice/*.exe

# Python
python-agent-bridge/.venv/
python-agent-bridge/__pycache__/
python-agent-bridge/data/
**/__pycache__/
**/*.pyc

# Next.js
nextjs-chat/.next/
nextjs-chat/node_modules/
nextjs-chat/.env.local

# Homeserver
homeserver/data/
homeserver/tuwunel
homeserver/tuwunel.exe

# Secrets — niemals committen
**/.env
**/.env.local
**/registration.yaml

# Logs
logs/
*.log
```

---

## CI (lokal, kein GitHub Actions für diese Phase)

```powershell
# Alle Checks in einem Schritt
function Invoke-AllChecks {
    Write-Host "── Go ─────────────────────────────────────" -ForegroundColor Blue
    Push-Location go-appservice
    go vet ./...
    golangci-lint run ./...
    go test ./...
    Pop-Location

    Write-Host "── Python ──────────────────────────────────" -ForegroundColor Green
    Push-Location python-agent-bridge
    uv run ruff check .
    uv run basedpyright .
    uv run pytest
    Pop-Location

    Write-Host "── Next.js ─────────────────────────────────" -ForegroundColor Magenta
    Push-Location nextjs-chat
    bun run typecheck
    bun run lint:ci
    bun run test:unit
    Pop-Location

    Write-Host "✅ All checks passed" -ForegroundColor Green
}

Invoke-AllChecks
```
