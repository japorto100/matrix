"use client";

import { mxcToThumbnail } from "@matrix/lib/utils";
import { Download, FileText, Image as ImageIcon, Link2 } from "lucide-react";
import type { Room } from "matrix-js-sdk";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { type LightboxItem, MediaLightbox } from "./MediaLightbox";

interface Props {
	room: Room | null;
}

interface MediaEntry {
	eventId: string;
	mxcUrl: string;
	msgtype: string;
	body?: string;
	mimeType?: string;
	filename?: string;
}

export function SharedMedia({ room }: Props) {
	const [lightbox, setLightbox] = useState<LightboxItem | null>(null);

	if (!room) return null;

	const events = room
		.getLiveTimeline()
		.getEvents()
		.filter((ev) => ev.getType() === "m.room.message");

	const toEntry = (
		ev: ReturnType<typeof room.getLiveTimeline>["getEvents"] extends () => Array<infer T>
			? T
			: never,
	): MediaEntry | null => {
		const content = ev.getContent() as Record<string, unknown> | undefined;
		const mxcUrl = content?.url as string | undefined;
		const msgtype = content?.msgtype as string | undefined;
		if (!mxcUrl || !msgtype) return null;
		const info = content?.info as Record<string, unknown> | undefined;
		return {
			eventId: ev.getId() ?? "",
			mxcUrl,
			msgtype,
			body: content?.body as string | undefined,
			mimeType: info?.mimetype as string | undefined,
			filename: content?.filename as string | undefined,
		};
	};

	const mediaItems = events
		.filter((ev) => ["m.image", "m.video"].includes((ev.getContent()?.msgtype as string) ?? ""))
		.map(toEntry)
		.filter((e): e is MediaEntry => !!e);

	const fileItems = events
		.filter((ev) => ["m.file", "m.audio"].includes((ev.getContent()?.msgtype as string) ?? ""))
		.map(toEntry)
		.filter((e): e is MediaEntry => !!e);

	const linkItems = events.filter((ev) => (ev.getContent()?.body as string)?.match(/https?:\/\//));

	if (mediaItems.length === 0 && fileItems.length === 0 && linkItems.length === 0) return null;

	const openLightbox = (entry: MediaEntry) => {
		setLightbox({
			eventId: entry.eventId,
			msgtype: entry.msgtype,
			mxcUrl: entry.mxcUrl,
			mimeType: entry.mimeType,
			filename: entry.filename,
			body: entry.body,
		});
	};

	const handleDirectDownload = async (entry: MediaEntry) => {
		try {
			const resp = await fetch(
				`/api/matrix/media?mxc=${encodeURIComponent(entry.mxcUrl.slice(6))}`,
			);
			const blob = await resp.blob();
			const href = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = href;
			a.download = entry.filename ?? entry.body ?? "datei";
			a.click();
			URL.revokeObjectURL(href);
		} catch (err) {
			console.error("[shared-media] download failed:", err);
		}
	};

	return (
		<div>
			<label className="text-xs font-medium text-muted-foreground mb-2 block">
				Geteilte Medien
			</label>

			{mediaItems.length > 0 && (
				<div className="mb-3">
					<p className="text-[10px] text-muted-foreground mb-1">
						<ImageIcon className="h-3 w-3 inline mr-1" />
						Medien ({mediaItems.length})
					</p>
					<div className="flex flex-wrap gap-1">
						{mediaItems.slice(0, 6).map((entry) => {
							const src = mxcToThumbnail(entry.mxcUrl, "", 60, 60);
							return (
								<button
									key={entry.eventId}
									type="button"
									className="p-0 border-0 bg-transparent cursor-pointer hover:opacity-80 transition-opacity"
									onClick={() => openLightbox(entry)}
									title={entry.body ?? "Ansehen"}
								>
									{/* biome-ignore lint/performance/noImgElement: Thumbnail, Matrix-URLs dynamisch */}
									<img src={src} alt="" className="h-12 w-12 rounded object-cover" loading="lazy" />
								</button>
							);
						})}
						{mediaItems.length > 6 && (
							<div className="text-[10px] text-muted-foreground self-end">
								+{mediaItems.length - 6}
							</div>
						)}
					</div>
				</div>
			)}

			{fileItems.length > 0 && (
				<div className="mb-3">
					<p className="text-[10px] text-muted-foreground mb-1">
						<FileText className="h-3 w-3 inline mr-1" />
						Dateien ({fileItems.length})
					</p>
					<div className="flex flex-col gap-1">
						{fileItems.slice(0, 5).map((entry) => (
							<div
								key={entry.eventId}
								className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted/30 group/file"
							>
								<FileText className="h-3 w-3 text-muted-foreground shrink-0" />
								<span className="text-[10px] text-muted-foreground flex-1 truncate">
									{entry.filename ?? entry.body ?? "Datei"}
								</span>
								<Button
									variant="ghost"
									size="icon"
									className="h-5 w-5 opacity-0 group-hover/file:opacity-100 shrink-0"
									onClick={() => void handleDirectDownload(entry)}
									title="Herunterladen"
								>
									<Download className="h-3 w-3" />
								</Button>
							</div>
						))}
					</div>
				</div>
			)}

			{linkItems.length > 0 && (
				<div>
					<p className="text-[10px] text-muted-foreground mb-1">
						<Link2 className="h-3 w-3 inline mr-1" />
						Links ({linkItems.length})
					</p>
					{linkItems.slice(0, 3).map((ev) => {
						const body = ev.getContent()?.body as string;
						const match = body?.match(/https?:\/\/[^\s]+/);
						return match ? (
							<a
								key={ev.getId()}
								href={match[0]}
								target="_blank"
								rel="noopener noreferrer"
								className="text-[10px] text-primary truncate block hover:underline"
							>
								{match[0]}
							</a>
						) : null;
					})}
				</div>
			)}

			<MediaLightbox item={lightbox} onClose={() => setLightbox(null)} />
		</div>
	);
}
