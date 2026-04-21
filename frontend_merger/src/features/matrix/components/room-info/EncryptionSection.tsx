"use client";

import { AlertCircle, Lock, ShieldAlert, ShieldCheck } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useState } from "react";
import { toast } from "sonner";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

interface Props {
	client: MatrixClient;
	roomId: string;
	isEncrypted: boolean;
	canEdit: boolean;
}

/**
 * G6 Encryption-Setup-Section.
 *
 * Zeigt den aktuellen E2EE-Status eines Raums. Wenn nicht verschluesselt und
 * User hat die Berechtigung (state_default+), kann E2EE aktiviert werden —
 * **IRREVERSIBEL**. Der Enable-Flow ist hinter Doppel-Confirm:
 *
 *  1. Erster Klick zeigt AlertDialog mit Warnung
 *  2. Zweiter Klick ("Verstanden, aktivieren") checkt ein Bestaetigungs-Feld
 *  3. Dann erst wird `m.room.encryption` State-Event gesendet
 */
export function EncryptionSection({ client, roomId, isEncrypted, canEdit }: Props) {
	const [confirmOpen, setConfirmOpen] = useState(false);
	const [doubleConfirmed, setDoubleConfirmed] = useState(false);
	const [enabling, setEnabling] = useState(false);

	const handleEnable = async () => {
		if (!doubleConfirmed) return;
		setEnabling(true);
		try {
			await (
				client.sendStateEvent as (r: string, t: string, c: unknown, s: string) => Promise<unknown>
			)(roomId, "m.room.encryption", { algorithm: "m.megolm.v1.aes-sha2" }, "");
			toast.success("Ende-zu-Ende Verschluesselung aktiviert.");
			setConfirmOpen(false);
			setDoubleConfirmed(false);
		} catch (err) {
			console.error("[encryption] enable failed:", err);
			toast.error("Verschluesselung konnte nicht aktiviert werden.");
		} finally {
			setEnabling(false);
		}
	};

	return (
		<div className="space-y-2">
			<label className="text-xs font-medium text-muted-foreground block">Verschluesselung</label>

			{isEncrypted ? (
				<div className="flex items-start gap-2 rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-400">
					<ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
					<div>
						<p className="font-medium">E2EE aktiv</p>
						<p className="text-[11px]">
							Nachrichten werden mit Megolm (<code>m.megolm.v1.aes-sha2</code>) verschluesselt. Nur
							verifizierte Geraete koennen sie entschluesseln.
						</p>
					</div>
				</div>
			) : (
				<>
					<div className="flex items-start gap-2 rounded-md bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
						<ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
						<div>
							<p className="font-medium">Keine E2EE</p>
							<p className="text-[11px]">
								Nachrichten werden unverschluesselt gespeichert. Server-Admins koennen mitlesen.
							</p>
						</div>
					</div>
					{canEdit && (
						<Button
							variant="outline"
							size="sm"
							className="w-full"
							onClick={() => setConfirmOpen(true)}
						>
							<Lock className="h-3.5 w-3.5 mr-2" />
							Verschluesselung aktivieren
						</Button>
					)}
				</>
			)}

			<AlertDialog
				open={confirmOpen}
				onOpenChange={(o) => {
					if (!o) {
						setConfirmOpen(false);
						setDoubleConfirmed(false);
					}
				}}
			>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle className="flex items-center gap-2">
							<AlertCircle className="h-5 w-5 text-amber-500" />
							Verschluesselung aktivieren — IRREVERSIBEL
						</AlertDialogTitle>
						<AlertDialogDescription>
							Das Aktivieren von Ende-zu-Ende-Verschluesselung in einem Raum ist nach Matrix-Spec
							<strong> nicht rueckgaengig zu machen</strong>. Nach Aktivierung:
						</AlertDialogDescription>
					</AlertDialogHeader>
					<div className="space-y-3 text-sm">
						<ul className="list-disc list-inside space-y-1 text-muted-foreground text-xs">
							<li>Alle Nachrichten werden mit Megolm verschluesselt</li>
							<li>Nur verifizierte Geraete koennen Nachrichten lesen</li>
							<li>Server-Admins koennen nicht mitlesen (aber Metadata sehen)</li>
							<li>Bots muessen E2EE-faehig sein oder koennen nichts mehr lesen</li>
							<li>Einmal aktiviert: kann nicht mehr deaktiviert werden</li>
						</ul>
						<label className="flex items-start gap-2 text-xs cursor-pointer">
							<input
								type="checkbox"
								checked={doubleConfirmed}
								onChange={(e) => setDoubleConfirmed(e.target.checked)}
								className="mt-0.5"
							/>
							<span>
								Ich verstehe: diese Aktion ist <strong>irreversibel</strong>. Nicht-E2EE-Bots
								verlieren Zugriff auf neue Nachrichten.
							</span>
						</label>
					</div>
					<AlertDialogFooter>
						<AlertDialogCancel disabled={enabling}>Abbrechen</AlertDialogCancel>
						<AlertDialogAction
							onClick={(e) => {
								e.preventDefault();
								void handleEnable();
							}}
							disabled={!doubleConfirmed || enabling}
							className="bg-amber-600 hover:bg-amber-700 text-white"
						>
							{enabling ? "Aktiviere…" : "Verstanden, aktivieren"}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
