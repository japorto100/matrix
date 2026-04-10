"use client";

import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import type { LatLngExpression } from "leaflet";

export interface LocationMapInnerProps {
	lat: number;
	lon: number;
	label?: string;
	zoom?: number;
	height?: number;
	className?: string;
}

function RecenterMap({ center, zoom }: { center: LatLngExpression; zoom: number }) {
	const map = useMap();
	useEffect(() => {
		map.setView(center, zoom);
	}, [map, center, zoom]);
	return null;
}

/**
 * Interactive Leaflet map. Must be loaded client-side only (no SSR).
 * This inner component is wrapped by LocationMap.tsx via next/dynamic.
 */
export function LocationMapInner({
	lat,
	lon,
	label,
	zoom = 15,
	height = 300,
	className,
}: LocationMapInnerProps) {
	const center: LatLngExpression = [lat, lon];

	useEffect(() => {
		// Fix default marker icon paths (Leaflet + bundler issue)
		import("leaflet").then((L) => {
			// biome-ignore lint: Leaflet internal prototype fix
			delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
			L.Icon.Default.mergeOptions({
				iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
				iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
				shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
			});
		});
	}, []);

	return (
		<div className={className} style={{ height, borderRadius: 8, overflow: "hidden" }}>
			<MapContainer
				center={center}
				zoom={zoom}
				style={{ height: "100%", width: "100%" }}
				scrollWheelZoom={false}
			>
				<TileLayer
					attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
					url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
				/>
				<Marker position={center}>
					{label && <Popup>{label}</Popup>}
				</Marker>
				<RecenterMap center={center} zoom={zoom} />
			</MapContainer>
		</div>
	);
}
