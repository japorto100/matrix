/**
 * Parsed geo: URI result (RFC 5870).
 * Used by both Matrix chat (m.location events) and Agent chat (tool results).
 */
export interface GeoCoordinates {
	lat: number;
	lon: number;
	uncertainty?: number;
}

/**
 * Parse a geo: URI (RFC 5870) into coordinates.
 * Format: geo:lat,lon;u=uncertainty
 *
 * @example parseGeoUri("geo:51.5008,0.1247;u=35")
 * // => { lat: 51.5008, lon: 0.1247, uncertainty: 35 }
 */
export function parseGeoUri(geoUri: string): GeoCoordinates | null {
	if (!geoUri.startsWith("geo:")) return null;

	const [, rest] = geoUri.split("geo:");
	if (!rest) return null;

	const [coords, ...params] = rest.split(";");
	const [latStr, lonStr] = (coords ?? "").split(",");

	const lat = Number.parseFloat(latStr ?? "");
	const lon = Number.parseFloat(lonStr ?? "");

	if (Number.isNaN(lat) || Number.isNaN(lon)) return null;

	let uncertainty: number | undefined;
	for (const param of params) {
		const [key, value] = param.split("=");
		if (key === "u" && value) {
			const u = Number.parseFloat(value);
			if (!Number.isNaN(u)) uncertainty = u;
		}
	}

	return { lat, lon, uncertainty };
}

/**
 * Build an OpenStreetMap link URL from a geo: URI.
 */
export function osmUrl(geoUri: string): string {
	const coords = parseGeoUri(geoUri);
	if (!coords) return "https://www.openstreetmap.org/";
	return `https://www.openstreetmap.org/?mlat=${coords.lat}&mlon=${coords.lon}&zoom=15`;
}

/**
 * Build an OpenStreetMap embeddable iframe URL.
 */
export function osmEmbedUrl(
	lat: number,
	lon: number,
	zoom = 15,
): string {
	const delta = 0.005;
	const bbox = `${lon - delta},${lat - delta},${lon + delta},${lat + delta}`;
	return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lon}`;
}
