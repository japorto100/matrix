# exec-secrets-bootstrap — Env-Files + SOPS+age Setup

**Datum**: 2026-04-17
**Scope**: Komplette `.env`-Struktur, Secret-Generation, SOPS+age Encrypted-Master-Pattern
**Status**: ✅ Implementiert

## Motivation

Nach dem `claude/merge-frontend-chat-ui-2OqmH` Branch-Merge hatten wir:
- Viele neue env-variablen (170+ über alle Services)
- `.env.example` Files teilweise inkonsistent (`env.example.merger` statt `.env.example`)
- Keine echten `.env` Files für Dev-Mode (localhost vs. Container)
- Kein zentrales Secret-Management
- Shared-Secrets (KEY_ENCRYPTION_SECRET, INGESTION_WORKER_SHARED_SECRET) nicht sync zwischen go+python

## Lösung — Hybrid SOPS+age Pattern

**Ein SOPS-encrypted YAML als Master**, daraus werden per-Service `.env` Files generiert.

```
secrets/stack.enc.yaml (committable, SOPS-encrypted)
       │
       │ sops -d + scripts/sync-secrets.sh
       ▼
.env                         ← docker-compose root
go-appservice/.env.development + .env.production
python-backend/.env + .env.development + .env.production
frontend_merger/.env.local + .env.development + .env.production
control-ui/.env.local + .env.development + .env.production
```

### Warum Hybrid, nicht pur zentral?

- Services lesen weiterhin **normale `.env` Files** (kein sops-decrypt bei jedem Start)
- SOPS ist Source-of-Truth für Multi-Machine + Team-Collaboration
- Shared-Secrets (KEY_ENCRYPTION_SECRET) einmal definieren → in alle .env propagiert
- Private Keys bleiben lokal (~/.config/sops/age/keys.txt)

## Was wurde erstellt

### Scripts

| Datei | Zweck |
|---|---|
| `scripts/bootstrap-env.py` | Initial-Setup: generiert secrets + alle .env Files + homeserver/registration.yaml + SOPS master |
| `scripts/sync-secrets.sh` | Daily-Use: `sops -d secrets/stack.enc.yaml` + propagiert values in per-service `.env` |
| `scripts/harden-env.py` | Existing Tool erweitert — regeneriert insecure defaults bei Bedarf |

### Config Files

| Datei | Status | Inhalt |
|---|---|---|
| `.sops.yaml` | ✅ committable | SOPS config mit age-public-key, regex für `secrets/*.yaml` |
| `secrets/stack.enc.yaml` | ✅ committable | SOPS-encrypted Master mit allen Secrets |
| `secrets/stack.yaml` | ❌ gitignored | Plain temp (falls manuell editiert) |
| `.gitignore` | ✅ updated | Plus `secrets/stack.yaml`, `secrets/*.yaml.plain` |

### Env-Files (22 total)

```
Repo-Root (docker-compose vars):
  .env, .env.development, .env.production, .env.example

go-appservice (GO_ENV flag):
  .env.development (native-dev, localhost URLs)
  .env.production (container-mode, service-names)
  .env.example

python-backend:
  .env (default alias), .env.development, .env.production, .env.example
  ingestion/.env.example (subservice, inherits from parent)

frontend_merger (Next.js 3-mode):
  .env.local (developer override), .env.development, .env.production, .env.example

control-ui (Next.js):
  .env.local, .env.development, .env.production, .env.example

agent-chat (Next.js):
  .env.example (existing, unchanged)

nextjs-chat (Next.js):
  .env.local.example (existing, unchanged)
```

### Matrix Config

- `homeserver/registration.yaml` — **neu generiert**, referenced von tuwunel.toml, AS/HS tokens matchen go-appservice/.env.*

## Generierte Secrets (14)

