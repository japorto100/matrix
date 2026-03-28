"use client";

import { MapPin } from "lucide-react";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { TextContent } from "./TextContent";

function osmUrl(geoUri: string): string {
	const [, coords] = geoUri.split(":");
	const [latLon] = (coords ?? "").split(";");
	const [lat, lon] = (latLon ?? "0,0").split(",");
	return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=15`;
}

export function LocationContent({ message }: { message: ResolvedMessage }) {
	if (!message.location) return <TextContent message={message} />;
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
