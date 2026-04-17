"use client";

// useWaveSurfer — wavesurfer.js v7 React hook
// Creates and manages a WaveSurfer instance bound to a container ref.

import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";

interface UseWaveSurferOptions {
	url: string | null;
	waveColor?: string;
	progressColor?: string;
	height?: number;
}

export function useWaveSurfer(
	containerRef: React.RefObject<HTMLDivElement | null>,
	{ url, waveColor = "#3f3f46", progressColor = "#10b981", height = 80 }: UseWaveSurferOptions,
) {
	const wsRef = useRef<WaveSurfer | null>(null);
	const [isPlaying, setIsPlaying] = useState(false);
	const [isReady, setIsReady] = useState(false);
	const [currentTime, setCurrentTime] = useState(0);
	const [duration, setDuration] = useState(0);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!containerRef.current || !url) return;

		setIsReady(false);
		setError(null);
		setIsLoading(true);

		const ws = WaveSurfer.create({
			container: containerRef.current,
			waveColor,
			progressColor,
			height,
			barWidth: 2,
			barGap: 1,
			barRadius: 2,
			cursorColor: "transparent",
			interact: true,
			normalize: true,
		});

		ws.on("ready", () => {
			setDuration(ws.getDuration());
			setIsReady(true);
			setIsLoading(false);
		});

		ws.on("audioprocess", () => {
			setCurrentTime(ws.getCurrentTime());
		});

		ws.on("play", () => setIsPlaying(true));
		ws.on("pause", () => setIsPlaying(false));
		ws.on("finish", () => setIsPlaying(false));

		ws.on("error", (err) => {
			setError(String(err));
			setIsLoading(false);
		});

		ws.load(url);
		wsRef.current = ws;

		return () => {
			ws.destroy();
			wsRef.current = null;
			setIsReady(false);
			setIsPlaying(false);
		};
	}, [url, waveColor, progressColor, height, containerRef]);

	const togglePlay = () => wsRef.current?.playPause();
	const seek = (seconds: number) =>
		wsRef.current?.seekTo(seconds / (wsRef.current.getDuration() || 1));

	return { isPlaying, isReady, isLoading, currentTime, duration, error, togglePlay, seek };
}
