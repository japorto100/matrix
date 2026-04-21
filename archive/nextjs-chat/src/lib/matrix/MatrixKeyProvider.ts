/**
 * MatrixKeyProvider — Brücke zwischen matrix-js-sdk EncryptionKeys und LiveKit E2EE.
 *
 * matrix-js-sdk's MatrixRTCSession generiert und verteilt Encryption Keys
 * via m.rtc.member State Events (manageMediaKeys: true).
 * Diese Klasse nimmt die Keys entgegen und speist sie in LiveKit's
 * E2EE Worker ein (SFrame Encryption der Audio/Video Streams).
 */

import { BaseKeyProvider } from "livekit-client";

/**
 * Baut eine LiveKit-kompatible participantIdentity aus MatrixRTC Membership.
 * Format: userId:deviceId (LiveKit identifiziert Teilnehmer damit)
 */
export function makeParticipantIdentity(userId: string, deviceId: string): string {
	return `${userId}:${deviceId}`;
}

/**
 * MatrixKeyProvider — erweitert LiveKit's BaseKeyProvider.
 *
 * Nutzung:
 *   const keyProvider = new MatrixKeyProvider();
 *   // Bei EncryptionKeyChanged Event:
 *   await keyProvider.setEncryptionKey(rawKey, keyIndex, participantIdentity);
 *   // An LiveKit Room übergeben:
 *   new Room({ e2ee: { keyProvider, worker: new Worker(...) } });
 */
export class MatrixKeyProvider extends BaseKeyProvider {
	constructor() {
		super({ sharedKey: false, ratchetWindowSize: 0, failureTolerance: -1, keyringSize: 256 });
	}

	/**
	 * Setzt einen Encryption Key für einen Teilnehmer.
	 * Wird aufgerufen wenn MatrixRTCSession ein EncryptionKeyChanged Event emittiert.
	 */
	async setEncryptionKey(
		rawKey: Uint8Array,
		keyIndex: number,
		participantIdentity: string,
	): Promise<void> {
		// Raw Uint8Array → CryptoKey (AES-GCM 256-bit) für LiveKit E2EE
		const cryptoKey = await crypto.subtle.importKey(
			"raw",
			rawKey.buffer as ArrayBuffer,
			{ name: "AES-GCM", length: 256 },
			false,
			["encrypt", "decrypt"],
		);
		// Protected BaseKeyProvider method → emittiert SetKey Event an den E2EE Worker
		this.onSetEncryptionKey(cryptoKey, participantIdentity, keyIndex);
	}
}
