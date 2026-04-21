"use client";

import { checkIndexedDBSupport } from "@matrix/lib/featureCheck";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

type State = "checking" | "ok" | "no-idb";

/**
 * Wrapper der Browser-Voraussetzungen prueft bevor der Matrix-Client startet.
 *
 * Aktuell: IndexedDB-Availability. Bei Fehlen wird Klartext-Fallback-UI
 * gerendert statt children — Matrix darf in dem Fall nicht initialisiert
 * werden (waerde stumm fehlschlagen beim Store-Setup).
 */
export function FeatureCheck({ children }: { children: ReactNode }) {
	const [state, setState] = useState<State>("checking");

	useEffect(() => {
		let cancelled = false;
		void checkIndexedDBSupport().then((ok) => {
			if (!cancelled) setState(ok ? "ok" : "no-idb");
		});
		return () => {
			cancelled = true;
		};
	}, []);

	if (state === "checking") {
		return (
			<div className="flex h-full items-center justify-center p-8 text-sm text-muted-foreground">
				Browser-Features werden geprüft…
			</div>
		);
	}

	if (state === "no-idb") {
		return (
			<div className="flex h-full items-center justify-center p-8">
				<div className="max-w-md space-y-4 rounded-lg border border-destructive/30 bg-destructive/5 p-6">
					<h2 className="text-lg font-semibold">Browser-Feature fehlt</h2>
					<p className="text-sm">
						Matrix benötigt <strong>IndexedDB</strong> für die lokale Speicherung von Sync-Daten und
						Verschlüsselungs-Schlüsseln. IndexedDB ist in diesem Browser nicht verfügbar —
						vermutlich Private-Browsing-Modus oder Storage deaktiviert.
					</p>
					<p className="text-sm">
						Bitte Storage aktivieren oder einen normalen Browser-Tab nutzen.{" "}
						<a
							href="https://developer.mozilla.org/de/docs/Web/API/IndexedDB_API"
							rel="noreferrer noopener"
							target="_blank"
							className="underline"
						>
							Was ist IndexedDB?
						</a>
					</p>
				</div>
			</div>
		);
	}

	return <>{children}</>;
}
