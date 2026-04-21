"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import type { MatrixClient } from "matrix-js-sdk";
import type {
	BackupTrustInfo,
	ImportRoomKeyProgressData,
	KeyBackupInfo,
	KeyBackupRestoreResult,
} from "matrix-js-sdk/lib/crypto-api";
import { CryptoEvent, ImportRoomKeyStage } from "matrix-js-sdk/lib/crypto-api";
import { useCallback, useEffect, useState } from "react";

export interface KeyBackupRestoreProgress {
	total: number;
	loaded: number;
}

export interface UseKeyBackupReturn {
	/** Aktuelle Backup-Version-Info vom Server (null wenn keines existiert). */
	info: KeyBackupInfo | null;
	/** Trust-Status des Backups (signed by cross-signing / trusted by any). */
	trust: BackupTrustInfo | null;
	/** Aktive Version gegen die dieses Device aktuell syncht (null = kein Backup aktiv). */
	activeVersion: string | null;
	/** Letzte Restore-Progress-Info (null = noch nicht oder zwischendrin). */
	restoreProgress: KeyBackupRestoreProgress | null;
	/** `true` waehrend Info/Trust/Version initial geladen wird. */
	loading: boolean;
	/** Fehler beim Laden oder Operations. */
	error: string | null;

	/** Manuell refreshen (z.B. nach bootstrapSecretStorage). */
	refresh: () => Promise<void>;
	/** Aktiviert den Backup-Engine (schreibt Megolm-Keys nach Server). */
	enable: () => Promise<void>;
	/**
	 * Erzeugt ein neues Backup (inkl. neuem Decryption-Key) — ALTE KEYS
	 * WERDEN UNBRAUCHBAR ausser User hat sie woanders gespeichert.
	 */
	reset: () => Promise<void>;
	/** Restored Keys aus dem Backup via Passphrase. */
	restoreWithPassphrase: (passphrase: string) => Promise<KeyBackupRestoreResult>;
	/** Restored Keys aus dem Backup (Recovery-Key muss in cryptoCallbacks verfuegbar sein). */
	restoreWithCachedKey: () => Promise<KeyBackupRestoreResult>;
}

/**
 * Konsolidierter Hook fuer Key-Backup-Management (Cinny-Inspired, SDK 41).
 *
 * Kombiniert die ursprunglich geplanten Sub-Hooks (useKeyBackupInfo,
 * useKeyBackupStatus, useKeyBackupSync, useKeyBackupTrust,
 * useRestoreBackupOnVerification, Progress-State) in einer einzigen API,
 * da die zugrundeliegenden crypto-Aufrufe alle dasselbe CryptoApi-Handle
 * benoetigen und die Sub-Hook-Trennung in Cinny hauptsaechlich durch
 * Cinny's jotai-Architektur motiviert war.
 *
 * Verwendung in BackupRestore UI (Tier C2):
 *  - Setup-Flow: `reset()` erzeugt neues Backup, `enable()` aktiviert es.
 *  - Restore-Flow: `restoreWithPassphrase(input)` laedt Keys zurueck,
 *    `restoreProgress` kann fuer Progress-UI verwendet werden.
 *  - Status-UI: `info`, `trust`, `activeVersion` direkt rendern.
 */
export function useKeyBackup(client: MatrixClient | null): UseKeyBackupReturn {
	const alive = useAlive();
	const [info, setInfo] = useState<KeyBackupInfo | null>(null);
	const [trust, setTrust] = useState<BackupTrustInfo | null>(null);
	const [activeVersion, setActiveVersion] = useState<string | null>(null);
	const [restoreProgress, setRestoreProgress] = useState<KeyBackupRestoreProgress | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const refresh = useCallback(async () => {
		if (!client) return;
		const crypto = client.getCrypto();
		if (!crypto) {
			setError("Crypto-API nicht initialisiert.");
			return;
		}
		setLoading(true);
		setError(null);
		try {
			const newInfo = await crypto.getKeyBackupInfo();
			const newActive = await crypto.getActiveSessionBackupVersion();
			const newTrust = newInfo ? await crypto.isKeyBackupTrusted(newInfo) : null;
			if (alive()) {
				setInfo(newInfo);
				setTrust(newTrust);
				setActiveVersion(newActive);
			}
		} catch (err) {
			if (alive()) {
				setError(err instanceof Error ? err.message : String(err));
			}
		} finally {
			if (alive()) setLoading(false);
		}
	}, [client, alive]);

	// Initial-Load bei Client-Ready.
	useEffect(() => {
		void refresh();
	}, [refresh]);

	// Reactive: bei Key-Backup-Status-Change (z.B. Remote-Reset, Trust-Change)
	// automatisch refreshen. Verhindert stale UI nach externen Aenderungen.
	// NB: CryptoEvent-Emitter ist MatrixClient (re-emittet), nicht CryptoApi selbst.
	useEffect(() => {
		if (!client) return;
		const handler = () => {
			void refresh();
		};
		client.on(CryptoEvent.KeyBackupStatus, handler);
		return () => {
			client.off(CryptoEvent.KeyBackupStatus, handler);
		};
	}, [client, refresh]);

	const enable = useCallback(async () => {
		if (!client) throw new Error("Kein Matrix-Client.");
		const crypto = client.getCrypto();
		if (!crypto) throw new Error("Crypto-API nicht initialisiert.");
		await crypto.checkKeyBackupAndEnable();
		await refresh();
	}, [client, refresh]);

	const reset = useCallback(async () => {
		if (!client) throw new Error("Kein Matrix-Client.");
		const crypto = client.getCrypto();
		if (!crypto) throw new Error("Crypto-API nicht initialisiert.");
		await crypto.resetKeyBackup();
		await refresh();
	}, [client, refresh]);

	const progressCallback = useCallback(
		(progress: ImportRoomKeyProgressData) => {
			if (!alive()) return;
			// Wir rendern nur den LoadKeys-Stage als Progress-Bar (Fetch ist kurz).
			if (progress.stage === ImportRoomKeyStage.LoadKeys) {
				setRestoreProgress({
					total: progress.total,
					loaded: progress.successes,
				});
			}
		},
		[alive],
	);

	const restoreWithPassphrase = useCallback(
		async (passphrase: string): Promise<KeyBackupRestoreResult> => {
			if (!client) throw new Error("Kein Matrix-Client.");
			const crypto = client.getCrypto();
			if (!crypto) throw new Error("Crypto-API nicht initialisiert.");
			setRestoreProgress({ total: 0, loaded: 0 });
			try {
				const result = await crypto.restoreKeyBackupWithPassphrase(passphrase, {
					progressCallback,
				});
				await refresh();
				return result;
			} finally {
				if (alive()) setRestoreProgress(null);
			}
		},
		[client, refresh, progressCallback, alive],
	);

	const restoreWithCachedKey = useCallback(async (): Promise<KeyBackupRestoreResult> => {
		if (!client) throw new Error("Kein Matrix-Client.");
		const crypto = client.getCrypto();
		if (!crypto) throw new Error("Crypto-API nicht initialisiert.");
		setRestoreProgress({ total: 0, loaded: 0 });
		try {
			const result = await crypto.restoreKeyBackup({ progressCallback });
			await refresh();
			return result;
		} finally {
			if (alive()) setRestoreProgress(null);
		}
	}, [client, refresh, progressCallback, alive]);

	return {
		info,
		trust,
		activeVersion,
		restoreProgress,
		loading,
		error,
		refresh,
		enable,
		reset,
		restoreWithPassphrase,
		restoreWithCachedKey,
	};
}
