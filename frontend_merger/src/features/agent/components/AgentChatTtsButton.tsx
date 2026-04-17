"use client";

// AC49b: TTS-Button — BFF /api/audio/synthesize → Web Audio API, fallback to SpeechSynthesis
// Loader spinner during fetch, stop button during playback.

import { Loader2, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

const EMOJI_RE =
	/[\u{1F300}-\u{1FAFF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{FE00}-\u{FE0F}]/gu;

function stripEmoji(text: string): string {
	return text.replace(EMOJI_RE, "").trim();
}

interface AgentChatTtsButtonProps {
	text: string;
	onSpeakStart?: () => void;
	shouldStop?: boolean;
}

export function AgentChatTtsButton({ text, onSpeakStart, shouldStop }: AgentChatTtsButtonProps) {
	const [state, setState] = useState<"idle" | "loading" | "speaking">("idle");
	const audioCtxRef = useRef<AudioContext | null>(null);
	const sourceRef = useRef<AudioBufferSourceNode | null>(null);
	const uttRef = useRef<SpeechSynthesisUtterance | null>(null);
	const abortRef = useRef<AbortController | null>(null);

	const stop = useCallback(() => {
		abortRef.current?.abort();
		abortRef.current = null;
		sourceRef.current?.stop();
		sourceRef.current = null;
		window.speechSynthesis?.cancel();
		uttRef.current = null;
		setState("idle");
	}, []);

	const speakFallback = useCallback((clean: string) => {
		if (typeof window === "undefined" || !("speechSynthesis" in window)) {
			setState("idle");
			return;
		}
		const utt = new SpeechSynthesisUtterance(clean);
		utt.lang = navigator.language || "en-US";
		utt.onend = () => setState("idle");
		utt.onerror = () => setState("idle");
		uttRef.current = utt;
		window.speechSynthesis.cancel();
		window.speechSynthesis.speak(utt);
		setState("speaking");
	}, []);

	const toggleTts = useCallback(async () => {
		if (state !== "idle") {
			stop();
			return;
		}
		const clean = stripEmoji(text);
		if (!clean) return;

		onSpeakStart?.();
		setState("loading");

		try {
			const ac = new AbortController();
			abortRef.current = ac;

			const res = await fetch("/api/audio/synthesize", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ text: clean.slice(0, 4096) }),
				signal: ac.signal,
			});

			if (!res.ok) throw new Error(`HTTP ${res.status}`);

			const arrayBuf = await res.arrayBuffer();
			if (ac.signal.aborted) return;

			const ctx = new AudioContext();
			audioCtxRef.current = ctx;
			const audioBuffer = await ctx.decodeAudioData(arrayBuf);
			if (ac.signal.aborted) return;

			const source = ctx.createBufferSource();
			source.buffer = audioBuffer;
			source.connect(ctx.destination);
			source.onended = () => setState("idle");
			sourceRef.current = source;
			source.start(0);
			setState("speaking");
		} catch (err) {
			if (err instanceof DOMException && err.name === "AbortError") return;
			// Fallback to browser SpeechSynthesis
			speakFallback(clean);
		}
	}, [state, text, stop, onSpeakStart, speakFallback]);

	useEffect(() => {
		if (shouldStop && state !== "idle") stop();
	}, [shouldStop, state, stop]);

	useEffect(() => () => stop(), [stop]);

	return (
		<button
			type="button"
			onClick={() => void toggleTts()}
			className={`flex items-center gap-1 text-[10px] transition-colors ${
				state !== "idle" ? "text-primary" : "text-muted-foreground/50 hover:text-muted-foreground"
			}`}
			title={state === "idle" ? "Read aloud" : "Stop reading"}
		>
			{state === "loading" ? (
				<Loader2 className="h-3 w-3 animate-spin" />
			) : state === "speaking" ? (
				<VolumeX className="h-3 w-3" />
			) : (
				<Volume2 className="h-3 w-3" />
			)}
		</button>
	);
}
