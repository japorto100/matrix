"use client";

// EditApiKeyModal — exec-16: Set/test/save API keys for LLM providers

import { CheckCircle, Key, Loader2, XCircle } from "lucide-react";
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
import { useSetApiKey, useValidateApiKey } from "@/lib/queries/hooks";
import type { LlmProvider } from "../types";

interface EditApiKeyModalProps {
	provider: LlmProvider | null;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

export function EditApiKeyModal({ provider, open, onOpenChange }: EditApiKeyModalProps) {
	const [apiKey, setApiKey] = useState("");
	const [validationResult, setValidationResult] = useState<{
		valid: boolean;
		error?: string;
		models?: string[];
	} | null>(null);

	const validate = useValidateApiKey();
	const saveKey = useSetApiKey();

	const handleClose = useCallback(() => {
		setApiKey("");
		setValidationResult(null);
		onOpenChange(false);
	}, [onOpenChange]);

	const handleTest = useCallback(async () => {
		if (!provider || !apiKey.trim()) return;
		setValidationResult(null);
		try {
			const result = await validate.mutateAsync({
				providerId: provider.id,
				apiKey: apiKey.trim(),
			});
			setValidationResult(result);
		} catch {
			setValidationResult({ valid: false, error: "Request failed" });
		}
	}, [provider, apiKey, validate]);

	const handleSave = useCallback(async () => {
		if (!provider || !apiKey.trim()) return;
		try {
			await saveKey.mutateAsync({
				providerId: provider.id,
				apiKey: apiKey.trim(),
			});
			toast.success(`API Key for ${provider.display_name} saved`);
			handleClose();
		} catch {
			toast.error("Failed to save API key");
		}
	}, [provider, apiKey, saveKey, handleClose]);

	if (!provider) return null;

	return (
		<Dialog open={open} onOpenChange={handleClose}>
			<DialogContent className="sm:max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Key className="h-4 w-4" />
						{provider.display_name} — API Key
					</DialogTitle>
					<DialogDescription>
						{provider.api_key_set
							? `Current key: ${provider.api_key_preview ?? "set"}`
							: "No key configured"}
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-4 py-2">
					<div className="space-y-2">
						<label htmlFor="api-key-input" className="text-xs font-medium">
							API Key
						</label>
						<Input
							id="api-key-input"
							type="password"
							placeholder="sk-..."
							value={apiKey}
							onChange={(e) => {
								setApiKey(e.target.value);
								setValidationResult(null);
							}}
							className="font-mono text-sm"
						/>
					</div>

					{/* Validation result */}
					{validationResult && (
						<div
							className={`flex items-start gap-2 rounded-md border p-3 text-xs ${
								validationResult.valid
									? "border-emerald-500/30 bg-emerald-950/10 text-emerald-400"
									: "border-red-500/30 bg-red-950/10 text-red-400"
							}`}
						>
							{validationResult.valid ? (
								<CheckCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
							) : (
								<XCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
							)}
							<div className="space-y-1">
								<p className="font-medium">
									{validationResult.valid ? "Key is valid" : "Key is invalid"}
								</p>
								{validationResult.error && (
									<p className="text-[11px] opacity-80 line-clamp-2">{validationResult.error}</p>
								)}
								{validationResult.models && validationResult.models.length > 0 && (
									<p className="text-[11px] opacity-80">
										{validationResult.models.length} models available
									</p>
								)}
							</div>
						</div>
					)}
				</div>

				<DialogFooter className="gap-2 sm:gap-0">
					<Button
						variant="outline"
						size="sm"
						onClick={handleTest}
						disabled={!apiKey.trim() || validate.isPending}
						className="gap-1.5"
					>
						{validate.isPending ? (
							<Loader2 className="h-3 w-3 animate-spin" />
						) : (
							<CheckCircle className="h-3 w-3" />
						)}
						Test
					</Button>
					<Button
						size="sm"
						onClick={handleSave}
						disabled={!apiKey.trim() || saveKey.isPending}
						className="gap-1.5"
					>
						{saveKey.isPending ? (
							<Loader2 className="h-3 w-3 animate-spin" />
						) : (
							<Key className="h-3 w-3" />
						)}
						Save
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
