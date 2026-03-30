"""
VoicePipelineAgent — Echtzeit Voice Chat über LiveKit WebRTC.

Architektur:
  Browser → WebRTC Audio → LiveKit SFU → VoicePipelineAgent
    → STT (faster-whisper/openai) → LLM (anthropic/openai) → TTS (piper/openai)
    → WebRTC Audio → Browser

Provider-agnostisch: STT/TTS/LLM via ENV umschaltbar (see providers.py).
Latenz: 200-500ms (End-of-Speech → Start-of-Response).
"""

from __future__ import annotations

from livekit.agents.voice import VoicePipelineAgent

from voice.providers import get_llm, get_stt, get_tts, get_vad


def create_voice_agent() -> VoicePipelineAgent:
    """Creates a VoicePipelineAgent with provider-agnostic STT/LLM/TTS."""
    return VoicePipelineAgent(
        vad=get_vad(),
        stt=get_stt(),
        llm=get_llm(),
        tts=get_tts(),
    )
