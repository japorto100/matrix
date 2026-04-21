"use client";

import { useKeyBackup } from "@matrix/lib/hooks/useKeyBackup";
import type { MatrixClient } from "matrix-js-sdk";
import { CryptoEvent } from "matrix-js-sdk/lib/crypto-api/CryptoEvent";
import {
	VerificationPhase,
	type VerificationRequest,
	VerificationRequestEvent,
} from "matrix-js-sdk/lib/crypto-api/verification";
import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";

const SESSION_KEY = "matrix.autoRestoreDone";

interface Props {
	client: MatrixClient | null;
}

/**
 * N1 — Auto-Restore Key-Backup nach erfolgreicher Verifikation.
 *
 * Passive Komponente (rendert nichts). Lauscht auf
 * CryptoEvent.VerificationRequestReceived + Phase=Done und triggert
 * dann restoreWithCachedKey(). Zusaetzlich Initial-Try beim Mount, falls
 * Backup schon beim letzten Login trusted war.
 *
 * Dual-Guard gegen Double-Restore (Contrarian #3):
 *  - useRef restoreStartedRef: synchroner In-Memory-Flag, verhindert
 *    concurrent-mode-Race zwischen Initial-Effect und Event-Listener.
 *  - sessionStorage matrix.autoRestoreDone: verhindert nochmaligen
 *    Restore in derselben Session bei Multi-Verify (zweites Device).
 */
export function AutoRestoreBackupOnVerification({ client }: Props) {
	const kb = useKeyBackup(client);
	const kbRef = useRef(kb);
	kbRef.current = kb;
	const restoreStartedRef = useRef(false);

	const tryRestore = useCallback(async () => {
		if (!client) return;
		if (restoreStartedRef.current) return;
		if (typeof window !== "undefined" && sessionStorage.getItem(SESSION_KEY) === "true") return;
		const { info, trust, restoreWithCachedKey } = kbRef.current;
		if (!info || !trust?.trusted) return;

		restoreStartedRef.current = true;
		if (typeof window !== "undefined") {
			sessionStorage.setItem(SESSION_KEY, "true");
		}

		const toastId = toast.loading("Alte Nachrichten werden entschlüsselt…");
		try {
			const result = await restoreWithCachedKey();
			if (result.imported > 0) {
				toast.success(`${result.imported} alte Nachrichten entschlüsselt.`, { id: toastId });
			} else {
				toast.dismiss(toastId);
			}
		} catch {
			// Kein Cached-Secret, Backup-Mismatch, o.Ae. — silent skip.
			toast.dismiss(toastId);
			restoreStartedRef.current = false;
			if (typeof window !== "undefined") {
				sessionStorage.removeItem(SESSION_KEY);
			}
		}
	}, [client]);

	const tryRestoreRef = useRef(tryRestore);
	tryRestoreRef.current = tryRestore;

	useEffect(() => {
		if (!client) return;
		const myUserId = client.getUserId();
		function onVerificationRequest(request: VerificationRequest) {
			if (request.otherUserId !== myUserId) return;
			function onChange() {
				if (request.phase === VerificationPhase.Done) {
					request.off(VerificationRequestEvent.Change, onChange);
					void tryRestoreRef.current();
				} else if (request.phase === VerificationPhase.Cancelled) {
					request.off(VerificationRequestEvent.Change, onChange);
				}
			}
			request.on(VerificationRequestEvent.Change, onChange);
		}
		client.on(CryptoEvent.VerificationRequestReceived, onVerificationRequest);
		return () => {
			client.off(CryptoEvent.VerificationRequestReceived, onVerificationRequest);
		};
	}, [client]);

	useEffect(() => {
		if (!kb.info || !kb.trust?.trusted) return;
		void tryRestore();
	}, [kb.info, kb.trust, tryRestore]);

	return null;
}
