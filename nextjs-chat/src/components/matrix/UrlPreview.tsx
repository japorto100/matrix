"use client";

import { useContext, useEffect, useState } from "react";
import { MatrixContext } from "./MatrixProvider";

interface OgData {
	"og:title"?: string;
	"og:description"?: string;
	"og:image"?: string;
	"og:url"?: string;
	"matrix:image:size"?: number;
}

interface Props {
	url: string;
}

// Modul-scoped Cache — lebt solange die Seite offen ist
const previewCache = new Map<string, OgData | null>();

/** B-5: Kleine OG-Karte unter einer Textnachricht. Nutzt SDK getUrlPreview (Homeserver-seitig). */
export function UrlPreview({ url }: Props) {
	const ctx = useContext(MatrixContext);
	const client = ctx?.client ?? null;
	const [data, setData] = useState<OgData | null>(previewCache.get(url) ?? null);

	useEffect(() => {
		if (!client || previewCache.has(url)) return;

		let cancelled = false;
		client
			.getUrlPreview(url, Date.now())
			.then((d) => {
				if (cancelled) return;
				const ogData: OgData = {
					"og:title": d["og:title"] as string | undefined,
					"og:description": d["og:description"] as string | undefined,
					"og:image": d["og:image"] as string | undefined,
					"og:url": d["og:url"] as string | undefined,
					"matrix:image:size": d["matrix:image:size"] as number | undefined,
				};
				previewCache.set(url, ogData);
				setData(ogData);
			})
			.catch(() => {
				previewCache.set(url, null);
			});

		return () => {
			cancelled = true;
		};
	}, [url, client]);

	if (!data?.["og:title"]) return null;

	const title = data["og:title"];
	const description = data["og:description"];
	const image = data["og:image"];
	// OG image kann mxc:// sein (Homeserver cached es) — in HTTP umwandeln
	const imageSrc = image?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(image.slice(6))}`
		: image;
	const displayUrl = (() => {
		try {
			return new URL(url).hostname;
		} catch {
			return url;
		}
	})();

	return (
		<a
			href={url}
			target="_blank"
			rel="noopener noreferrer"
			className="flex gap-2 mt-1.5 rounded-lg border bg-muted/40 hover:bg-muted transition-colors overflow-hidden no-underline max-w-[320px]"
		>
			{imageSrc && (
				// biome-ignore lint/performance/noImgElement: OG image URL ist extern/dynamisch
				<img src={imageSrc} alt="" className="w-16 h-16 object-cover shrink-0" loading="lazy" />
			)}
			<div className="flex flex-col justify-center p-2 min-w-0">
				<p className="text-xs font-medium text-foreground truncate">{title}</p>
				{description && (
					<p className="text-[10px] text-muted-foreground line-clamp-2 mt-0.5">{description}</p>
				)}
				<p className="text-[10px] text-primary mt-1 truncate">{displayUrl}</p>
			</div>
		</a>
	);
}

// ─── URL-Erkennung ────────────────────────────────────────────────────────────

const URL_REGEX = /https?:\/\/[^\s<>"{}|\\^`[\]]+/;

/** Extrahiert die erste URL aus einem Text. */
export function extractFirstUrl(text: string): string | null {
	return text.match(URL_REGEX)?.[0] ?? null;
}
