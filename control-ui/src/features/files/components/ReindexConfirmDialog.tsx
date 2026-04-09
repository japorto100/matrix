"use client";

// DW19 — approval-write confirm dialog for Reindex action.
// Two-step: user must type file name to confirm; 30s countdown after which confirm is disabled.
// Sends x-confirm-token header to POST /api/files/[id]/reindex.

import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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

const CONFIRM_TTL_S = 30;

interface ReindexConfirmDialogProps {
	open: boolean;
	fileId: string;
	fileName: string;
	onClose: () => void;
	onSuccess: () => void;
}

export function ReindexConfirmDialog({
	open,
	fileId,
	fileName,
	onClose,
	onSuccess,
}: ReindexConfirmDialogProps) {
	const [typed, setTyped] = useState("");
	const [secondsLeft, setSecondsLeft] = useState(CONFIRM_TTL_S);
	const [isPending, setIsPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

	// Reset state each time dialog opens
	useEffect(() => {
		if (open) {
			setTyped("");
			setSecondsLeft(CONFIRM_TTL_S);
			setError(null);

			intervalRef.current = setInterval(() => {
				setSecondsLeft((s) => {
					if (s <= 1) {
						if (intervalRef.current) clearInterval(intervalRef.current);
						return 0;
					}
					return s - 1;
				});
			}, 1000);
		}
		return () => {
			if (intervalRef.current) clearInterval(intervalRef.current);
		};
	}, [open]);

	const confirmed = typed.trim() === fileName && secondsLeft > 0;

	async function handleConfirm() {
		if (!confirmed) return;
		setIsPending(true);
		setError(null);

		const requestId = crypto.randomUUID();
		const confirmToken = crypto.randomUUID();

		try {
			const res = await fetch(`/api/files/${encodeURIComponent(fileId)}/reindex`, {
				method: "POST",
				headers: {
					"x-request-id": requestId,
					"x-confirm-token": confirmToken,
				},
				cache: "no-store",
			});

			if (!res.ok) {
				const body = (await res.json().catch(() => ({}))) as { code?: string };
				setError(body.code ?? "REINDEX_FAILED");
				return;
			}

			onSuccess();
			onClose();
		} catch {
			setError("GATEWAY_UNAVAILABLE");
		} finally {
			setIsPending(false);
		}
	}

	return (
		<Dialog open={open} onOpenChange={(v) => !v && onClose()}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<AlertTriangle className="h-4 w-4 text-amber-500" />
						Confirm Reindex
					</DialogTitle>
					<DialogDescription>
						This will re-process and re-chunk the file. Existing chunks and vector embeddings will
						be replaced. Type the file name to confirm.
					</DialogDescription>
				</DialogHeader>

				<div className="flex flex-col gap-3 py-2">
					<p className="text-xs font-mono text-muted-foreground bg-muted rounded px-2 py-1 break-all">
						{fileName}
					</p>
					<Input
						placeholder={`Type "${fileName}" to confirm`}
						value={typed}
						onChange={(e) => setTyped(e.target.value)}
						disabled={secondsLeft === 0 || isPending}
						autoComplete="off"
					/>
					{secondsLeft === 0 && (
						<p className="text-xs text-destructive font-mono">
							Confirmation window expired. Close and try again.
						</p>
					)}
					{secondsLeft > 0 && secondsLeft <= CONFIRM_TTL_S && (
						<p className="text-xs text-muted-foreground">
							Window expires in{" "}
							<span className={secondsLeft <= 10 ? "text-amber-500 font-semibold" : ""}>
								{secondsLeft}s
							</span>
						</p>
					)}
					{error && (
						<p className="text-xs text-destructive font-mono flex items-center gap-1">
							<AlertTriangle className="h-3 w-3" />
							{error}
						</p>
					)}
				</div>

				<DialogFooter>
					<Button variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
						Cancel
					</Button>
					<Button size="sm" disabled={!confirmed || isPending} onClick={() => void handleConfirm()}>
						{isPending ? (
							<Loader2 className="h-3.5 w-3.5 animate-spin" />
						) : (
							<RefreshCw className="h-3.5 w-3.5" />
						)}
						Reindex
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
