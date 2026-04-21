"use client";

import { useCallback, useEffect, useRef } from "react";

/**
 * Mount-Race-Guard fuer async-Flows.
 *
 * Gibt einen Callback zurueck der `false` returnt sobald die Komponente
 * unmounted ist. Verhindert setState-after-unmount-Warnings und unnoetige
 * Promise-Resolutions nach Navigation.
 *
 *   const alive = useAlive();
 *   void doWork().then((res) => { if (alive()) setState(res); });
 */
export function useAlive(): () => boolean {
	const mountedRef = useRef(true);
	useEffect(() => {
		mountedRef.current = true;
		return () => {
			mountedRef.current = false;
		};
	}, []);
	return useCallback(() => mountedRef.current, []);
}
