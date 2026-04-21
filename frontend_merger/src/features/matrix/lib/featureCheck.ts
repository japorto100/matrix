"use client";

/**
 * Prueft ob IndexedDB im aktuellen Browser verfuegbar ist.
 *
 * Fail-fast-Gate vor Matrix-Client-Init: verhindert silent-fail bei
 * Private-Browsing, deaktivierter Storage oder Corporate-Firewalls die
 * IndexedDB sandboxen. Matrix-js-sdk nutzt IDB fuer Sync-Store und
 * Rust-Crypto fuer den Crypto-Store — ohne IDB kein E2EE-State persistent.
 *
 * Implementation: versucht eine Probe-Datenbank zu oeffnen, loescht sie
 * direkt nach Check. `indexedDB.open` kann synchron werfen (SecurityError
 * in strict Private-Mode), deshalb try-catch um den Call und Promise um
 * async success/error events.
 */
export async function checkIndexedDBSupport(): Promise<boolean> {
	if (typeof indexedDB === "undefined") return false;
	const dbName = `matrix-idb-probe-${Date.now()}`;
	return new Promise((resolve) => {
		let request: IDBOpenDBRequest;
		try {
			request = indexedDB.open(dbName);
		} catch {
			resolve(false);
			return;
		}
		request.onsuccess = () => {
			resolve(true);
			try {
				indexedDB.deleteDatabase(dbName);
			} catch {
				// Probe-DB Cleanup ist Best-Effort, Fehler hier sind irrelevant.
			}
		};
		request.onerror = () => {
			resolve(false);
			try {
				indexedDB.deleteDatabase(dbName);
			} catch {
				// dito.
			}
		};
	});
}
