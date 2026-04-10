"use client";

import { MapPin } from "lucide-react";
import { osmUrl, parseGeoUri } from "@/lib/matrix/geo";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { LocationEmbed } from "./LocationEmbed";
import { TextContent } from "./TextContent";

export function LocationContent({ message }: { message: ResolvedMessage }) {
	if (!message.location) return <TextContent message={message} />;

	const coords = parseGeoUri(message.location.geoUri);
	if (!coords) {
		// Fallback: plain link (unparseable geo URI)
		const url = osmUrl(message.location.geoUri);
		return (
			<a
				href={url}
				target="_blank"
				rel="noopener noreferrer"
				className="flex items-center gap-2 text-sm text-primary hover:underline"
			>
				<MapPin className="h-4 w-4 shrink-0" />
				<span>Standort öffnen</span>
			</a>
		);
	}

	return (
		<LocationEmbed lat={coords.lat} lon={coords.lon} zoom={15} height={180} className="max-w-sm" />
	);
}
