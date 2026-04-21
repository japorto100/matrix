"use client";

import type { CryptoCallbacks } from "matrix-js-sdk/lib/crypto-api";

/**
 * In-Memory Cache fuer Secret-Storage Recovery-Keys (4S / MSC1946).
 *
 * Wird befuellt wenn der User eine Recovery-Passphrase eingibt oder einen
 * Recovery-Key direkt abgibt (spaeterer SecretStorage-/ManualVerification-UI-Flow).
 * Die matrix-js-sdk ruft anschliessend `cryptoCallbacks.getSecretStorageKey`
 * auf — waehrend `bootstrapSecretStorage`, waehrend Device-Verify oder wenn
 * ein neues Device die Session-Backup-Keys aus 4S laedt.
 *
 * Der Cache ist **tab-lokal und fluechtig**: Page-Reload, Tab-Close und Logout
 * leeren ihn. Keys werden nie in LocalStorage oder IndexedDB geschrieben — dort
 * landen nur die davon abgeleiteten Megolm-/Olm-Session-Keys via Rust-Crypto.
 */
const rememberedKeys = new Map<string, Uint8Array<ArrayBuffer>>();

/**
 * Haelt einen entschluesselten Recovery-Key bereit, damit die SDK ihn waehrend
 * der aktuellen Session ueber `cryptoCallbacks.getSecretStorageKey` abholen kann.
 */
export function rememberSecretStorageKey(keyId: string, privateKey: Uint8Array<ArrayBuffer>): void {
	if (!(privateKey instanceof Uint8Array)) {
		throw new Error("rememberSecretStorageKey: privateKey muss eine Uint8Array sein");
	}
	rememberedKeys.set(keyId, privateKey);
}

/** Leert den Session-Cache (bei Logout oder Client-Destroy aufrufen). */
export function forgetAllSecretStorageKeys(): void {
	rememberedKeys.clear();
}

/** Debug-Hilfe: aktuelle Anzahl gecachter Keys. */
export function getRememberedKeyCount(): number {
	return rememberedKeys.size;
}

/**
 * Callbacks die an `createClient({ cryptoCallbacks })` uebergeben werden.
 *
 * - `getSecretStorageKey` wird aufgerufen wenn die SDK einen Secret-Storage-Key
 *   benoetigt. Wir laufen durch die angefragten Key-IDs und returnen die erste
 *   die wir im Session-Cache haben. Wenn keiner matcht: `null` — die SDK wirft
 *   dann eine Exception in der aufrufenden Operation (z.B. `bootstrapSecretStorage`),
 *   die UI sollte das auf "Recovery-Passphrase erforderlich" mappen.
 *
 * - `cacheSecretStorageKey` wird aufgerufen wenn ein **neuer** Key erzeugt wird
 *   (z.B. beim ersten `bootstrapSecretStorage` Setup). Wir speichern ihn direkt,
 *   damit unmittelbar folgende SDK-Operationen nicht wieder nach dem Key fragen.
 */
export const cryptoCallbacks: CryptoCallbacks = {
	getSecretStorageKey: async (opts) => {
		for (const keyId of Object.keys(opts.keys)) {
			const candidate = rememberedKeys.get(keyId);
			if (candidate) return [keyId, candidate];
		}
		return null;
	},

	cacheSecretStorageKey: (keyId, _keyInfo, key) => {
		rememberedKeys.set(keyId, key);
	},
};
