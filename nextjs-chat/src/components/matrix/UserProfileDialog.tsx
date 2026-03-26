"use client";

import { Camera } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useEffect, useRef, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

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
	const fileInputRef = useRef<HTMLInputElement>(null);

	// Profil laden wenn Dialog öffnet
	useEffect(() => {
		if (!open) return;
		const userId = client.getUserId();
		if (!userId) return;
		const user = client.getUser(userId);
		setDisplayName(user?.displayName ?? "");
		setAvatarMxc(user?.avatarUrl ?? undefined);
		setAvatarPreview(undefined);
		setSelectedFile(null);
	}, [open, client]);

	const avatarSrc =
		avatarPreview ??
		(avatarMxc?.startsWith("mxc://")
			? `/api/matrix/media?mxc=${encodeURIComponent(avatarMxc.slice(6))}`
			: undefined);

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

					{/* Anzeigename */}
					<div className="w-full">
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Anzeigename
						</label>
						<input
							type="text"
							value={displayName}
							onChange={(e) => setDisplayName(e.target.value)}
							placeholder="Dein Anzeigename"
							className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>
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
