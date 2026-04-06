"use client";

// DW7 — AudioPlayer: wavesurfer.js v7 waveform + play/pause/seek
// v1.5: Region-Plugin for transcript-sync (DW21)

import { AlertTriangle, Loader2, Pause, Play } from "lucide-react";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { useWaveSurfer } from "../hooks/useWaveSurfer";

function formatTime(seconds: number): string {
	const m = Math.floor(seconds / 60);
	const s = Math.floor(seconds % 60);
	return `${m}:${s.toString().padStart(2, "0")}`;
}

interface AudioPlayerProps {
	url: string;
	title?: string;
}

export function AudioPlayer({ url, title }: AudioPlayerProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const { isPlaying, isReady, isLoading, currentTime, duration, error, togglePlay } = useWaveSurfer(
		containerRef,
		{ url },
	);

	return (
		<div className="flex flex-col gap-3 rounded-xl border border-border bg-card/50 p-4">
			{title && <p className="text-xs font-medium text-muted-foreground truncate">{title}</p>}

			{error ? (
				<div className="flex items-center gap-2 text-destructive text-xs py-4">
					<AlertTriangle className="h-4 w-4 shrink-0" />
					<span className="font-mono">{error}</span>
				</div>
			) : (
				<>
					{/* Waveform container */}
					<div className="relative rounded-lg overflow-hidden bg-muted/20 min-h-[80px]">
						{isLoading && (
							<div className="absolute inset-0 flex items-center justify-center">
								<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
							</div>
						)}
						<div ref={containerRef} className={isLoading ? "opacity-0" : "opacity-100"} />
					</div>

					{/* Controls */}
					<div className="flex items-center gap-3">
						<Button
							variant="ghost"
							size="icon"
							className="h-8 w-8 shrink-0"
							onClick={togglePlay}
							disabled={!isReady}
						>
							{isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
						</Button>

						<span className="text-[10px] font-mono text-muted-foreground w-20 shrink-0">
							{formatTime(currentTime)} / {formatTime(duration)}
						</span>

						<span className="text-[10px] text-muted-foreground/40 font-mono ml-auto">
							Transcript sync — v1.5
						</span>
					</div>
				</>
			)}
		</div>
	);
}
