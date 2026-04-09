"use client";

// useHls — hls.js v1.5 hook for HLS video streaming
// Safari native HLS fallback: if HLS.isSupported() is false but video.canPlayType returns truthy,
// the src is assigned directly (native HLS via Media Source Extensions or native decoder).

import Hls from "hls.js";
import { useEffect, useRef } from "react";

interface UseHlsOptions {
	src: string | null;
	onError?: (msg: string) => void;
}

export function useHls(
	videoRef: React.RefObject<HTMLVideoElement | null>,
	{ src, onError }: UseHlsOptions,
) {
	const hlsRef = useRef<Hls | null>(null);

	useEffect(() => {
		const video = videoRef.current;
		if (!video || !src) return;

		// Destroy existing instance
		hlsRef.current?.destroy();
		hlsRef.current = null;

		const isHls = src.includes(".m3u8");

		if (isHls && Hls.isSupported()) {
			// hls.js path (Chrome, Firefox, Edge)
			const hls = new Hls({ enableWorker: true });
			hls.loadSource(src);
			hls.attachMedia(video);
			hls.on(Hls.Events.ERROR, (_, data) => {
				if (data.fatal) {
					onError?.(data.details ?? "HLS_FATAL_ERROR");
				}
			});
			hlsRef.current = hls;
		} else {
			// Native path: Safari HLS / non-HLS (mp4, webm)
			video.src = src;
		}

		return () => {
			hlsRef.current?.destroy();
			hlsRef.current = null;
		};
	}, [src, onError, videoRef]);
}
