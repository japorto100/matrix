"use client";

import {
	createClient,
	type ICreateClientOpts,
	IndexedDBStore,
	type MatrixClient,
} from "matrix-js-sdk";

export interface MatrixClientOptions {
	homeserverUrl: string;
	userId: string;
	accessToken: string;
	deviceId?: string;
}

let _client: MatrixClient | null = null;

/**
 * Erstellt oder gibt den bestehenden Matrix-Client zurück.
 * Singleton — nur ein Client pro Browser-Tab.
 */
export async function getMatrixClient(opts: MatrixClientOptions): Promise<MatrixClient> {
	if (_client) return _client;

	// D-1: IndexedDBStore für persistente Sync-State über Page-Reloads
	const store = new IndexedDBStore({
		indexedDB: globalThis.indexedDB,
		dbName: `matrix-sync-${opts.userId}`,
	});
	await store.startup();

	const clientOpts: ICreateClientOpts & { threadSupport?: boolean; pendingEventOrdering?: string } =
		{
			baseUrl: opts.homeserverUrl,
			userId: opts.userId,
			accessToken: opts.accessToken,
			deviceId: opts.deviceId,
			timelineSupport: true,
			threadSupport: true, // B-8: Thread-Unterstützung (MSC3440)
			pendingEventOrdering: "detached", // Fix: "chronological" crasht bei sendEvent/redact/etc.
			store,
		};

	_client = createClient(clientOpts);

	// Rust WASM Crypto initialisieren (vodozemac — ersetzt libolm)
	// Fallback: E2EE deaktiviert wenn WASM nicht verfügbar
	try {
		await _client.initRustCrypto();
		// MSC4153: In Prod nur an cross-signed-verifizierte Geräte senden.
		// Dev: false (Bot muss nicht verifiziert sein). Prod: true (Bot ist cross-signed).
		const blacklist = process.env.NEXT_PUBLIC_E2EE_BLACKLIST_UNVERIFIED === "true";
		const crypto = _client.getCrypto();
		if (crypto) crypto.globalBlacklistUnverifiedDevices = blacklist;
		console.info(
			`[matrix] Rust crypto initialized (E2EE enabled, blacklist=${blacklist ? "on" : "off"})`,
		);
	} catch (err) {
		console.warn("[matrix] Rust crypto init failed — E2EE disabled:", err);
	}

	return _client;
}

/**
 * Beendet den Matrix-Client und gibt den Singleton frei.
 * Aufrufen beim Unmounten der MatrixProvider-Komponente.
 */
export function destroyMatrixClient(): void {
	if (_client) {
		_client.stopClient();
		_client = null;
		console.info("[matrix] Client destroyed");
	}
}
