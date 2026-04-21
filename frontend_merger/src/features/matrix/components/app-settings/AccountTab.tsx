"use client";

import { useCapabilities } from "@matrix/lib/hooks/useCapabilities";
import { mxcToHttp } from "@matrix/lib/utils";
import { Camera, Pencil } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
	client: MatrixClient;
}

export function AccountTab({ client }: Props) {
	const myUserId = client.getUserId() ?? "";
	const myUser = client.getUser(myUserId);
	const { data: capabilities } = useCapabilities(client);

	const [displayName, setDisplayName] = useState(myUser?.displayName ?? "");
	const [editingName, setEditingName] = useState(false);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const avatarInputRef = useRef<HTMLInputElement>(null);

	const canChangeDisplayName = capabilities?.["m.set_displayname"]?.enabled ?? true;
	const canChangeAvatar = capabilities?.["m.set_avatar_url"]?.enabled ?? true;

	const mxcAvatar = myUser?.avatarUrl;
	const avatarSrc = avatarPreview ?? (mxcAvatar ? mxcToHttp(mxcAvatar) : undefined);
	const initials = displayName.slice(0, 2).toUpperCase() || "?";

	const saveName = async () => {
		setEditingName(false);
		const trimmed = displayName.trim();
		if (!trimmed) return;
		try {
			await client.setDisplayName(trimmed);
			toast.success("Anzeigename gespeichert.");
		} catch {
			toast.error("Name konnte nicht gespeichert werden.");
		}
	};

	const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;
		e.target.value = "";
		setAvatarPreview(URL.createObjectURL(file));
		try {
			const upload = await client.uploadContent(file);
			await client.setAvatarUrl(upload.content_uri);
			toast.success("Avatar gespeichert.");
		} catch {
			toast.error("Avatar konnte nicht gesetzt werden.");
			setAvatarPreview(undefined);
		}
	};

	return (
		<div className="space-y-4">
			<div className="flex flex-col items-center gap-3">
				<div className="relative">
					<Avatar className="h-20 w-20">
						{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
						<AvatarFallback className="bg-muted text-lg">{initials}</AvatarFallback>
					</Avatar>
					{canChangeAvatar && (
						<button
							type="button"
							className="absolute bottom-0 right-0 h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90"
							onClick={() => avatarInputRef.current?.click()}
							title="Avatar aendern"
						>
							<Camera className="h-3.5 w-3.5" />
						</button>
					)}
					<input
						ref={avatarInputRef}
						type="file"
						accept="image/*"
						className="hidden"
						onChange={handleAvatarUpload}
					/>
				</div>

				<div className="text-center">
					{editingName ? (
						<Input
							value={displayName}
							onChange={(e) => setDisplayName(e.target.value)}
							onKeyDown={(e) => {
								if (e.key === "Enter") void saveName();
								if (e.key === "Escape") setEditingName(false);
							}}
							onBlur={saveName}
							autoFocus
							className="text-center font-semibold"
							disabled={!canChangeDisplayName}
						/>
					) : (
						<div className="flex items-center gap-1">
							<span className="text-base font-semibold">{displayName}</span>
							{canChangeDisplayName && (
								<button
									type="button"
									onClick={() => setEditingName(true)}
									className="text-muted-foreground hover:text-foreground"
								>
									<Pencil className="h-3 w-3" />
								</button>
							)}
						</div>
					)}
					<div className="text-[10px] text-muted-foreground font-mono mt-1">{myUserId}</div>
				</div>
			</div>

			<div className="border-t pt-4 space-y-2">
				<h3 className="text-sm font-semibold">Passwort aendern</h3>
				{capabilities?.["m.change_password"]?.enabled ? (
					<p className="text-xs text-muted-foreground">
						Passwort-Aenderung ist auf deinem Homeserver verfuegbar. Nutze das Matrix-Account-
						Management-UI deines Homeservers (typ. unter <code>/_matrix/client/account/manage</code>
						).
					</p>
				) : (
					<p className="text-xs text-muted-foreground">
						Passwort-Aenderung ist auf diesem Homeserver nicht verfuegbar.
					</p>
				)}
			</div>

			<div className="border-t pt-4 space-y-2">
				<h3 className="text-sm font-semibold text-destructive">Account deaktivieren</h3>
				<p className="text-xs text-muted-foreground">
					Nutze das Management-UI deines Homeservers. Die Deaktivierung ist
					<strong> unwiderruflich</strong>.
				</p>
				<Button variant="outline" size="sm" disabled>
					Management oeffnen (TODO: homeserver link)
				</Button>
			</div>
		</div>
	);
}
