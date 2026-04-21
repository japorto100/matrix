# Voice Subsystem — Agent Voice-Chat

**Status**: 🚧 **Under Construction** — funktional (LiveKit-basiert), aber Vendor-Lock reduzierbar.

## Was das ist

Voice-Layer für den Agent. **2 Use-Cases**:

### 1. Matrix Group-Calls mit AI-Teilnehmer (primary)
Der Agent **joined** als virtueller Teilnehmer eine Matrix-Group-Call-Session (Element Call). User sprechen — Agent hört zu (STT), versteht (LLM), antwortet mit Voice (TTS). Voll duplex.

```
User spricht in Matrix-Call
  ↓ Audio via WebRTC → LiveKit SFU (:7880)
  ↓ Agent (als Room-Teilnehmer) empfängt stream
  ↓ worker.py → STT (whisper-local oder OpenAI)
  ↓ pipeline.py → LLM (providers.py::get_llm)
  ↓ TTS (piper oder OpenAI)
  ↓ Audio-Response via LiveKit zurück in Room
User hört Agent
```

### 2. Standalone Agent Voice-Chat (non-Matrix, secondary)
User ohne Matrix-Setup soll 1:1 Voice-Chat mit Agent haben können — ohne dass er Matrix-Stack starten muss. **Aktuell nicht implementiert**, siehe TODO.

```
Browser (frontend_merger) mit Mic-Access
  ↓ WebRTC direct oder WebSocket audio
  ↓ Python voice worker
  ↓ STT → LLM → TTS
  ↓ Audio zurück
Browser spielt response
```

## Architecture

```
voice/
├─ __init__.py
├─ providers.py     ← Factory-functions für LLM/STT/TTS/VAD
│                     Nutzt env-vars: AGENT_PROVIDER, AGENT_MODEL,
│                     AGENT_STT_PROVIDER, AGENT_TTS_PROVIDER, AGENT_TTS_VOICE
├─ pipeline.py      ← LiveKit-Agent pipeline glue (room join + stream handling)
├─ worker.py        ← Entry-point, subscribes to room-events
└─ pyproject.toml   ← deps: livekit-agents, plugins (anthropic/openai/whisper/piper)
```

## Current Vendor-Lock

| Component | Aktuelle Implementierung | Vendor-Risk |
|---|---|---|
| **LiveKit Server** | `livekit/livekit-server` image (Apache 2.0) | 🟢 Low — OSS, self-hostable |
| **LiveKit Agents SDK** | `livekit-agents` Python package (Apache 2.0) | 🟢 Low — OSS |
| **STT Default** | OpenAI Whisper via cloud API | 🔴 **Vendor-lock** |
| **STT Alternative** | `whisper-local` (Faster-Whisper) | 🟢 Local, no vendor |
| **TTS Default** | `piper` (open-source neural TTS) | 🟢 Local, no vendor |
| **TTS Alternative** | OpenAI TTS `alloy` voice | 🔴 Cloud-lock |
| **LLM Plugin** | Anthropic/OpenAI direct SDK (LiveKit plugins) | 🟡 **Cloud-lock**, umgeht LiteLLM |
| **VAD** | Silero VAD (local) | 🟢 Local |

**Key Issue**: LLM-Plugin-Layer nutzt direkt anthropic/openai APIs — umgeht zentrale LiteLLM-Routing-Schicht die sonst im Agent-Stack genutzt wird.

**Warum umgeht Voice LiteLLM?**: LiveKit-Agents brauchen **low-latency streaming** (first-token-latency <500ms kritisch für natürliche Konversation). Plugins haben optimierte streaming-connections direkt zu Provider. LiteLLM-Proxy würde 100-300ms latency addieren.

## TODO — Vendor-Lock reduzieren

### Priority 1: Fully-Local Dev-Default
Aktuell läuft Voice nur mit Cloud-API-Keys (Anthropic/OpenAI). Für vollständig offline Dev:

- [ ] **LLM**: Ollama Plugin für `livekit-agents` integrieren
  → Config: `AGENT_PROVIDER=openai-compatible` + `AGENT_MODEL=llama3.3` + `OPENAI_BASE_URL=http://localhost:11434/v1`
  → Existierende Infrastructure (Ollama native installiert, config via mise)
- [ ] **STT**: `whisper-local` als default (schon installiert — base-model)
  → `AGENT_STT_PROVIDER=whisper-local` als default statt `off`
- [ ] **TTS**: `piper` bleibt default ✓
- [ ] **Fallback-chain**: wenn Cloud-keys leer → automatisch local-mode

