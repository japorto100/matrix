"use client";

// AC47: Voice-Input via Web Speech API (Chrome/Edge)
// Extracted from AgentChatComposer.tsx

import { useCallback, useEffect, useRef, useState } from "react";

// ── Web Speech API Types ────────────────────────────────────────────────────

interface SpeechRecognitionEvent extends Event {
	results: SpeechRecognitionResultList;
}
interface SpeechRecognitionResultList {
	readonly length: number;
	[index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionResult {
	readonly length: number;
	[index: number]: SpeechRecognitionAlternative;
	readonly isFinal: boolean;
}
interface SpeechRecognitionAlternative {
	readonly transcript: string;
}
interface SpeechRecognitionInstance extends EventTarget {
	lang: string;
	interimResults: boolean;
	maxAlternatives: number;
	onresult: ((ev: SpeechRecognitionEvent) => void) | null;
	onerror: ((ev: Event) => void) | null;
	onend: (() => void) | null;
	start(): void;
	stop(): void;
	abort(): void;
}
declare global {
	interface Window {
		SpeechRecognition?: new () => SpeechRecognitionInstance;
		webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
	}
}

// ── Hook ────────────────────────────────────────────────────────────────────

export type VoiceState = "inactive" | "listening" | "processing";

export function useSpeechInput(onTranscript: (text: string) => void) {
	const [voiceState, setVoiceState] = useState<VoiceState>("inactive");
	const recRef = useRef<SpeechRecognitionInstance | null>(null);

	const isSupported =
		typeof window !== "undefined" &&
		(window.SpeechRecognition !== undefined || window.webkitSpeechRecognition !== undefined);

	const startListening = useCallback(() => {
		if (!isSupported) return;
		const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
		if (!Ctor) return;
		const rec = new Ctor();
		rec.lang = navigator.language || "en-US";
		rec.interimResults = false;
		rec.maxAlternatives = 1;

		rec.onresult = (ev) => {
			const transcript = ev.results[0]?.[0]?.transcript ?? "";
			if (transcript) {
				setVoiceState("processing");
				onTranscript(transcript);
			}
		};
		rec.onerror = () => setVoiceState("inactive");
		rec.onend = () => setVoiceState("inactive");

		recRef.current = rec;
		rec.start();
		setVoiceState("listening");
	}, [isSupported, onTranscript]);

	const stopListening = useCallback(() => {
		recRef.current?.stop();
		recRef.current = null;
		setVoiceState("inactive");
	}, []);

	const toggleVoice = useCallback(() => {
		if (voiceState === "inactive") startListening();
		else stopListening();
	}, [voiceState, startListening, stopListening]);

	useEffect(
		() => () => {
			recRef.current?.abort();
		},
		[],
	);

	return { voiceState, isSupported, toggleVoice };
}
