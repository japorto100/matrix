"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import { useKeyBackup } from "@matrix/lib/hooks/useKeyBackup";
import { AlertCircle, CheckCircle2, DatabaseBackup, Loader2, ShieldAlert } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
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
}

type Mode = "status" | "restore-passphrase";

/**
 * Key-Backup Status- und Restore-UI.
 *
 * Zeigt den aktuellen Backup-Status (eingerichtet? vertrauenswuerdig? aktiv?)
 * und bietet Actions:
 *  - "Restore via Passphrase": laedt alle Megolm-Session-Keys aus dem Server-
 *    Backup mit Progress-Bar.
 *  - "Backup aktivieren": wenn ein Backup existiert aber dieses Device noch
 *    nicht synchronisiert (activeVersion=null), startet den Sync.
 *
 * Feature-Flag `NEXT_PUBLIC_CINNY_TIER_C` (default=false): wenn `false`,
 * rendert die Komponente gar nichts — Rollback-Safety fuer Dev.
 */
export function BackupRestore({ client, open, onClose }: Props) {
	const alive = useAlive();
	const kb = useKeyBackup(client);
	const [mode, setMode] = useState<Mode>("status");
	const [passphrase, setPassphrase] = useState("");
	const [restoring, setRestoring] = useState(false);
	const [restoreError, setRestoreError] = useState<string | null>(null);

	// Rollback-Flag: wenn das Feature deaktiviert ist, rendern wir nichts.
	// Default=false — in Dev/CI sicher, User muss explizit opt-in.
	const flagEnabled = process.env.NEXT_PUBLIC_CINNY_TIER_C === "true";

	const handleClose = useCallback(() => {
		if (restoring) return;
		setMode("status");
		setPassphrase("");
		setRestoreError(null);
		onClose();
	}, [restoring, onClose]);

	const handleEnable = useCallback(async () => {
		try {
			await kb.enable();
			toast.success("Backup-Sync aktiviert.");
		} catch (err) {
			toast.error(err instanceof Error ? err.message : String(err));
		}
	}, [kb]);

	const handleRestorePassphrase = useCallback(async () => {
		setRestoreError(null);
		if (!passphrase.trim()) {
			setRestoreError("Bitte Recovery-Passphrase eingeben.");
			return;
		}
		setRestoring(true);
		try {
			const result = await kb.restoreWithPassphrase(passphrase.trim());
			toast.success(
				`Restore erfolgreich: ${result.total} Keys geladen (${result.imported} neu, ${
					result.total - result.imported
				} bereits vorhanden).`,
			);
			if (alive()) {
				setPassphrase("");
				setMode("status");
			}
		} catch (err) {
			if (alive()) {
				setRestoreError(err instanceof Error ? err.message : String(err));
			}
		} finally {
			if (alive()) setRestoring(false);
		}
	}, [kb, passphrase, alive]);

	if (!flagEnabled) return null;

	const progressPct =
		kb.restoreProgress && kb.restoreProgress.total > 0
			? Math.round((kb.restoreProgress.loaded / kb.restoreProgress.total) * 100)
			: 0;

	return (
		<Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<DatabaseBackup className="h-5 w-5 text-primary" />
						Key-Backup
					</DialogTitle>
					<DialogDescription>
						Dein Schluessel-Backup erlaubt dir, auf neuen Geraeten auf alte verschluesselte
						Nachrichten zuzugreifen.
					</DialogDescription>
				</DialogHeader>

				{/* Loading-State */}
				{kb.loading && (
					<div className="flex items-center justify-center gap-3 py-6 text-sm text-muted-foreground">
						<Loader2 className="h-4 w-4 animate-spin" />
						Status wird geladen…
					</div>
				)}

				{/* Error-State */}
				{kb.error && (
					<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
						<div className="flex items-start gap-2">
							<AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
							<span>{kb.error}</span>
						</div>
					</div>
				)}

				{/* Status-View */}
				{!kb.loading && mode === "status" && (
					<div className="space-y-3">
						<BackupStatusPanel
							hasBackup={!!kb.info}
							trusted={kb.trust?.trusted ?? false}
							activeVersion={kb.activeVersion}
							version={kb.info?.version ?? null}
						/>

						{kb.info && (
							<div className="flex flex-wrap gap-2">
								{!kb.activeVersion && (
									<Button onClick={handleEnable} size="sm" variant="outline">
										Backup-Sync aktivieren
									</Button>
								)}
								<Button onClick={() => setMode("restore-passphrase")} size="sm">
									Restore via Passphrase
								</Button>
							</div>
						)}

						{!kb.info && (
							<div className="flex items-start gap-2 rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
								<AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
								Kein Backup eingerichtet. Richte zuerst eine Recovery-Passphrase ein (Menü
								„Cross-Signing → Passphrase").
							</div>
						)}
					</div>
				)}

				{/* Restore-View */}
				{mode === "restore-passphrase" && (
					<div className="space-y-3">
						<div className="space-y-1">
							<Label htmlFor="backupPassphrase" className="text-xs">
								Recovery-Passphrase
							</Label>
							<Input
								id="backupPassphrase"
								type="password"
								value={passphrase}
								onChange={(e) => setPassphrase(e.target.value)}
								disabled={restoring}
								autoFocus
							/>
						</div>

						{restoreError && (
							<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
								{restoreError}
							</div>
						)}

						{restoring && kb.restoreProgress && (
							<div className="space-y-1">
								<div className="flex justify-between text-xs text-muted-foreground">
									<span>Lade Keys…</span>
									<span>
										{kb.restoreProgress.loaded} / {kb.restoreProgress.total} ({progressPct}%)
									</span>
								</div>
								<div className="h-1.5 w-full overflow-hidden rounded bg-muted">
									<div
										className="h-full bg-primary transition-all"
										style={{ width: `${progressPct}%` }}
									/>
								</div>
							</div>
						)}
					</div>
				)}

				<DialogFooter>
					{mode === "status" && (
						<Button variant="outline" onClick={handleClose} disabled={restoring}>
							Schliessen
						</Button>
					)}
					{mode === "restore-passphrase" && (
						<>
							<Button variant="outline" onClick={() => setMode("status")} disabled={restoring}>
								Zurück
							</Button>
							<Button onClick={handleRestorePassphrase} disabled={restoring}>
								{restoring ? "Restore läuft…" : "Restore starten"}
							</Button>
						</>
					)}
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

interface BackupStatusPanelProps {
	hasBackup: boolean;
	trusted: boolean;
	activeVersion: string | null;
	version: string | null;
}

function BackupStatusPanel({ hasBackup, trusted, activeVersion, version }: BackupStatusPanelProps) {
	if (!hasBackup) {
		return (
			<div className="flex items-start gap-2 rounded-md bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
				<ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
				<div>
					<p className="font-medium">Kein Backup auf dem Server</p>
					<p className="text-xs">Neue verschluesselte Nachrichten werden nicht gesichert.</p>
				</div>
			</div>
		);
	}
	if (!trusted) {
		return (
			<div className="flex items-start gap-2 rounded-md bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
				<ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
				<div>
					<p className="font-medium">Backup ist nicht vertrauenswuerdig</p>
					<p className="text-xs">
						Version {version} existiert, aber die Signatur ist nicht cross-signed. Verifiziere
						zuerst dein Device.
					</p>
				</div>
			</div>
		);
	}
	if (!activeVersion) {
		return (
			<div className="flex items-start gap-2 rounded-md bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
				<ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
				<div>
					<p className="font-medium">Backup nicht aktiv</p>
					<p className="text-xs">
						Version {version} existiert und ist vertrauenswuerdig, aber dieses Geraet synchronisiert
						aktuell nicht.
					</p>
				</div>
			</div>
		);
	}
	return (
		<div className="flex items-start gap-2 rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-400">
			<CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
			<div>
				<p className="font-medium">Backup aktiv</p>
				<p className="text-xs">
					Version {activeVersion} — dieses Geraet sichert neue Keys automatisch auf dem Server.
				</p>
			</div>
		</div>
	);
}