### Priority 2: Standalone (non-Matrix) Voice-Chat

Aktuell: Voice erfordert Matrix-Call (LiveKit-room joined via Matrix-signalling).

Ziel: User kann im **frontend_merger** Voice-button klicken → direkt mit Agent reden.

Ideen:
- [ ] **WebRTC-direct**: Browser → livekit-server (ohne Matrix-signalling) → python worker
  Benötigt: eigene Room-Creation im lk-jwt-service für Non-Matrix users
- [ ] **Alternative: WebSocket-Audio**: Browser → py-backend :8094/ws/voice → streams
  Vermeidet LiveKit-komplett, nutzt WhisperLive-Pattern
  → könnte `AGENT_STT_PROVIDER=whisper-live` sein
- [ ] **UI**: Mic-Button in frontend_merger → `features/agent/components/VoiceInput.tsx` (noch nicht vorhanden)

### Priority 3: Open-Source LLM-Plugin via LiteLLM

Latency-Problem lösen:
- LiteLLM v1.50+ hat **native-streaming** für provider passthrough
- LiveKit-Agent-Plugin schreiben das LiteLLM statt direkt-Provider nutzt:
  ```python
  class LiteLLMPlugin(LLM):
      def __init__(self):
          self.base_url = "http://localhost:4000"
          self.api_key = os.environ["LITELLM_MASTER_KEY"]
      async def chat_stream(...): ...
  ```
  → Vorteil: unified billing/rate-limiting, per-user virtual-keys
  → Nachteil: +50-100ms latency (tolerable)
- [ ] `AGENT_PROVIDER=litellm` als neue Option

### Priority 4: Self-Hosted STT Upgrades

Whisper-local läuft aktuell via API-mode (HTTP localhost:8095). Alternativen:
- [ ] **WhisperX** (forced-alignment + word-timestamps) für besseres VAD-handoff
- [ ] **Faster-Whisper** (CTranslate2-based, 4× schneller als openai/whisper)
- [ ] **Kyutai STT** (neu 2024, streaming-first architecture)

### Priority 5: Multi-lingual TTS

Piper default ist en_US. Für de/es/fr:
- [ ] Piper voice-packs für deutsche Sprache (Matrix-User oft DE)
- [ ] **Coqui TTS** als alternative (open source, multilingual)
- [ ] **Bark** (neural, emotional) — deutlich größer, optional

## Env-Vars (aktuell genutzt)

```env
# In python-backend/.env.development:
AGENT_PROVIDER=anthropic                    # or: openai, openai-compatible
AGENT_MODEL=                                 # model override (empty = provider-default)
AGENT_STT_PROVIDER=off                       # off | whisper-local | openai
AGENT_TTS_PROVIDER=piper                     # piper | openai | kokoro
AGENT_TTS_VOICE=                             # openai: alloy | piper: voice-filename
WHISPER_MODEL=base                           # tiny, base, small, medium, large
LIVEKIT_URL=ws://localhost:7880              # LiveKit-Server endpoint
OPENAI_BASE_URL=                             # für openai-compatible (Ollama/vLLM)
```

## Starten

```bash
# Voraussetzung: LiveKit-Server + lk-jwt-service laufen
podman-compose --profile calls up -d

# Voice-Worker starten:
cd python-backend/voice
uv run python worker.py
# → Worker joined rooms wenn Matrix-User Voice-Call startet
```

## Verify

- [ ] Matrix-Call mit Agent als Teilnehmer klappt (siehe exec-linux-setup-users-2026-04-17.md)
- [ ] STT/TTS-Qualität akzeptabel
- [ ] Latency <1s end-to-end (User spricht → Agent antwortet)
- [ ] Cloud-keys entfernen → fällt auf local (whisper + piper + ollama) zurück

## Related

- `docker-compose.yml` → `--profile calls` (coturn + livekit-server + lk-jwt-service)
- `homeserver/tuwunel.v1.6.toml` → `[turn_uris]` für coturn-Integration
- `homeserver/livekit.yaml` → LiveKit-Server-config
- LiveKit Matrix-Integration: https://github.com/element-hq/lk-jwt-service
- Element Call Spec: MSC3898 + MSC4075

## Warum Voice optional bleibt

Voice ist **resource-intensive** (STT-model ~150MB, TTS ~50MB, LiveKit ~80MB, plus LLM-streaming). Auf 8GB RAM-System: nur starten wenn wirklich genutzt (`--profile calls`). Text-Chat via agent-chat/nextjs-chat/frontend_merger ist primärer Use-Case, Voice ist Premium-Feature.
