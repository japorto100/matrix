"use client";

/**
 * Agent Voice Hook — LiveKit WebRTC Voice Chat.
 *
 * Verbindet direkt mit LiveKit Room (kein MatrixRTC — Agent ist kein Matrix-User).
 * Room-Name: "agent-voice-{threadId}"
 * Python VoicePipelineAgent subscribed automatisch und startet STT→LLM→TTS.
 *
 * Braucht: LiveKit SFU (Port 7880) + lk-jwt-service (Port 8080) + Voice Worker
 */

import { useCallback, useRef, useState } from "react";

export type VoiceStatus = "idle" | "connecting" | "active" | "disconnecting";

export interface UseAgentVoiceReturn {
	voiceStatus: VoiceStatus;
	/** LiveKit Token für <LiveKitRoom> */
	token: string | null;
	/** LiveKit Server URL */
	serverUrl: string | null;
	/** Voice starten */
	joinVoice: () => Promise<void>;
	/** Voice beenden */
	leaveVoice: () => Promise<void>;
}

const LK_JWT_SERVICE_URL = process.env.NEXT_PUBLIC_LK_JWT_SERVICE_URL;

async function fetchVoiceToken(threadId: string): Promise<{ token: string; url: string }> {
	if (!LK_JWT_SERVICE_URL) {
		throw new Error("NEXT_PUBLIC_LK_JWT_SERVICE_URL not configured");
	}
	const res = await fetch(`${LK_JWT_SERVICE_URL}/sfu/get`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			room: `agent-voice-${threadId}`,
			// Agent Voice nutzt eine vereinfachte Auth — kein Matrix OpenID nötig
			device_id: `voice-${Date.now()}`,
		}),
	});

	if (!res.ok) {
		throw new Error(`Voice JWT error: ${res.status} ${await res.text()}`);
	}

	const data = (await res.json()) as { jwt: string; url: string };
	return { token: data.jwt, url: data.url };
}

export function useAgentVoice(threadId: string | undefined): UseAgentVoiceReturn {
	const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
	const [token, setToken] = useState<string | null>(null);
	const [serverUrl, setServerUrl] = useState<string | null>(null);
	const roomRef = useRef<unknown>(null);

	const joinVoice = useCallback(async () => {
		if (!threadId || voiceStatus !== "idle") return;
		setVoiceStatus("connecting");

		try {
			const { token: jwt, url } = await fetchVoiceToken(threadId);
			setToken(jwt);
			setServerUrl(url);
			setVoiceStatus("active");
		} catch (err) {
			console.error("[agent-voice] join failed:", err);
			setVoiceStatus("idle");
			setToken(null);
			setServerUrl(null);
		}
	}, [threadId, voiceStatus]);

	const leaveVoice = useCallback(async () => {
		setVoiceStatus("disconnecting");
		roomRef.current = null;
		setToken(null);
		setServerUrl(null);
		setVoiceStatus("idle");
	}, []);

	return { voiceStatus, token, serverUrl, joinVoice, leaveVoice };
}
