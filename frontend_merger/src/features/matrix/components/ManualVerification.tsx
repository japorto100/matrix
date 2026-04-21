"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import { rememberSecretStorageKey } from "@matrix/lib/secretStorageKeys";
import { ShieldCheck } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { decodeRecoveryKey, deriveRecoveryKeyFromPassphrase } from "matrix-js-sdk/lib/crypto-api";
import type { SecretStorageKeyDescriptionAesV1 } from "matrix-js-sdk/lib/secret-storage";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
	client: MatrixClient;
	open: boolean;
	onClose: () => void;
	onSuccess: () => void;
	/**
	 * Guard fuer Race-Avoidance: wenn `useCrossSigning` aktuell in einer
	 * QR-/SAS-Phase ist, soll der Manual-Flow geblockt werden — beide gleichzeitig
	 * koennen Cross-Signing-Keys kollidieren lassen.
	 */
	activeOtherFlow: boolean;
}

type Mode = "passphrase" | "key";

interface SecretStorageDefaultKeyContent {
	key?: string;
}

/**
 * Manual Cross-Signing Recovery per Passphrase oder Recovery-Key.
 *
 * Alternative zum QR/SAS-Flow (useCrossSigning): wenn der User keinen zweiten
 * Device zur Hand hat, aber die Recovery-Passphrase (oder den 48-Character
 * Recovery-Key) weiss, kann er damit die Cross-Signing-Keys aus dem
 * Server-Side Secret Storage (4S) laden.
 *
 * Voraussetzung: 4S ist auf dem Server eingerichtet
 * (`m.secret_storage.default_key` existiert in account_data). Falls nicht,
 * wirft der Flow mit Hinweis — User muss erst via anderem verifizierten
 * Device eine Recovery-Passphrase erzeugen (SecretStorage-Setup, Tier-C).
 *
 * Flow:
 *  1. `m.secret_storage.default_key` + `m.secret_storage.key.<keyId>` aus
 *     account_data lesen (key-beschreibung + passphrase-parameter).
 *  2. Input (Passphrase → PBKDF2 → Uint8Array, oder Recovery-Key → Base58-decode).
 *  3. `client.secretStorage.checkKey()` gegen die Description validieren.
 *  4. Bei Match: `rememberSecretStorageKey` + `bootstrapCrossSigning` +
 *     `bootstrapSecretStorage` + `loadSessionBackupPrivateKeyFromSecretStorage`.
 *  5. Device ist danach cross-signed verifiziert.
 */
