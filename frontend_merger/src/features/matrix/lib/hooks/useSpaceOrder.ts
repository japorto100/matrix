"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "matrix.spaceOrder";

function loadOrder(): string[] {
	if (typeof window === "undefined") return [];
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return [];
		const parsed = JSON.parse(raw) as unknown;
		return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
	} catch {
		return [];
	}
}

function saveOrder(order: string[]) {
	if (typeof window === "undefined") return;
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(order));
	} catch {
		/* ignore */
	}
}

/**
 * N5 — Lokale Space-Reihenfolge via localStorage.
 *
 * Matrix-Protokoll kennt keinen cross-client-stabilen Space-Order-State; Element-Web
 * nutzt ebenfalls lokale Preferences. Pattern: lokal-only, UI macht explizit, dass
 * die Reihenfolge nur auf diesem Geraet gilt.
 *
 * API:
 *  - `sortSpaces(spaces)` — reiht die uebergebene Liste laut gespeicherter Order;
 *    unbekannte Spaces haengen am Ende in SDK-Default-Reihenfolge.
 *  - `moveSpace(sourceId, targetId, before)` — schiebt sourceId vor/nach targetId.
 */
export function useSpaceOrder() {
	const [order, setOrder] = useState<string[]>(() => loadOrder());

	useEffect(() => {
		saveOrder(order);
	}, [order]);

	const sortSpaces = useCallback(
		<T extends { roomId: string }>(spaces: T[]): T[] => {
			if (order.length === 0) return spaces;
			const indexOf = new Map(order.map((id, i) => [id, i]));
			return [...spaces].sort((a, b) => {
				const ai = indexOf.get(a.roomId);
				const bi = indexOf.get(b.roomId);
				if (ai === undefined && bi === undefined) return 0;
				if (ai === undefined) return 1;
				if (bi === undefined) return -1;
				return ai - bi;
			});
		},
		[order],
	);

	const moveSpace = useCallback(
		(sourceId: string, targetId: string, before: boolean, knownIds: string[]) => {
			// Basis: bekannte Reihenfolge der gerenderten Spaces (damit neue Spaces integriert werden).
			const base = order.length > 0 ? mergeWithKnown(order, knownIds) : knownIds;
			const withoutSource = base.filter((id) => id !== sourceId);
			const targetIdx = withoutSource.indexOf(targetId);
			if (targetIdx === -1) return;
			const insertAt = before ? targetIdx : targetIdx + 1;
			withoutSource.splice(insertAt, 0, sourceId);
			setOrder(withoutSource);
		},
		[order],
	);

	return useMemo(() => ({ sortSpaces, moveSpace }), [sortSpaces, moveSpace]);
}

function mergeWithKnown(order: string[], knownIds: string[]): string[] {
	const kept = order.filter((id) => knownIds.includes(id));
	const newOnes = knownIds.filter((id) => !kept.includes(id));
	return [...kept, ...newOnes];
}
