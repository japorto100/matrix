"use client";

import { useCallback, useEffect, useState } from "react";

const SCHEMA_VERSION = 1;

interface StoredSurface {
	schema_version: number;
	surface_json: Record<string, unknown>;
	updated_at?: string;
}

export interface PersistentSurfaceApi {
	surfaceJson: Record<string, unknown> | null;
	save: (json: Record<string, unknown>) => void;
	clear: () => void;
}

function storageKey(surfaceId: string): string {
	return `a2ui.surface.${surfaceId}`;
}

/**
 * Phase-1: localStorage-only.
 *
 * Phase-2 will add BFF sync via /api/surfaces/[id] once go-appservice exposes
 * /api/v1/surfaces/*. Until then, surfaces are per-browser, per-origin — no
 * cross-device carry-over.
 */
export function usePersistentSurface(surfaceId: string): PersistentSurfaceApi {
	const [surfaceJson, setSurfaceJson] = useState<Record<string, unknown> | null>(null);

	useEffect(() => {
		const raw = window.localStorage.getItem(storageKey(surfaceId));
		if (!raw) return;
		try {
			const parsed = JSON.parse(raw) as StoredSurface;
			if (parsed.schema_version === SCHEMA_VERSION) {
				setSurfaceJson(parsed.surface_json);
			} else {
				window.localStorage.removeItem(storageKey(surfaceId));
			}
		} catch {
			window.localStorage.removeItem(storageKey(surfaceId));
		}
	}, [surfaceId]);

	const save = useCallback(
		(json: Record<string, unknown>) => {
			const entry: StoredSurface = {
				schema_version: SCHEMA_VERSION,
				surface_json: json,
				updated_at: new Date().toISOString(),
			};
			window.localStorage.setItem(storageKey(surfaceId), JSON.stringify(entry));
			setSurfaceJson(json);
		},
		[surfaceId],
	);

	const clear = useCallback(() => {
		window.localStorage.removeItem(storageKey(surfaceId));
		setSurfaceJson(null);
	}, [surfaceId]);

	return { surfaceJson, save, clear };
}
