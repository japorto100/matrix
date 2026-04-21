"use client";

import { cryptoCallbacks, forgetAllSecretStorageKeys } from "@matrix/lib/secretStorageKeys";
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
			// cryptoCallbacks wird von bootstrapSecretStorage / device-verify aufgerufen
			// um den Session-Recovery-Key abzufragen (siehe secretStorageKeys.ts).
			cryptoCallbacks,
		};

	_client = createClient(clientOpts);

	// Rust WASM Crypto initialisieren (vodozemac — ersetzt libolm).
	// Hart scheitern wenn E2EE required (Default), sonst opt-in Dev/Bot-Pfad.
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
		// NEXT_PUBLIC_E2EE_REQUIRED default=true. Nur explizites "false" erlaubt weiterlaufen
		// (für Dev-Setups ohne WASM oder Bot-Testing-Accounts ohne E2EE).
		const e2eeRequired = process.env.NEXT_PUBLIC_E2EE_REQUIRED !== "false";
		const errorMessage = err instanceof Error ? err.message : String(err);
		const isWasmUnavailable =
			errorMessage.toLowerCase().includes("webassembly") ||
			errorMessage.toLowerCase().includes("wasm") ||
			err instanceof RangeError;

		if (e2eeRequired) {
			console.error("[matrix] Rust crypto init failed — E2EE required, aborting client init:", err);
			// Stale-Client-Prevention: beim nächsten Aufruf soll neu probiert werden,
			// nicht die halb-initialisierte Instanz zurückgegeben werden.
			_client.stopClient();
			_client = null;
			throw new Error(
				isWasmUnavailable
					? "E2EE konnte nicht initialisiert werden: WebAssembly ist in diesem Browser nicht verfügbar. Bitte WASM/JavaScript aktivieren oder einen anderen Browser verwenden."
					: `E2EE konnte nicht initialisiert werden: ${errorMessage}`,
			);
		}

		console.warn(
			"[matrix] Rust crypto init failed — E2EE disabled (opt-in via NEXT_PUBLIC_E2EE_REQUIRED=false):",
			err,
		);
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
		// Session-Recovery-Keys aus dem In-Memory-Cache entfernen.
		forgetAllSecretStorageKeys();
		console.info("[matrix] Client destroyed");
	}
}