| Secret | Format | Shared In |
|---|---|---|
| `KEY_ENCRYPTION_SECRET` | 64 hex (32 bytes) | go + python (AES-GCM Vault) |
| `INGESTION_WORKER_SHARED_SECRET` | 64 hex | go + python (anti-SSRF HMAC) |
| `MATRIX_AS_TOKEN` | 64 hex | go + registration.yaml |
| `MATRIX_HS_TOKEN` | 64 hex | go + registration.yaml |
| `MATRIX_CRYPTO_PICKLE_KEY` | 64 hex | go (E2EE SQLite) |
| `ARTIFACT_STORAGE_SIGNING_SECRET` | 64 hex | go (signed URLs HMAC) |
| `AUTH_JWT_SECRET` | 64 hex | go (JWT) |
| `MATRIX_KEY_BACKUP_PASSWORD` | 24 alphanum | go (Megolm backup) |
| `MATRIX_BOT_PASSWORD` | 24 alphanum | python (bot login) |
| `POSTGRES_PASSWORD` | 24 alphanum | root + go + python |
| `OPENOBSERVE_PASSWORD` | 24 alphanum | go + python (telemetry) |
| `OPEN_SANDBOX_API_KEY` | 64 hex | root + python (sandbox auth) |
| `LIVEKIT_API_KEY` | 24 alphanum | root (LiveKit server API) |
| `LIVEKIT_API_SECRET` | 36 alphanum | root (LiveKit server API) |

## Workflow

### Initial Setup (einmalig, schon erledigt)

```bash
# 1. Generate secrets + all .env files
cd ~/code/matrix
python3 scripts/bootstrap-env.py

# 2. age-key generieren
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt

# 3. .sops.yaml mit public key (bootstrap-env.py macht das automatisch)

# 4. Encrypt master
sops -e secrets/stack.yaml > secrets/stack.enc.yaml
rm secrets/stack.yaml
```

### Daily: Secrets editieren

```bash
# Öffnet decrypted in $EDITOR, auto-re-encrypt on save
sops secrets/stack.enc.yaml

# Propagiert changes in alle service .env files
./scripts/sync-secrets.sh

# Verify
./scripts/sync-secrets.sh --check
```

### Multi-Machine Onboarding

```bash
# 1. git clone
git clone https://github.com/japorto100/matrix.git
cd matrix

# 2. age-private-key von USB/KeePassXC kopieren
mkdir -p ~/.config/sops/age
cp /media/usb/matrix-age-master.key ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt

# 3. Decrypt + sync
./scripts/sync-secrets.sh
```

## age Key Info

**Public Key** (in `.sops.yaml`, committable):
```
age1rmky9cgc73nytcfxak9l0jrusufjaslzy4vuvkyahxvlp99xmg7s490uu6
```

**Private Key** (NIEMALS committen):
- Location: `~/.config/sops/age/keys.txt`
- Permissions: 0600
- Backup empfohlen: KeePassXC Attachment + USB-Stick

## Offene Punkte

1. **API-Keys** müssen User-provided werden:
   - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`
   - `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN` / `FINBERT_HF_API_TOKEN`
   - `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (optional)
   - `NEXT_PUBLIC_TAMBO_API_KEY` (optional)
   - `CLOUDFLARED_TUNNEL_TOKEN` (nur für Named Tunnels, nicht für Quick Tunnel)

2. **Matrix Bot Login** → erzeugt `MATRIX_BOT_ACCESS_TOKEN`, muss nach erstem Bot-Start via `matrix-commander` geholt werden.

3. **MATRIX_ACCESS_TOKEN** in frontend_merger → nach User-Login via Matrix-Client.

## Related

- `docs/env-vars.md` — Referenz aller env-variablen
- [SOPS Documentation](https://github.com/getsops/sops)
- [age Documentation](https://github.com/FiloSottile/age)
- MINT-SETUP-OVERVIEW.md Section 10 "Security & Secrets"

## Verify-Gates

- [x] `scripts/bootstrap-env.py` läuft ohne Fehler
- [x] 16 Files erstellt (verifiziert via ls)
- [x] `sops -d secrets/stack.enc.yaml` decrypted successful
- [x] `./scripts/sync-secrets.sh --check` zeigt alle 4 Sections
- [x] Keine Secrets im git committed (verifiziert `git ls-files | grep -E '\.env$'`)
- [x] `.sops.yaml` public-key matches age-key-file
- [ ] API-Keys vom User providen (pending)
- [ ] Integration-Test: dev-stack.sh + alle Services können starten (pending verification)
