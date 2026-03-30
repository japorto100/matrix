"""
LiveKit Agent Worker — Entry Point für den Voice AI Agent.

Start:
    cd python-backend
    uv run python -m voice.worker

Der Worker verbindet sich mit dem LiveKit SFU und wartet auf Rooms
mit dem Prefix "agent-voice-". Sobald ein User einen Voice-Chat startet,
joint der Agent automatisch und beginnt die STT→LLM→TTS Pipeline.

ENV:
    LIVEKIT_URL        = ws://localhost:7880
    LIVEKIT_API_KEY    = devkey
    LIVEKIT_API_SECRET = your-livekit-secret
"""

from __future__ import annotations

import logging

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli

from voice.pipeline import create_voice_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice.worker")


async def entrypoint(ctx: JobContext) -> None:
    """Called when a new agent-voice room is created."""
    logger.info("Voice agent joining room: %s", ctx.room.name)

    agent = create_voice_agent()

    # Agent subscribed nur Audio (kein Video nötig für Voice Chat)
    await agent.start(ctx.room)

    logger.info("Voice agent active in room: %s", ctx.room.name)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            auto_subscribe=AutoSubscribe.AUDIO_ONLY,
        ),
    )
