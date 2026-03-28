"use client";

import { Download, ExternalLink, Mic, Music } from "lucide-react";
import { useState } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { TextContent } from "./TextContent";

function formatDuration(ms: number): string {
	const s = Math.floor(ms / 1000);
	const m = Math.floor(s / 60);
	const sec = s % 60;
	return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function ImageContent({ message }: { message: ResolvedMessage }) {
	const [lightbox, setLightbox] = useState(false);
	const src = message.thumbnailUrl ?? message.url;
	if (!src) return <TextContent message={message} />;
	const hasCaption = message.body && message.body !== message.fileName;

	return (
		<>
			<button
				type="button"
				className="block p-0 border-0 bg-transparent cursor-pointer"
				onClick={() => setLightbox(true)}
				title="Bild vergrößern"
			>
				{/* biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch */}
				<img
					src={src}
					alt={message.fileName ?? message.body}
					style={{ width: 150, height: 150, maxWidth: 150, maxHeight: 150, objectFit: "contain" }}
					className="rounded-lg bg-muted/30"
					loading="lazy"
				/>
			</button>
			{hasCaption && <p className="text-sm mt-1">{message.body}</p>}
			{lightbox && (
				<Dialog open={lightbox} onOpenChange={setLightbox}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 bg-black/95 border-none overflow-hidden data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "Bild"}</DialogTitle>
						<div className="relative flex flex-col items-center justify-center h-full">
							{/* biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch */}
							<img
								src={message.url ?? src}
								alt={message.fileName ?? message.body}
								className="max-w-full max-h-[75vh] object-contain"
							/>
							<div className="absolute top-2 right-2 flex items-center gap-1">
								<a
									href={message.url ?? src}
									download={message.fileName ?? "image"}
									className="h-8 w-8 flex items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
									title="Herunterladen"
								>
									<Download className="h-4 w-4" />
								</a>
								<a
									href={message.url ?? src}
									target="_blank"
									rel="noopener noreferrer"
									className="h-8 w-8 flex items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
									title="In neuem Tab öffnen"
								>
									<ExternalLink className="h-4 w-4" />
								</a>
							</div>
							{message.fileName && (
								<p className="text-xs text-white/70 mt-2 pb-2">{message.fileName}</p>
							)}
						</div>
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

export function VideoContent({ message }: { message: ResolvedMessage }) {
	if (!message.url) return <TextContent message={message} />;
	return (
		<div className="space-y-1">
			<video
				src={message.url}
				controls
				poster={message.thumbnailUrl}
				className="rounded-lg bg-black"
				style={{ width: 250, height: 140, maxWidth: 250, maxHeight: 200, objectFit: "contain" }}
				preload="metadata"
			/>
			{message.fileName && (
				<p className="text-[10px] text-muted-foreground truncate">{message.fileName}</p>
			)}
		</div>
	);
}

export function AudioContent({ message }: { message: ResolvedMessage }) {
	if (!message.url) return <TextContent message={message} />;
	if (message.isVoice) {
		return (
			<div className="flex items-center gap-2 bg-muted/50 rounded-xl px-3 py-2 min-w-[200px]">
				<Mic className="h-4 w-4 text-primary shrink-0" />
				<audio src={message.url} controls className="h-8 flex-1 min-w-0" preload="metadata" />
				{message.duration && (
					<span className="text-[10px] text-muted-foreground shrink-0">
						{formatDuration(message.duration)}
					</span>
				)}
			</div>
		);
	}
	return (
		<div className="space-y-1">
			<div className="flex items-center gap-2">
				<Music className="h-4 w-4 text-primary shrink-0" />
				{message.fileName && (
					<span className="text-xs font-medium truncate">{message.fileName}</span>
				)}
				{message.duration && (
					<span className="text-[10px] text-muted-foreground">
						{formatDuration(message.duration)}
					</span>
				)}
			</div>
			<audio src={message.url} controls className="w-full h-8" preload="metadata" />
		</div>
	);
}

export function StickerContent({ message }: { message: ResolvedMessage }) {
	const src = message.thumbnailUrl ?? message.url;
	if (!src) return null;
	// biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch
	return (
		<img
			src={src}
			alt={message.body}
			className="max-w-[128px] max-h-[128px] object-contain"
			loading="lazy"
		/>
	);
}