export function ManualVerification({ client, open, onClose, onSuccess, activeOtherFlow }: Props) {
	const alive = useAlive();
	const [mode, setMode] = useState<Mode>("passphrase");
	const [input, setInput] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleSubmit = async () => {
		if (activeOtherFlow) {
			setError("Eine QR-/SAS-Verifikation läuft bereits. Bitte erst abbrechen.");
			return;
		}
		if (!input.trim()) {
			setError("Bitte Passphrase bzw. Recovery-Key eingeben.");
			return;
		}
		setLoading(true);
		setError(null);

		try {
			// 1) Default-Key-ID aus account_data holen.
			// Cast auf `never`: SDK-Typ ist `keyof AccountDataEvents`, Matrix-Spec erlaubt
			// aber fuer custom-Keys weitere Typen — hier ist der eventType well-known.
			const defaultKeyEvent = client.getAccountData(
				"m.secret_storage.default_key" as unknown as never,
			);
			const defaultKeyId = (
				defaultKeyEvent?.getContent() as SecretStorageDefaultKeyContent | undefined
			)?.key;
			if (!defaultKeyId) {
				throw new Error(
					"Kein Secret-Storage-Key eingerichtet. Erstelle zuerst eine Recovery-Passphrase auf einem anderen verifizierten Geraet.",
				);
			}

			// 2) Key-Beschreibung laden (algorithm + passphrase-params + mac/iv).
			const keyInfoEvent = client.getAccountData(
				`m.secret_storage.key.${defaultKeyId}` as unknown as never,
			);
			const keyInfo = keyInfoEvent?.getContent() as SecretStorageKeyDescriptionAesV1 | undefined;
			if (!keyInfo) {
				throw new Error("Secret-Storage-Key-Info fehlt im Account-Data.");
			}

			// 3) Recovery-Key ableiten.
			let recoveryKey: Uint8Array<ArrayBuffer>;
			if (mode === "passphrase") {
				if (!keyInfo.passphrase) {
					throw new Error(
						"Dieser Secret-Storage-Key hat keine Passphrase konfiguriert — bitte Recovery-Key direkt eingeben.",
					);
				}
				const { salt, iterations, bits } = keyInfo.passphrase as {
					salt: string;
					iterations: number;
					bits?: number;
				};
				recoveryKey = await deriveRecoveryKeyFromPassphrase(input.trim(), salt, iterations, bits);
			} else {
				recoveryKey = decodeRecoveryKey(input.trim().replace(/\s+/g, ""));
			}

			// 4) Gegen secret storage verifizieren.
			const matches = await client.secretStorage.checkKey(recoveryKey, keyInfo);
			if (!matches) {
				throw new Error(
					mode === "passphrase" ? "Falsche Passphrase." : "Ungueltiger Recovery-Key.",
				);
			}

			// 5) Key merken fuer cryptoCallbacks.getSecretStorageKey.
			rememberSecretStorageKey(defaultKeyId, recoveryKey);

			// 6) Cross-Signing, Secret Storage und Key-Backup aus 4S laden.
			const crypto = client.getCrypto();
			if (!crypto) {
				throw new Error("Crypto-API nicht initialisiert — WASM-Probleme?");
			}
			await crypto.bootstrapCrossSigning({});
			await crypto.bootstrapSecretStorage({});
			await crypto.loadSessionBackupPrivateKeyFromSecretStorage();

			if (alive()) {
				setInput("");
				onSuccess();
			}
		} catch (err) {
			if (alive()) {
				setError(err instanceof Error ? err.message : String(err));
			}
		} finally {
			if (alive()) {
				setLoading(false);
			}
		}
	};

	return (
		<Dialog
			open={open}
			onOpenChange={(o) => {
				if (!o && !loading) onClose();
			}}
		>
			<DialogContent className="max-w-sm">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<ShieldCheck className="h-5 w-5 text-primary" />
						Verifizieren via Recovery
					</DialogTitle>
					<DialogDescription>
						Gib deine Recovery-Passphrase oder deinen 48-Zeichen Recovery-Key ein — damit laedt
						dieses Geraet die Cross-Signing-Keys aus deinem Server-Account.
					</DialogDescription>
				</DialogHeader>

				{activeOtherFlow && (
					<div className="rounded-md bg-amber-500/10 p-3 text-sm text-amber-600">
						Eine QR-/SAS-Verifikation läuft bereits. Bitte erst abschliessen oder abbrechen.
					</div>
				)}

				<div className="space-y-3">
					<div className="flex gap-3 text-sm">
						<button
							type="button"
							onClick={() => setMode("passphrase")}
							className={
								mode === "passphrase" ? "font-semibold underline" : "text-muted-foreground"
							}
						>
							Passphrase
						</button>
						<button
							type="button"
							onClick={() => setMode("key")}
							className={mode === "key" ? "font-semibold underline" : "text-muted-foreground"}
						>
							Recovery-Key
						</button>
					</div>

					<div className="space-y-1">
						<Label htmlFor="manualVerificationInput" className="text-xs">
							{mode === "passphrase"
								? "Recovery-Passphrase"
								: "Recovery-Key (48 Zeichen, Spaces erlaubt)"}
						</Label>
						<Input
							id="manualVerificationInput"
							type={mode === "passphrase" ? "password" : "text"}
							value={input}
							onChange={(e) => setInput(e.target.value)}
							disabled={loading || activeOtherFlow}
							autoFocus
						/>
					</div>

					{error && (
						<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
					)}
				</div>

				<DialogFooter>
					<Button variant="outline" onClick={onClose} disabled={loading}>
						Abbrechen
					</Button>
					<Button onClick={handleSubmit} disabled={loading || activeOtherFlow}>
						{loading ? "Prüfe…" : "Verifizieren"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
