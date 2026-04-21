"use client";

import { useAccountData } from "@matrix/lib/hooks/useAccountData";
import { useAlive } from "@matrix/lib/hooks/useAlive";
import { rememberSecretStorageKey } from "@matrix/lib/secretStorageKeys";
import { AlertCircle, CheckCircle2, Copy, Download, KeyRound } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import type { GeneratedSecretStorageKey } from "matrix-js-sdk/lib/crypto-api";
import { useCallback, useState } from "react";
import { toast } from "sonner";
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
	/** Callback nach erfolgreichem Setup (z.B. zum Refresh anderer Hooks). */
	onSuccess?: () => void;
}

type Stage = "passphrase" | "processing" | "show-key";

interface SecretStorageDefaultKeyContent {
	key?: string;
}

/**
 * Setup-UI fuer Server-Side Secret Storage (4S / m.secret_storage.v1.aes-hmac-sha2).
 *
 * 4S ist die Voraussetzung fuer alles was Cross-Signing-Recovery und
 * Key-Backup betrifft — erst mit 4S kann der User Cross-Signing-Keys, den
 * Backup-Decryption-Key und andere Secrets verschluesselt auf dem Homeserver
 * ablegen, damit andere Devices (oder dieses nach Reset) sie zurueckholen.
 *
 * Flow:
 *  1. User gibt Recovery-Passphrase ein (+ Confirm).
 *  2. `crypto.createRecoveryKeyFromPassphrase(passphrase)` erzeugt einen
 *     Secret-Storage-Key (privateKey + encodedPrivateKey als 48-Zeichen-String).
 *  3. `crypto.bootstrapSecretStorage({ setupNewSecretStorage: true,
 *     createSecretStorageKey })` schreibt den Key verschluesselt ins
 *     account_data (`m.secret_storage.default_key` + zugehoerige
 *     `m.secret_storage.key.<keyId>`). Cross-Signing-Private-Keys und
 *     (falls vorhanden) Backup-Keys werden zusaetzlich mit diesem Key
 *     verschluesselt ins account_data geschrieben.
 *  4. Ergebnis: der `encodedPrivateKey` wird dem User **einmal** gezeigt —
 *     er sollte ihn sicher speichern (Passphrase + Key sind gleichwertige
 *     Recovery-Pfade; wer die Passphrase vergisst, braucht den Key).
 *
 * SICHERHEIT: der 48-Zeichen-Key wird nur clientseitig angezeigt und sofort
 * aus dem State geloescht wenn der Dialog geschlossen wird. Er wird **nicht**
 * geloggt, **nicht** in LocalStorage gespeichert.
 */
