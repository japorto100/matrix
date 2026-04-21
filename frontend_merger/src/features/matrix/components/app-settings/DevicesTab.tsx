"use client";

import { useDevices } from "@matrix/lib/hooks/useDevices";
import { Laptop, LogOut, ShieldAlert, ShieldCheck, Smartphone } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { Button } from "@/components/ui/button";

interface Props {
	client: MatrixClient;
}

function relativeTime(ts?: number): string {
	if (!ts) return "nie";
	const diff = Date.now() - ts;
	const mins = Math.floor(diff / 60000);
	if (mins < 1) return "gerade";
	if (mins < 60) return `vor ${mins}m`;
	const hours = Math.floor(mins / 60);
	if (hours < 24) return `vor ${hours}h`;
	const days = Math.floor(hours / 24);
	if (days < 30) return `vor ${days}d`;
	return new Date(ts).toLocaleDateString("de-DE");
}

function deviceIcon(name: string | null) {
	const lower = (name ?? "").toLowerCase();
	if (lower.includes("mobile") || lower.includes("android") || lower.includes("iphone"))
		return Smartphone;
	return Laptop;
}

export function DevicesTab({ client }: Props) {
	const { devices, loading, error, logoutDevice } = useDevices(client);

	return (
		<div className="space-y-3">
			<div>
				<h3 className="text-sm font-semibold">Deine Geraete</h3>
				<p className="text-xs text-muted-foreground">
					Sitzungen auf verschiedenen Geraeten. Verifiziert = vertrauenswuerdig fuer E2EE.
				</p>
			</div>

			{loading && <div className="text-sm text-muted-foreground">Lade Geraete-Liste…</div>}

			{error && (
				<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
			)}

			<div className="flex flex-col gap-2">
				{devices.map((device) => {
					const Icon = deviceIcon(device.displayName);
					return (
						<div
							key={device.deviceId}
							className="flex items-start gap-3 rounded-md border border-border/40 p-3"
						>
							<Icon className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
							<div className="min-w-0 flex-1 space-y-0.5">
								<div className="flex items-center gap-2">
									<span className="text-sm font-medium truncate">
										{device.displayName ?? "Unbenannt"}
									</span>
									{device.isCurrent && (
										<span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
											Aktuell
										</span>
									)}
									{device.isVerified ? (
										<span
											className="text-[10px] text-emerald-600 dark:text-emerald-400 flex items-center gap-0.5"
											title="Cross-signed verifiziert"
										>
											<ShieldCheck className="h-3 w-3" /> verifiziert
										</span>
									) : (
										<span
											className="text-[10px] text-amber-600 dark:text-amber-400 flex items-center gap-0.5"
											title="Nicht verifiziert"
										>
											<ShieldAlert className="h-3 w-3" /> unverifiziert
										</span>
									)}
								</div>
								<div className="text-[10px] text-muted-foreground">
									<code>{device.deviceId}</code>
								</div>
								{device.lastSeenIp && (
									<div className="text-[10px] text-muted-foreground">
										Zuletzt gesehen: {relativeTime(device.lastSeenTs)} aus {device.lastSeenIp}
									</div>
								)}
							</div>
							{!device.isCurrent && (
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
									onClick={() => void logoutDevice(device.deviceId)}
									title="Abmelden"
								>
									<LogOut className="h-3.5 w-3.5" />
								</Button>
							)}
						</div>
					);
				})}
				{!loading && devices.length === 0 && (
					<p className="text-xs text-muted-foreground">Keine Geraete gefunden.</p>
				)}
			</div>

			<p className="text-[10px] text-muted-foreground">
				Verifikations-Flow ist im Cross-Signing-Banner auf der Chat-Hauptseite verfuegbar
				(Passphrase oder QR/SAS mit zweitem Geraet).
			</p>
		</div>
	);
}
