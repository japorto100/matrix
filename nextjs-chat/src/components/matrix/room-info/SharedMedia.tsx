"use client";

import { FileText, Image, Link2 } from "lucide-react";
import type { Room } from "matrix-js-sdk";
import { mxcToThumbnail } from "@/lib/matrix/utils";

interface Props {
	room: Room | null;
}

export function SharedMedia({ room }: Props) {
	if (!room) return null;
	const events = room
		.getLiveTimeline()
		.getEvents()
		.filter((ev) => ev.getType() === "m.room.message");
	const mediaItems = events.filter((ev) =>
		["m.image", "m.video"].includes(ev.getContent()?.msgtype as string),
	);
	const fileItems = events.filter((ev) =>
		["m.file", "m.audio"].includes(ev.getContent()?.msgtype as string),
	);
	const linkItems = events.filter((ev) =>
		(ev.getContent()?.body as string)?.match(/https?:\/\//),
	);
	if (mediaItems.length === 0 && fileItems.length === 0 && linkItems.length === 0) return null;

	return (
		<div>
			<label className="text-xs font-medium text-muted-foreground mb-2 block">
				Geteilte Medien
			</label>
			{mediaItems.length > 0 && (
				<div className="mb-2">
					<p className="text-[10px] text-muted-foreground mb-1">
						<Image className="h-3 w-3 inline mr-1" />
						Medien ({mediaItems.length})
					</p>
					<div className="flex flex-wrap gap-1">
						{mediaItems.slice(0, 6).map((ev) => {
							const url = ev.getContent()?.url as string;
							const src = url?.startsWith("mxc://") ? mxcToThumbnail(url, "", 60, 60) : undefined;
							return src ? (
								// biome-ignore lint/performance/noImgElement: Matrix-URLs dynamisch
								<img key={ev.getId()} src={src} alt="" className="h-12 w-12 rounded object-cover" loading="lazy" />
							) : null;
						})}
						{mediaItems.length > 6 && (
							<p className="text-[10px] text-muted-foreground self-end">+{mediaItems.length - 6}</p>
						)}
					</div>
				</div>
			)}
			{fileItems.length > 0 && (
				<div className="mb-2">
					<p className="text-[10px] text-muted-foreground mb-1">
						<FileText className="h-3 w-3 inline mr-1" />
						Dateien ({fileItems.length})
					</p>
					{fileItems.slice(0, 3).map((ev) => (
						<p key={ev.getId()} className="text-[10px] text-muted-foreground truncate">
							{(ev.getContent()?.body as string) ?? "Datei"}
						</p>
					))}
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
							<a key={ev.getId()} href={match[0]} target="_blank" rel="noopener noreferrer" className="text-[10px] text-primary truncate block hover:underline">
								{match[0]}
							</a>
						) : null;
					})}
				</div>
			)}
		</div>
	);
}
