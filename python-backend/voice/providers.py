"""
Voice Provider Factory — provider-agnostische STT/TTS/LLM Auswahl via ENV.

AGENT_STT_PROVIDER = whisper-local | openai        (default: whisper-local)
AGENT_TTS_PROVIDER = piper | openai | kokoro        (default: piper)
AGENT_PROVIDER     = anthropic | openai | openai-compatible (default: anthropic)
AGENT_MODEL        = model override (optional)
"""

from __future__ import annotations

import os


def get_stt():
    """Returns a LiveKit STT plugin instance based on AGENT_STT_PROVIDER."""
    provider = os.getenv("AGENT_STT_PROVIDER", "whisper-local")

    if provider == "openai":
        from livekit.plugins.openai import STT
        return STT()

    # Default: faster-whisper (open source, lokal)
    from livekit.plugins.silero import VAD  # noqa: F401 — ensures silero is importable
    try:
        from livekit_whisper import WhisperSTT
        model = os.getenv("WHISPER_MODEL", "base")
        return WhisperSTT(model=model)
    except ImportError:
        # Fallback: OpenAI Whisper API wenn faster-whisper nicht verfügbar
        from livekit.plugins.openai import STT
        return STT()


def get_tts():
    """Returns a LiveKit TTS plugin instance based on AGENT_TTS_PROVIDER."""
    provider = os.getenv("AGENT_TTS_PROVIDER", "piper")

    if provider == "openai":
        from livekit.plugins.openai import TTS
        voice = os.getenv("AGENT_TTS_VOICE", "alloy")
        return TTS(voice=voice)

    if provider == "kokoro":
        try:
            from livekit_kokoro import KokoroTTS
            return KokoroTTS()
        except ImportError:
            pass

    # Default: Piper TTS (open source, lokal)
    try:
        from livekit_piper import PiperTTS
        return PiperTTS()
    except ImportError:
        # Fallback: OpenAI TTS wenn Piper nicht verfügbar
        from livekit.plugins.openai import TTS
        return TTS(voice=os.getenv("AGENT_TTS_VOICE", "alloy"))


def get_llm():
    """Returns a LiveKit LLM plugin instance based on AGENT_PROVIDER."""
    provider = os.getenv("AGENT_PROVIDER", "anthropic")
    model = os.getenv("AGENT_MODEL", "")

    if provider == "anthropic":
        from livekit.plugins.anthropic import LLM
        return LLM(model=model or "claude-sonnet-4-6")

    # openai + openai-compatible (Ollama, OpenRouter, vLLM, LM Studio)
    from livekit.plugins.openai import LLM
    kwargs = {}
    if model:
        kwargs["model"] = model
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return LLM(**kwargs)


def get_vad():
    """Returns Silero VAD (Voice Activity Detection) — immer Open Source."""
    from livekit.plugins.silero import VAD
    return VAD.load()
