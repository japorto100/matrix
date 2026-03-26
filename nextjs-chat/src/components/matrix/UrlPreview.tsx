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

/** B-5: Kleine OG-Karte unter einer Textnachricht. */
export function UrlPreview({ url }: Props) {
	const ctx = useContext(MatrixContext);
	const accessToken = ctx?.client?.getAccessToken() ?? undefined;
	const [data, setData] = useState<OgData | null>(previewCache.get(url) ?? null);

	useEffect(() => {
		if (previewCache.has(url)) return; // bereits gecacht (auch null = kein Preview)

		const controller = new AbortController();

		const headers: HeadersInit = {};
		if (accessToken) {
			headers.Authorization = `Bearer ${accessToken}`;
		}

		fetch(`/api/matrix/preview?url=${encodeURIComponent(url)}`, {
			signal: controller.signal,
			headers,
		})
			.then((r) => (r.ok ? r.json() : null))
			.then((d: OgData | null) => {
				previewCache.set(url, d);
				setData(d);
			})
			.catch(() => {
				previewCache.set(url, null);
			});

		return () => controller.abort();
	}, [url, accessToken]);

	if (!data?.["og:title"]) return null;

	const title = data["og:title"];
	const description = data["og:description"];
	const image = data["og:image"];
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
			{image && (
				// biome-ignore lint/performance/noImgElement: OG image URL ist extern/dynamisch
				<img src={image} alt="" className="w-16 h-16 object-cover shrink-0" loading="lazy" />
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
