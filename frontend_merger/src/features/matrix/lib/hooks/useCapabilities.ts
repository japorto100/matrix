"use client";

import { useQuery } from "@tanstack/react-query";
import type { MatrixClient } from "matrix-js-sdk";
import type { Capabilities } from "matrix-js-sdk/lib/serverCapabilities";

/**
 * Liest die Server-Capabilities einmal pro Session und cached sie via
 * React-Query.
 *
 * Server-Capabilities sagen uns was der Homeserver unterstuetzt — relevant
 * fuer Feature-Gating:
 *  - `m.change_password.enabled` → Password-Change-UI rendern?
 *  - `m.set_displayname.enabled` → Displayname-Edit aktivieren?
 *  - `m.set_avatar_url.enabled` → Avatar-Edit aktivieren?
 *  - `m.room_versions.available` → Room-Upgrade-UI mit richtiger default-version
 *
 * Capabilities aendern sich nicht waehrend einer Session (Homeserver restart
 * triggert Matrix-Re-Login). Daher `staleTime: Infinity` und `gcTime` hoch.
 *
 * Return: `data` ist typed `Capabilities | undefined` (undefined waehrend
 * initial fetch). `isLoading`/`error` fuer UI-Feedback.
 */
export function useCapabilities(client: MatrixClient | null) {
	return useQuery<Capabilities>({
		queryKey: ["matrix", "capabilities", client?.getUserId() ?? null],
		queryFn: async () => {
			if (!client) throw new Error("Kein Matrix-Client.");
			return client.getCapabilities();
		},
		enabled: !!client,
		staleTime: Number.POSITIVE_INFINITY,
		gcTime: 1000 * 60 * 60, // 1h
		retry: 1,
	});
}
