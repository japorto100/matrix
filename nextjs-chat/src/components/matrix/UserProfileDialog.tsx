"use client";

import { Camera, ShieldAlert, ShieldCheck } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useEffect, useRef, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { getAutoAcceptDMs, setAutoAcceptDMs } from "@/lib/matrix/hooks/useAutoAcceptInvites";
import { mxcToHttp } from "@/lib/matrix/utils";

interface Props {
	client: MatrixClient;
	trigger: React.ReactNode;
}

export function UserProfileDialog({ client, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [displayName, setDisplayName] = useState("");
	const [avatarMxc, setAvatarMxc] = useState<string | undefined>();
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [isSaving, setIsSaving] = useState(false);
	const [statusMsg, setStatusMsg] = useState("");
	const [isCrossSigningReady, setIsCrossSigningReady] = useState<boolean | null>(null);
	const [autoAccept, setAutoAccept] = useState(getAutoAcceptDMs());
	const fileInputRef = useRef<HTMLInputElement>(null);

	// Profil laden wenn Dialog öffnet
	useEffect(() => {
		if (!open) return;
		const userId = client.getUserId();
		if (!userId) return;
		const user = client.getUser(userId);
		setDisplayName(user?.displayName ?? "");
		setStatusMsg(user?.presenceStatusMsg ?? "");
		setAvatarMxc(user?.avatarUrl ?? undefined);
		setAvatarPreview(undefined);
		setSelectedFile(null);

		// Cross-Signing Status prüfen
		client
			.getCrypto()
			?.isCrossSigningReady()
			.then((ready) => setIsCrossSigningReady(ready))
			.catch(() => setIsCrossSigningReady(false));
	}, [open, client]);

	const avatarSrc =
		avatarPreview ??
		(avatarMxc?.startsWith("mxc://") ? mxcToHttp(avatarMxc) : undefined);

	const initials = displayName.slice(0, 2).toUpperCase() || "?";

	function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
		const file = e.target.files?.[0];
		if (!file) return;
		setSelectedFile(file);
		setAvatarPreview(URL.createObjectURL(file));
	}

	async function save() {
		setIsSaving(true);
		try {
			// Displayname speichern
			const userId = client.getUserId();
			const user = userId ? client.getUser(userId) : null;
			if (displayName.trim() && displayName !== user?.displayName) {
				await client.setDisplayName(displayName.trim());
			}

			// Avatar hochladen und setzen
			if (selectedFile) {
				const upload = await client.uploadContent(selectedFile);
				await client.setAvatarUrl(upload.content_uri);
			}

			// Status/Bio setzen
			const currentStatus = client.getUser(client.getUserId()!)?.presenceStatusMsg ?? "";
			if (statusMsg.trim() !== currentStatus) {
				await client.setPresence({ presence: "online", status_msg: statusMsg.trim() || undefined });
			}

			setOpen(false);
		} catch (err) {
			console.error("[UserProfileDialog] Profil speichern fehlgeschlagen:", err);
		} finally {
			setIsSaving(false);
		}
	}

	const userId = client.getUserId() ?? "";

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-sm">
				<DialogHeader>
					<DialogTitle>Profil bearbeiten</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col items-center gap-4">
					{/* Avatar mit Upload-Button */}
					<div className="relative">
						<Avatar className="h-20 w-20">
							{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
							<AvatarFallback className="text-lg font-semibold">{initials}</AvatarFallback>
						</Avatar>
						<button
							type="button"
							className="absolute bottom-0 right-0 h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
							title="Avatar ändern"
							onClick={() => fileInputRef.current?.click()}
						>
							<Camera className="h-3.5 w-3.5" />
						</button>
						<input
							ref={fileInputRef}
							type="file"
							accept="image/*"
							className="hidden"
							onChange={handleFileSelect}
						/>
					</div>

					{/* User-ID (nicht editierbar) */}
					<p className="text-xs text-muted-foreground">{userId}</p>

					{/* Cross-Signing Status */}
					{isCrossSigningReady !== null && (
						<div className="flex items-center gap-1.5 text-xs">
							{isCrossSigningReady ? (
								<>
									<ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
									<span className="text-emerald-500">Cross-Signing eingerichtet</span>
								</>
							) : (
								<>
									<ShieldAlert className="h-3.5 w-3.5 text-destructive" />
									<span className="text-destructive/80">Cross-Signing nicht eingerichtet</span>
								</>
							)}
						</div>
					)}

					{/* Anzeigename */}
					<div className="w-full">
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Anzeigename
						</label>
						<Input
							value={displayName}
							onChange={(e) => setDisplayName(e.target.value)}
							placeholder="Dein Anzeigename"
						/>
					</div>
					{/* Status/Bio */}
					<div className="w-full">
						<label className="text-xs font-medium text-muted-foreground mb-1 block">Status</label>
						<Input
							value={statusMsg}
							onChange={(e) => setStatusMsg(e.target.value)}
							placeholder="Was machst du gerade?"
						/>
					</div>

					{/* Auto-Accept DMs */}
					<label className="flex items-center justify-between w-full cursor-pointer">
						<span className="text-xs font-medium text-muted-foreground">
							DM-Einladungen automatisch annehmen
						</span>
						<Switch
							checked={autoAccept}
							onCheckedChange={(checked) => {
								setAutoAccept(checked);
								setAutoAcceptDMs(checked);
							}}
						/>
					</label>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={save} disabled={isSaving || !displayName.trim()}>
						{isSaving ? "Speichere…" : "Speichern"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