export function SecretStorage({ client, open, onClose, onSuccess }: Props) {
	const alive = useAlive();
	const [stage, setStage] = useState<Stage>("passphrase");
	const [passphrase, setPassphrase] = useState("");
	const [confirmPassphrase, setConfirmPassphrase] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [generatedKey, setGeneratedKey] = useState<string | null>(null);

	// Check: 4S bereits eingerichtet? Warnung falls ja (reset wuerde alte Keys entwerten).
	const existingDefault = useAccountData<SecretStorageDefaultKeyContent>(
		client,
		"m.secret_storage.default_key",
	);
	const alreadySetup = !!existingDefault?.key;

	const reset = useCallback(() => {
		setStage("passphrase");
		setPassphrase("");
		setConfirmPassphrase("");
		setError(null);
		setGeneratedKey(null);
	}, []);

	const handleClose = useCallback(() => {
		reset();
		onClose();
	}, [reset, onClose]);

	const handleSubmit = useCallback(async () => {
		setError(null);

		if (!passphrase.trim()) {
			setError("Bitte eine Passphrase eingeben.");
			return;
		}
		if (passphrase.length < 8) {
			setError("Passphrase zu kurz (mindestens 8 Zeichen).");
			return;
		}
		if (passphrase !== confirmPassphrase) {
			setError("Passphrases stimmen nicht überein.");
			return;
		}

		setStage("processing");
		try {
			const crypto = client.getCrypto();
			if (!crypto) throw new Error("Crypto-API nicht initialisiert — WASM-Probleme?");

			// 1) Recovery-Key aus Passphrase ableiten.
			const generated: GeneratedSecretStorageKey =
				await crypto.createRecoveryKeyFromPassphrase(passphrase);

			// 2) Key im Session-Cache vormerken, damit cryptoCallbacks.getSecretStorageKey
			//    ihn waehrend bootstrapSecretStorage sofort liefern kann.
			//    keyId wissen wir erst NACH bootstrap, aber cacheSecretStorageKey im callback
			//    wird aufgerufen — wir uebergeben den Key ueber die createSecretStorageKey-
			//    Factory-Funktion direkt.

			// 3) bootstrapSecretStorage schreibt den neuen 4S-Setup ins account_data.
			//    setupNewSecretStorage=true erzwingt eine Neuanlage.
			//    setupNewKeyBackup=true erzeugt gleich ein Key-Backup.
			await crypto.bootstrapSecretStorage({
				setupNewSecretStorage: true,
				setupNewKeyBackup: true,
				createSecretStorageKey: async () => generated,
			});

			// 4) Key fuer die aktuelle Session merken (cryptoCallbacks findet ihn dann).
			// Die Default-KeyId wird von bootstrapSecretStorage in account_data geschrieben —
			// wir koennen sie nach bootstrap lesen.
			const defaultEvent = client.getAccountData(
				"m.secret_storage.default_key" as unknown as never,
			);
			const newKeyId = (defaultEvent?.getContent() as SecretStorageDefaultKeyContent | undefined)
				?.key;
			if (newKeyId) {
				rememberSecretStorageKey(newKeyId, generated.privateKey);
			}

			if (alive()) {
				setGeneratedKey(generated.encodedPrivateKey ?? null);
				setStage("show-key");
				onSuccess?.();
			}
		} catch (err) {
			if (alive()) {
				setError(err instanceof Error ? err.message : String(err));
				setStage("passphrase");
			}
		}
	}, [client, passphrase, confirmPassphrase, alive, onSuccess]);

	const handleCopyKey = useCallback(() => {
		if (!generatedKey) return;
		navigator.clipboard
			.writeText(generatedKey)
			.then(() => toast.success("Recovery-Key in die Zwischenablage kopiert."))
			.catch(() => toast.error("Kopieren fehlgeschlagen."));
	}, [generatedKey]);

	const handleDownloadKey = useCallback(() => {
		if (!generatedKey) return;
		const blob = new Blob(
			[
				`Matrix Recovery Key\n\n${generatedKey}\n\nBewahre diesen Key sicher auf. Mit dem Key kannst du auf einem neuen Geraet deine Verschluesselungs-Schluessel wiederherstellen.\n`,
			],
			{ type: "text/plain" },
		);
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `matrix-recovery-key-${new Date().toISOString().slice(0, 10)}.txt`;
		a.click();
		URL.revokeObjectURL(url);
	}, [generatedKey]);

	return (
		<Dialog open={open} onOpenChange={(o) => !o && stage !== "processing" && handleClose()}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<KeyRound className="h-5 w-5 text-primary" />
						Recovery-Passphrase einrichten
					</DialogTitle>
					<DialogDescription>
						Mit einer Recovery-Passphrase kannst du deine Verschluesselungs-Schluessel auf neuen
						Geraeten wiederherstellen — auch ohne zweites aktives Geraet.
					</DialogDescription>
				</DialogHeader>

				{stage === "passphrase" && (
					<div className="space-y-3">
						{alreadySetup && (
							<div className="flex items-start gap-2 rounded-md bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
								<AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
								<div>
									<p className="font-medium">Bereits eingerichtet</p>
									<p className="text-xs">
										Es existiert bereits eine Recovery-Passphrase auf dem Server. Fortfahren erzeugt
										eine neue und macht die alte ungueltig — alte verschluesselte Nachrichten
										koennten unlesbar werden, wenn du den alten Key nirgends mehr hast.
									</p>
								</div>
							</div>
						)}

						<div className="space-y-1">
							<Label htmlFor="secretStoragePassphrase" className="text-xs">
								Recovery-Passphrase (min. 8 Zeichen)
							</Label>
							<Input
								id="secretStoragePassphrase"
								type="password"
								value={passphrase}
								onChange={(e) => setPassphrase(e.target.value)}
								autoFocus
							/>
						</div>

						<div className="space-y-1">
							<Label htmlFor="secretStorageConfirm" className="text-xs">
								Passphrase bestaetigen
							</Label>
							<Input
								id="secretStorageConfirm"
								type="password"
								value={confirmPassphrase}
								onChange={(e) => setConfirmPassphrase(e.target.value)}
							/>
						</div>

						{error && (
							<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
								{error}
							</div>
						)}
					</div>
				)}

				{stage === "processing" && (
					<div className="flex items-center justify-center gap-3 py-10 text-sm text-muted-foreground">
						<div className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
						<span>Recovery-Setup läuft — Keys werden verschluesselt abgelegt…</span>
					</div>
				)}

				{stage === "show-key" && generatedKey && (
					<div className="space-y-3">
						<div className="flex items-start gap-2 rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-400">
							<CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
							<div>
								<p className="font-medium">Recovery eingerichtet</p>
								<p className="text-xs">
									Dies ist dein 48-Zeichen Recovery-Key. Speichere ihn **an einem sicheren Ort**
									(Passwort-Manager oder Offline). Der Key wird nach Schliessen des Dialogs nicht
									mehr angezeigt.
								</p>
							</div>
						</div>

						<div className="rounded-md bg-muted p-3 font-mono text-sm break-all select-all">
							{generatedKey}
						</div>

						<div className="flex gap-2">
							<Button variant="outline" onClick={handleCopyKey} className="flex-1">
								<Copy className="mr-2 h-3.5 w-3.5" />
								Kopieren
							</Button>
							<Button variant="outline" onClick={handleDownloadKey} className="flex-1">
								<Download className="mr-2 h-3.5 w-3.5" />
								Als Datei speichern
							</Button>
						</div>
					</div>
				)}

				<DialogFooter>
					{stage === "passphrase" && (
						<>
							<Button variant="outline" onClick={handleClose}>
								Abbrechen
							</Button>
							<Button onClick={handleSubmit}>Einrichten</Button>
						</>
					)}
					{stage === "show-key" && <Button onClick={handleClose}>Fertig</Button>}
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
