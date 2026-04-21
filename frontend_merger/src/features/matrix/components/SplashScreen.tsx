"use client";

import { Loader2, MessageCircle } from "lucide-react";

interface Props {
	/** Hauptzeile unter dem Logo. Default: "Verbinde mit Matrix…". */
	message?: string;
	/** Kleingedruckter Detail-Hinweis unter message (optional). */
	detail?: string;
}

/**
 * Brand-Splash fuer den Matrix-Client-Lade-State.
 *
 * Ersetzt den frueheren inline-Loader in `MatrixChat` waehrend
 * `!isReady` — gibt visuelles Feedback mit Brand-Element statt
 * eines nackten Spinners.
 */
export function SplashScreen({ message = "Verbinde mit Matrix…", detail }: Props) {
	return (
		<div className="flex h-full items-center justify-center p-8">
			<div className="flex max-w-sm flex-col items-center gap-4 text-center">
				<div className="relative">
					<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
						<MessageCircle className="h-8 w-8 text-primary" />
					</div>
					<Loader2 className="absolute -bottom-1 -right-1 h-5 w-5 animate-spin text-primary" />
				</div>
				<div className="space-y-1">
					<p className="font-medium">{message}</p>
					{detail && <p className="text-xs text-muted-foreground">{detail}</p>}
				</div>
			</div>
		</div>
	);
}
