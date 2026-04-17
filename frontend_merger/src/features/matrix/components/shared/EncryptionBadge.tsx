"use client";

import { Lock, LockOpen } from "lucide-react";
import { cn } from "@/lib/utils";

interface EncryptionBadgeProps {
	isEncrypted: boolean;
	/** Kompakte Variante (nur Icon, kein Text) */
	compact?: boolean;
	className?: string;
}

export function EncryptionBadge({ isEncrypted, compact, className }: EncryptionBadgeProps) {
	return (
		<div className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
			{isEncrypted ? (
				<>
					<Lock className="h-3.5 w-3.5 text-emerald-500" />
					{!compact && <span>Verschlüsselt</span>}
				</>
			) : (
				<>
					<LockOpen className="h-3.5 w-3.5 text-destructive/70" />
					{!compact && <span>Nicht verschlüsselt</span>}
				</>
			)}
		</div>
	);
}
