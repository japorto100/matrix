"use client";

// AC47b: MediaRecorder fallback for Firefox/Safari (no webkitSpeechRecognition)
// Extracted from AgentChatComposer.tsx

import { useCallback, useEffect, useRef, useState } from "react";

export type MediaRecState = "inactive" | "recording" | "processing";

const TRANSCRIBE_URL = "/api/audio/transcribe";

export function useMediaRecorderInput(onTranscript: (t: string) => void, deviceId?: string) {
	const [state, setState] = useState<MediaRecState>("inactive");
	const recRef = useRef<MediaRecorder | null>(null);
	const chunksRef = useRef<Blob[]>([]);
	const streamRef = useRef<MediaStream | null>(null);

	const isSupported =
		typeof window !== "undefined" &&
		typeof MediaRecorder !== "undefined" &&
		typeof navigator?.mediaDevices?.getUserMedia === "function";

	const start = useCallback(async () => {
		if (!isSupported) return;
		try {
			const stream = await navigator.mediaDevices.getUserMedia({
				audio: deviceId ? { deviceId: { exact: deviceId } } : true,
			});
			streamRef.current = stream;
			const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
				? "audio/webm;codecs=opus"
				: "audio/webm";
			const recorder = new MediaRecorder(stream, { mimeType });
			chunksRef.current = [];
			recorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunksRef.current.push(e.data);
			};
			recorder.onstop = async () => {
				streamRef.current?.getTracks().forEach((t) => t.stop());
				streamRef.current = null;
				const blob = new Blob(chunksRef.current, { type: mimeType });
				setState("processing");
				try {
					const form = new FormData();
					form.append("file", blob, "recording.webm");
					const res = await fetch(TRANSCRIBE_URL, { method: "POST", body: form });
					if (res.ok) {
						const data = (await res.json()) as { text?: string };
						if (data.text) onTranscript(data.text);
					}
				} catch {
					// silent fail
				}
				setState("inactive");
			};
			recRef.current = recorder;
			recorder.start();
			setState("recording");
		} catch {
			setState("inactive");
		}
	}, [isSupported, deviceId, onTranscript]);

	const stop = useCallback(() => {
		recRef.current?.stop();
		recRef.current = null;
	}, []);

	const toggle = useCallback(() => {
		if (state === "recording") stop();
		else if (state === "inactive") void start();
	}, [state, start, stop]);

	useEffect(
		() => () => {
			recRef.current?.stop();
			streamRef.current?.getTracks().forEach((t) => t.stop());
		},
		[],
	);

	return { state, isSupported, toggle };
}
