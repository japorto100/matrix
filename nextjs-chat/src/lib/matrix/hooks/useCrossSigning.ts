"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { CryptoEvent } from "matrix-js-sdk/lib/crypto-api/CryptoEvent";
import {
	type ShowQrCodeCallbacks,
	type ShowSasCallbacks,
	VerificationPhase,
	type VerificationRequest,
	VerificationRequestEvent,
	type Verifier,
	VerifierEvent,
} from "matrix-js-sdk/lib/crypto-api/verification";
import { useCallback, useEffect, useRef, useState } from "react";

export type CrossSigningState =
	| "checking"
	| "ready"
	| "needs_verification"
	| "verifying_wait" // Anfrage gesendet, warte auf Element X
	| "verifying_qr" // QR anzeigen, warte auf Scan
	| "verifying_sas" // SAS-Emojis vergleichen
	| "verifying_confirm" // Element X hat gescannt, Bestätigung nötig
	| "done";

export interface SasData {
	emoji: [string, string][] | undefined;
	confirm: () => void;
	cancel: () => void;
}

export interface QrConfirmData {
	confirm: () => void;
	cancel: () => void;
}

export interface UseCrossSigningReturn {
	state: CrossSigningState;
	qrPng: string | null; // base64 PNG data URL
	sasData: SasData | null;
	qrConfirmData: QrConfirmData | null;
	startVerification: () => Promise<void>;
	cancelVerification: () => void;
}

export function useCrossSigning(client: MatrixClient | null): UseCrossSigningReturn {
	const [state, setState] = useState<CrossSigningState>("checking");
	const [qrPng, setQrPng] = useState<string | null>(null);
	const [sasData, setSasData] = useState<SasData | null>(null);
	const [qrConfirmData, setQrConfirmData] = useState<QrConfirmData | null>(null);
	const requestRef = useRef<VerificationRequest | null>(null);

	// Status beim Start prüfen
	useEffect(() => {
		if (!client) return;
		async function checkStatus() {
			const crypto = client!.getCrypto();
			if (!crypto) {
				setState("ready");
				return;
			}
			const ready = await crypto.isCrossSigningReady();
			setState(ready ? "done" : "needs_verification");
		}
		checkStatus().catch(() => setState("needs_verification"));
	}, [client]);

	// Eingehende Verifikationsanfragen von Element X abfangen
	useEffect(() => {
		if (!client) return;
		function onRequest(request: VerificationRequest) {
			if (request.otherUserId !== client!.getUserId()) return;
			requestRef.current = request;
			setState("verifying_wait");
			processRequest(request);
		}
		client.on(CryptoEvent.VerificationRequestReceived, onRequest);
		return () => {
			client.off(CryptoEvent.VerificationRequestReceived, onRequest);
		};
	}, [client]); // eslint-disable-line react-hooks/exhaustive-deps

	const processRequest = useCallback(async (request: VerificationRequest) => {
		// Auf Ready-Phase warten
		await waitForPhase(request, VerificationPhase.Ready);

		// QR-Code generieren (request.generateQRCode gibt Uint8ClampedArray zurück)
		const qrBytes = await request.generateQRCode();

		if (qrBytes && qrBytes.length > 0) {
			// Bytes als QR-PNG rendern (binary segment — nicht als Text)
			const qrcode = await import("qrcode");
			const png = await qrcode.toDataURL([{ data: Buffer.from(qrBytes), mode: "byte" }], {
				errorCorrectionLevel: "L",
				width: 240,
			});
			setQrPng(png);
			setState("verifying_qr");

			// Auf Scan durch Element X warten — Verifier wird im request gesetzt
			await waitForPhase(request, VerificationPhase.Started);
			const verifier = request.verifier;
			if (verifier) {
				verifier.on(VerifierEvent.ShowReciprocateQr, (callbacks: ShowQrCodeCallbacks) => {
					setQrConfirmData({
						confirm: () => {
							callbacks.confirm();
							setState("done");
							cleanup();
						},
						cancel: () => {
							callbacks.cancel();
							cancelVerification();
						},
					});
					setState("verifying_confirm");
				});
				try {
					await verifier.verify();
					setState("done");
					cleanup();
				} catch {
					setState("needs_verification");
					cleanup();
				}
			}
		} else {
			// Kein QR → SAS Emoji-Fallback
			await waitForPhase(request, VerificationPhase.Started);
			const verifier = request.verifier;
			if (verifier) {
				verifier.on(VerifierEvent.ShowSas, (callbacks: ShowSasCallbacks) => {
					setSasData({
						emoji: callbacks.sas.emoji as [string, string][] | undefined,
						confirm: () => {
							callbacks.confirm();
							setState("done");
							cleanup();
						},
						cancel: () => {
							callbacks.mismatch();
							cancelVerification();
						},
					});
					setState("verifying_sas");
				});
				try {
					await verifier.verify();
					setState("done");
					cleanup();
				} catch {
					setState("needs_verification");
					cleanup();
				}
			}
		}
	}, []); // eslint-disable-line react-hooks/exhaustive-deps

	const startVerification = useCallback(async () => {
		if (!client) return;
		const crypto = client.getCrypto();
		if (!crypto) return;
		setState("verifying_wait");
		try {
			const request = await crypto.requestOwnUserVerification();
			requestRef.current = request;
			await processRequest(request);
		} catch {
			setState("needs_verification");
			cleanup();
		}
	}, [client, processRequest]);

	const cancelVerification = useCallback(() => {
		requestRef.current?.cancel();
		requestRef.current = null;
		setQrPng(null);
		setSasData(null);
		setQrConfirmData(null);
		setState("needs_verification");
	}, []);

	function cleanup() {
		requestRef.current = null;
		setQrPng(null);
		setSasData(null);
		setQrConfirmData(null);
	}

	return { state, qrPng, sasData, qrConfirmData, startVerification, cancelVerification };
}

function waitForPhase(request: VerificationRequest, phase: VerificationPhase): Promise<void> {
	const terminalPhases = [VerificationPhase.Cancelled, VerificationPhase.Done];
	return new Promise((resolve, reject) => {
		if (request.phase === phase) {
			resolve();
			return;
		}
		if (terminalPhases.includes(request.phase)) {
			reject(new Error("verification ended"));
			return;
		}
		function onChange() {
			if (request.phase === phase) {
				request.off(VerificationRequestEvent.Change, onChange);
				resolve();
			} else if (terminalPhases.includes(request.phase)) {
				request.off(VerificationRequestEvent.Change, onChange);
				reject(new Error("verification cancelled or done"));
			}
		}
		request.on(VerificationRequestEvent.Change, onChange);
	});
}
