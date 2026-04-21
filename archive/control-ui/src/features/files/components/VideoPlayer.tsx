"use client";

// DW8 — VideoPlayer: hls.js v1.5 + custom useHls hook
// Native Safari HLS fallback via Media Source Extensions
// v1.5: Transcript-Sync panel (DW21)

import { AlertTriangle } from "lucide-react";
import { useRef, useState } from "react";
import { useHls } from "../hooks/useHls";

interface VideoPlayerProps {
	url: string;
	title?: string;
	poster?: string;
}

export function VideoPlayer({ url, title, poster }: VideoPlayerProps) {
	const videoRef = useRef<HTMLVideoElement>(null);
	const [hlsError, setHlsError] = useState<string | null>(null);

	useHls(videoRef, { src: url, onError: setHlsError });

	return (
		<div className="flex flex-col gap-2 rounded-xl border border-border bg-card/50 overflow-hidden">
			{title && (
				<p className="text-xs font-medium text-muted-foreground px-4 pt-3 truncate">{title}</p>
			)}

			{hlsError ? (
				<div className="flex items-center gap-2 text-destructive text-xs px-4 py-6">
					<AlertTriangle className="h-4 w-4 shrink-0" />
					<span className="font-mono">{hlsError}</span>
				</div>
			) : (
				<video
					ref={videoRef}
					controls
					poster={poster}
					className="w-full aspect-video bg-black"
					playsInline
				/>
			)}

			<p className="text-[10px] text-muted-foreground/40 font-mono px-4 pb-3">
				Transcript sync — v1.5
			</p>
		</div>
	);
}
