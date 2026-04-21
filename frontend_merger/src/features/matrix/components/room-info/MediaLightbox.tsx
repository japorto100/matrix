"use client";

import { mxcToHttp } from "@matrix/lib/utils";
import { Download, ExternalLink, X } from "lucide-react";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export interface LightboxItem {
	eventId: string;
	msgtype: "m.image" | "m.video" | "m.audio" | "m.file" | string;
	mxcUrl: string;
	mimeType?: string;
	filename?: string;
	body?: string;
}

interface Props {
	item: LightboxItem | null;
	onClose: () => void;
}

/**
 * Full-Screen Lightbox fuer geteilte Media (D6).
 *
 * Darstellung nach msgtype:
 *  - m.image → <img> in voller Aufloesung, Download + Open-in-new-tab Buttons
 *  - m.video → <video controls>, Download + Open-Buttons
 *  - m.audio/m.file → File-Card mit Filename + Download-Button (kein Inline-Player)
 *
 * Keyboard: ESC schliesst. Multi-Image-Navigation (next/prev) ist explicit
 * aus dem Scope — Cinny hat das auch nicht, wir koennen das spaeter nachlegen.
 */
export function MediaLightbox({ item, onClose }: Props) {
	useEffect(() => {
		if (!item) return;
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [item, onClose]);

	if (!item) return null;

	const fullUrl = mxcToHttp(item.mxcUrl);
	const displayName = item.filename ?? item.body ?? "Datei";

	const handleDownload = async () => {
		try {
			const resp = await fetch(fullUrl);
			const blob = await resp.blob();
			const href = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = href;
			a.download = displayName;
			a.click();
			URL.revokeObjectURL(href);
		} catch (err) {
			console.error("[lightbox] download failed:", err);
			// Fallback: normaler Link-Click
			window.open(fullUrl, "_blank");
		}
	};

	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
			onClick={onClose}
			onKeyDown={(e) => {
				if (e.key === "Escape") onClose();
			}}
			role="dialog"
			aria-modal="true"
			tabIndex={-1}
		>
			{/* Top-Bar mit Actions */}
			<div className="absolute top-0 inset-x-0 flex items-center justify-between p-4 z-10 bg-gradient-to-b from-black/60 to-transparent">
				<p className="text-sm text-white truncate flex-1">{displayName}</p>
				<div className="flex items-center gap-1 shrink-0">
					<Button
						variant="ghost"
						size="icon"
						className="text-white hover:bg-white/10 h-8 w-8"
						onClick={(e) => {
							e.stopPropagation();
							void handleDownload();
						}}
						title="Herunterladen"
					>
						<Download className="h-4 w-4" />
					</Button>
					<Button
						variant="ghost"
						size="icon"
						className="text-white hover:bg-white/10 h-8 w-8"
						onClick={(e) => {
							e.stopPropagation();
							window.open(fullUrl, "_blank");
						}}
						title="In neuem Tab oeffnen"
					>
						<ExternalLink className="h-4 w-4" />
					</Button>
					<Button
						variant="ghost"
						size="icon"
						className="text-white hover:bg-white/10 h-8 w-8"
						onClick={onClose}
						title="Schliessen (ESC)"
					>
						<X className="h-4 w-4" />
					</Button>
				</div>
			</div>

			{/* Content */}
			<div
				className="max-w-[90vw] max-h-[90vh] flex items-center justify-center"
				onClick={(e) => e.stopPropagation()}
				onKeyDown={(e) => e.stopPropagation()}
				role="presentation"
			>
				{item.msgtype === "m.image" && (
					// biome-ignore lint/performance/noImgElement: Blob-URL, Lightbox-Preview
					<img
						src={fullUrl}
						alt={displayName}
						className="max-w-full max-h-[90vh] object-contain rounded"
					/>
				)}
				{item.msgtype === "m.video" && (
					<video src={fullUrl} controls autoPlay className="max-w-full max-h-[90vh] rounded" />
				)}
				{(item.msgtype === "m.audio" ||
					item.msgtype === "m.file" ||
					(item.msgtype !== "m.image" && item.msgtype !== "m.video")) && (
					<div className="bg-background rounded-lg p-8 text-center space-y-3 min-w-[320px]">
						<div className="text-lg font-medium">{displayName}</div>
						{item.mimeType && <div className="text-xs text-muted-foreground">{item.mimeType}</div>}
						{item.msgtype === "m.audio" ? (
							<audio src={fullUrl} controls className="w-full" />
						) : (
							<Button onClick={() => void handleDownload()} className="w-full">
								<Download className="h-4 w-4 mr-2" />
								Herunterladen
							</Button>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
