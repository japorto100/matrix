"use client";

// AC50: TTS autoplay for sealed assistant messages
// Extracted from AgentChatThread.tsx

import type { TextUIPart, UIMessage } from "ai";
import { useEffect, useRef } from "react";
import { EMOJI_STRIP_RE } from "../lib/utils";

/**
 * Autoplay TTS for the latest sealed assistant message.
 * Fetches audio from /api/audio/synthesize and plays via Web Audio API.
 */
export function useAutoplayTts(
	messages: UIMessage[],
	isStreaming: boolean,
	enabled: boolean,
): void {
	const abortRef = useRef<AbortController | null>(null);
	const srcRef = useRef<AudioBufferSourceNode | null>(null);
	const lastPlayedIdRef = useRef<string | null>(null);

	// Cleanup on unmount
	useEffect(
		() => () => {
			abortRef.current?.abort();
			try {
				srcRef.current?.stop();
			} catch {}
		},
		[],
	);

	useEffect(() => {
		if (!enabled || isStreaming) return;
		const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
		if (!lastAssistant || lastAssistant.id === lastPlayedIdRef.current) return;

		const isMsgStreaming = lastAssistant.parts.some(
			(p) => p.type === "text" && (p as TextUIPart & { state?: string }).state === "streaming",
		);
		if (isMsgStreaming) return;

		const text = lastAssistant.parts
			.filter((p): p is TextUIPart => p.type === "text")
			.map((p) => p.text)
			.join("")
			.replace(EMOJI_STRIP_RE, "")
			.trim();
		if (!text) return;

		lastPlayedIdRef.current = lastAssistant.id;
		abortRef.current?.abort();
		const ac = new AbortController();
		abortRef.current = ac;

		void (async () => {
			try {
				const res = await fetch("/api/audio/synthesize", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ text: text.slice(0, 4096) }),
					signal: ac.signal,
				});
				if (!res.ok || ac.signal.aborted) return;
				const buf = await res.arrayBuffer();
				if (ac.signal.aborted) return;
				const ctx = new AudioContext();
				const audioBuffer = await ctx.decodeAudioData(buf);
				if (ac.signal.aborted) return;
				const source = ctx.createBufferSource();
				source.buffer = audioBuffer;
				source.connect(ctx.destination);
				srcRef.current = source;
				source.start(0);
			} catch {
				// silent fail — autoplay is best-effort
			}
		})();
	}, [messages, isStreaming, enabled]);
}
