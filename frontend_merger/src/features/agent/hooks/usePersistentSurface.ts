"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
	syncState: "idle" | "loading" | "saving" | "error";
}

function storageKey(surfaceId: string): string {
	return `a2ui.surface.${surfaceId}`;
}

function readCache(surfaceId: string): Record<string, unknown> | null {
	try {
		const raw = window.localStorage.getItem(storageKey(surfaceId));
		if (!raw) return null;
		const parsed = JSON.parse(raw) as StoredSurface;
		if (parsed.schema_version !== SCHEMA_VERSION) {
			window.localStorage.removeItem(storageKey(surfaceId));
			return null;
		}
		return parsed.surface_json;
	} catch {
		window.localStorage.removeItem(storageKey(surfaceId));
		return null;
	}
}

function writeCache(surfaceId: string, json: Record<string, unknown>): void {
	const entry: StoredSurface = {
		schema_version: SCHEMA_VERSION,
		surface_json: json,
		updated_at: new Date().toISOString(),
	};
	window.localStorage.setItem(storageKey(surfaceId), JSON.stringify(entry));
}

/**
 * Phase-2 (#31): BFF-synced with localStorage as a warm cache.
 *
 * Read path: localStorage first (instant render), server fetch in the
 * background; on success, reconcile and update state + cache. 404 from
 * the server is treated as "no server record" — the cache value stays.
 *
 * Write path: save() writes to localStorage (instant) and PUTs to the
 * server. Server errors are surfaced via syncState="error" but don't
 * revert the local value — the user's change is kept locally and will
 * retry on next save.
 *
 * No optimistic-concurrency at this phase; last-write-wins matches the
 * Go handler + the assumption that users don't race themselves.
 */
export function usePersistentSurface(surfaceId: string): PersistentSurfaceApi {
	const [surfaceJson, setSurfaceJson] = useState<Record<string, unknown> | null>(null);
	const [syncState, setSyncState] = useState<PersistentSurfaceApi["syncState"]>("idle");
	const hydrated = useRef(false);

	useEffect(() => {
		const cached = readCache(surfaceId);
		if (cached) setSurfaceJson(cached);

		let cancelled = false;
		setSyncState("loading");
		fetch(`/api/surfaces/${encodeURIComponent(surfaceId)}`, { cache: "no-store" })
			.then(async (res) => {
				if (cancelled) return;
				if (res.status === 404) {
					setSyncState("idle");
					return;
				}
				if (!res.ok) {
					setSyncState("error");
					return;
				}
				const body = (await res.json()) as StoredSurface;
				if (body.schema_version === SCHEMA_VERSION && body.surface_json) {
					setSurfaceJson(body.surface_json);
					writeCache(surfaceId, body.surface_json);
				}
				setSyncState("idle");
			})
			.catch(() => {
				if (!cancelled) setSyncState("error");
			})
			.finally(() => {
				hydrated.current = true;
			});

		return () => {
			cancelled = true;
		};
	}, [surfaceId]);

	const save = useCallback(
		(json: Record<string, unknown>) => {
			writeCache(surfaceId, json);
			setSurfaceJson(json);
			setSyncState("saving");
			void fetch(`/api/surfaces/${encodeURIComponent(surfaceId)}`, {
				method: "PUT",
				headers: { "content-type": "application/json" },
				body: JSON.stringify({ schema_version: SCHEMA_VERSION, surface_json: json }),
			})
				.then((res) => {
					setSyncState(res.ok ? "idle" : "error");
				})
				.catch(() => {
					setSyncState("error");
				});
		},
		[surfaceId],
	);

	const clear = useCallback(() => {
		window.localStorage.removeItem(storageKey(surfaceId));
		setSurfaceJson(null);
		setSyncState("saving");
		void fetch(`/api/surfaces/${encodeURIComponent(surfaceId)}`, { method: "DELETE" })
			.then((res) => {
				// 404 is fine — server already had no record.
				setSyncState(res.ok || res.status === 404 ? "idle" : "error");
			})
			.catch(() => {
				setSyncState("error");
			});
	}, [surfaceId]);

	return { surfaceJson, save, clear, syncState };
}
