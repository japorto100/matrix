"use client";

import { ExternalLink, MapPin } from "lucide-react";
import { osmEmbedUrl } from "@/lib/matrix/geo";

export interface LocationEmbedProps {
	lat: number;
	lon: number;
	label?: string;
	zoom?: number;
	className?: string;
	height?: number;
}

/**
 * Lightweight OSM embed via iframe. Zero map-library dependencies, SSR-safe.
 * Works in both Matrix chat (m.location) and Agent chat (tool results).
 */
export function LocationEmbed({
	lat,
	lon,
	label,
	zoom = 15,
	className,
	height = 200,
}: LocationEmbedProps) {
	const embedSrc = osmEmbedUrl(lat, lon, zoom);
	const osmLink = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=${zoom}`;

	return (
		<div className={className}>
			<iframe
				title={label ?? `Location ${lat}, ${lon}`}
				src={embedSrc}
				width="100%"
				height={height}
				style={{ border: "1px solid var(--border, #333)", borderRadius: 8 }}
				loading="lazy"
				referrerPolicy="no-referrer"
			/>
			<a
				href={osmLink}
				target="_blank"
				rel="noopener noreferrer"
				className="flex items-center gap-1.5 mt-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
			>
				<MapPin className="h-3 w-3 shrink-0" />
				<span>{label ?? `${lat.toFixed(5)}, ${lon.toFixed(5)}`}</span>
				<ExternalLink className="h-3 w-3 shrink-0 ml-auto" />
			</a>
		</div>
	);
}
