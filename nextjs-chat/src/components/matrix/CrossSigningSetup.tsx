"use client";

import { ShieldAlert, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import type { UseCrossSigningReturn } from "@/lib/matrix/hooks/useCrossSigning";

interface Props {
	cs: UseCrossSigningReturn;
}

/**
 * Banner + Modal für Cross-Signing Device-Verifikation.
 * QR-Code: Web App zeigt QR, Element X scannt ihn.
 * SAS Fallback: Emoji-Vergleich zwischen beiden Geräten.
 */
export function CrossSigningSetup({ cs }: Props) {
	const { state, qrPng, sasData, qrConfirmData, startVerification, cancelVerification } = cs;

	if (state === "done" || state === "checking" || state === "ready") return null;

	const isVerifying = state !== "needs_verification";

	return (
		<>
			{/* Banner */}
			{state === "needs_verification" && (
				<div className="flex items-center gap-3 px-4 py-2 bg-yellow-500/10 border-b border-yellow-500/30 text-sm">
					<ShieldAlert className="h-4 w-4 text-yellow-500 shrink-0" />
					<span className="flex-1 text-yellow-700 dark:text-yellow-400">
						Dieses Gerät ist nicht verifiziert — öffne Element X um E2EE freizuschalten.
					</span>
					<Button
						size="sm"
						variant="outline"
						className="h-7 text-xs border-yellow-500/40 hover:bg-yellow-500/10"
						onClick={startVerification}
					>
						<ShieldCheck className="h-3.5 w-3.5 mr-1" />
						Verifizieren
					</Button>
				</div>
			)}

			{/* Modal */}
			<Dialog
				open={isVerifying}
				onOpenChange={(isOpen: boolean) => !isOpen && cancelVerification()}
			>
				<DialogContent className="max-w-sm">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2">
							<ShieldCheck className="h-5 w-5 text-primary" />
							Gerät verifizieren
						</DialogTitle>
						<DialogDescription>
							{state === "verifying_wait" &&
								"Verifikationsanfrage gesendet — öffne Element X und bestätige dort…"}
							{state === "verifying_qr" &&
								"Scanne diesen QR-Code mit Element X (Einstellungen → Geräte → Sitzungen)."}
							{state === "verifying_confirm" &&
								"Element X hat den QR-Code gescannt — stimmt alles überein?"}
							{state === "verifying_sas" &&
								"Vergleiche diese Emojis mit Element X. Stimmen alle überein?"}
						</DialogDescription>
					</DialogHeader>

					{/* Warten */}
					{state === "verifying_wait" && (
						<div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
							<div className="flex flex-col items-center gap-3">
								<div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
								Warte auf Element X…
							</div>
						</div>
					)}

					{/* QR Code */}
					{state === "verifying_qr" && qrPng && (
						<div className="flex flex-col items-center gap-3 py-2">
							{/* biome-ignore lint/a11y/useAltText: QR-Code für Geräteverifikation */}
							<img
								src={qrPng}
								width={200}
								height={200}
								className="rounded-lg border bg-white p-2"
							/>
							<p className="text-xs text-muted-foreground text-center">
								Oder warte — SAS-Emojis erscheinen als Fallback.
							</p>
						</div>
					)}

					{/* QR bestätigen (Element X hat gescannt) */}
					{state === "verifying_confirm" && qrConfirmData && (
						<div className="flex gap-2 mt-2">
							<Button variant="outline" className="flex-1" onClick={qrConfirmData.cancel}>
								<X className="h-4 w-4 mr-1" />
								Abbrechen
							</Button>
							<Button className="flex-1" onClick={qrConfirmData.confirm}>
								<ShieldCheck className="h-4 w-4 mr-1" />
								Bestätigen
							</Button>
						</div>
					)}

					{/* SAS Emojis */}
					{state === "verifying_sas" && sasData?.emoji && (
						<div className="flex flex-col items-center gap-4 py-2">
							<div className="grid grid-cols-4 gap-3">
								{sasData.emoji.map(([emoji, name], i) => (
									// biome-ignore lint/suspicious/noArrayIndexKey: SAS emojis haben stabile Positionen
									<div key={i} className="flex flex-col items-center gap-1">
										<span className="text-2xl">{emoji}</span>
										<span className="text-[10px] text-muted-foreground capitalize">{name}</span>
									</div>
								))}
							</div>
							<div className="flex gap-2 w-full">
								<Button variant="outline" className="flex-1" onClick={sasData.cancel}>
									<X className="h-4 w-4 mr-1" />
									Stimmt nicht
								</Button>
								<Button className="flex-1" onClick={sasData.confirm}>
									<ShieldCheck className="h-4 w-4 mr-1" />
									Stimmt überein
								</Button>
							</div>
						</div>
					)}

					{/* Abbrechen (QR/Wait States) */}
					{(state === "verifying_wait" || state === "verifying_qr") && (
						<Button variant="ghost" size="sm" onClick={cancelVerification} className="mt-1">
							Abbrechen
						</Button>
					)}
				</DialogContent>
			</Dialog>
		</>
	);
}
