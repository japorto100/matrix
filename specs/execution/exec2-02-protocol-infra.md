# exec2-02: Matrix Chat Protokoll + Infrastruktur

> Konsolidiert aus exec-03 Sektionen 3+4 (Protokoll-Level + Infrastruktur)
> Stand: 30.03.2026

---

## Protokoll-Level

### C-1: Sliding Sync (MSC3575/MSC4186)
- [x] SlidingSync Instanz mit Recency-Sorting, Lazy Member Loading
- [x] SDK v41.2.0 nutzt unstable MSC3575 Endpoint

### C-2: Authenticated Media (MSC3916)
- [x] Identisch mit QW-4 — durch Media-Proxy geloest

### C-3: Cross-Signing (MSC4153)
- [x] Go: Bootstrap MSK/SSK/USK, SignOwnDevice, Seeds-Persistence
- [x] Browser: useCrossSigning Hook, QR-Code Flow + SAS Emoji-Fallback
- [x] waitForPhase Terminal-State Guard Fix

### C-8: Go Appservice Key Backup
- [x] Megolm-Session-Keys Export/Import in verschluesselte Datei
- [x] Auto-Export nach jedem To-Device-Event + Shutdown

### C-10: MSC4381 — sender_key/device_id entfernt
- [x] Deprecated Felder aus m.room.encrypted Events entfernt (Privacy)

### D-1: E2EE Vollbetrieb (Szenario C)
- [x] Browser initRustCrypto() + Go OlmMachine
- [x] EnsureSession Fix + IndexedDBStore Fix

### D-2: Key Exchange
- [x] Key Upload, Query, One-Time Key Claiming — intern von mautrix-go

---

## Infrastruktur

### I-1: .env.development / .env.production Trennung
- [x] GO_ENV steuert welche Datei geladen wird
- [x] Saubere Dev/Prod Config

### I-2: Echte Crypto-Keys
- [x] openssl rand -hex 32 fuer alle Keys
- [x] Keine Platzhalter mehr

### I-3: MATRIX_AGENT_PREFIX konfigurierbar
- [x] Go: config.AgentPrefix
- [x] Next.js: NEXT_PUBLIC_MATRIX_AGENT_PREFIX

### HS-1: Homeserver-Config Audit
- [x] Room Version 12 (Project Hydra)
- [x] rocksdb_direct_io = false fuer WSL2+NTFS
- [x] DB Backups konfiguriert

---

## Offene Punkte (Backlog)

### C-4: Encrypted State Events (MSC3414/MSC4362)
- [ ] Wartet auf Tuwunel-Support — SDK vorbereitet

### OIDC/MAS Auth
- [ ] Tuwunel Legacy SSO evaluiert, MAS nicht kompatibel
- [ ] Fuer spaetere Portierung relevant
