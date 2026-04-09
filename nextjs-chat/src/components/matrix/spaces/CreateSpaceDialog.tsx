"use client";

import { Camera } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { Visibility } from "matrix-js-sdk";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface Props {
	client: MatrixClient;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

export function CreateSpaceDialog({ client, open, onOpenChange }: Props) {
	const [name, setName] = useState("");
	const [visibility, setVisibility] = useState<Visibility>(Visibility.Private);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const [avatarFile, setAvatarFile] = useState<File | null>(null);
	const [isCreating, setIsCreating] = useState(false);
	const avatarInputRef = useRef<HTMLInputElement>(null);

	const initials = name.slice(0, 2).toUpperCase() || "?";

	const handleAvatarSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;
		e.target.value = "";
		setAvatarFile(file);
		setAvatarPreview(URL.createObjectURL(file));
	};

	const handleCreate = async () => {
		const trimmed = name.trim();
		if (!trimmed) return;
		setIsCreating(true);
		try {
			// Avatar hochladen falls vorhanden
			let avatarUrl: string | undefined;
			if (avatarFile) {
				const upload = await client.uploadContent(avatarFile);
				avatarUrl = upload.content_uri;
			}

			// Space erstellen (m.space Room-Typ)
			await client.createRoom({
				name: trimmed,
				visibility,
				creation_content: { type: "m.space" },
				initial_state: avatarUrl
					? [{ type: "m.room.avatar", state_key: "", content: { url: avatarUrl } }]
					: [],
				power_level_content_override: {
					events_default: 0,
					invite: 50,
					state_default: 50,
				},
			});

			toast.success(`Space "${trimmed}" erstellt.`);
			onOpenChange(false);
			setName("");
			setVisibility(Visibility.Private);
			setAvatarPreview(undefined);
			setAvatarFile(null);
		} catch (err) {
			console.error("[CreateSpaceDialog] failed:", err);
			toast.error("Space konnte nicht erstellt werden.");
		} finally {
			setIsCreating(false);
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="sm:max-w-[400px]" aria-describedby={undefined}>
				<DialogHeader>
					<DialogTitle>Neuer Space</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col items-center gap-4 py-2">
					{/* Avatar */}
					<div className="relative">
						<Avatar className="h-16 w-16">
							{avatarPreview && <AvatarImage src={avatarPreview} alt={name} />}
							<AvatarFallback className="text-lg font-semibold bg-muted">{initials}</AvatarFallback>
						</Avatar>
						<button
							type="button"
							className="absolute bottom-0 right-0 h-6 w-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
							onClick={() => avatarInputRef.current?.click()}
						>
							<Camera className="h-3 w-3" />
						</button>
						<input
							ref={avatarInputRef}
							type="file"
							accept="image/*"
							className="hidden"
							onChange={handleAvatarSelect}
						/>
					</div>

					{/* Name */}
					<div className="w-full space-y-1.5">
						<Label htmlFor="space-name">Name</Label>
						<Input
							id="space-name"
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="z.B. Trading, Research, Team Alpha"
							onKeyDown={(e) => {
								if (e.key === "Enter" && name.trim()) handleCreate();
							}}
							autoFocus
						/>
					</div>

					{/* Sichtbarkeit */}
					<div className="w-full space-y-1.5">
						<Label>Sichtbarkeit</Label>
						<Tabs
							value={visibility}
							onValueChange={(v) =>
								setVisibility(v === Visibility.Public ? Visibility.Public : Visibility.Private)
							}
							className="w-full"
						>
							<TabsList className="w-full">
								<TabsTrigger value={Visibility.Private} className="flex-1">
									Privat
								</TabsTrigger>
								<TabsTrigger value={Visibility.Public} className="flex-1">
									Öffentlich
								</TabsTrigger>
							</TabsList>
						</Tabs>
						<p className="text-[10px] text-muted-foreground">
							{visibility === Visibility.Private
								? "Nur eingeladene Mitglieder können diesen Space sehen."
								: "Jeder kann diesen Space finden und beitreten."}
						</p>
					</div>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => onOpenChange(false)}>
						Abbrechen
					</Button>
					<Button onClick={handleCreate} disabled={!name.trim() || isCreating}>
						{isCreating ? "Erstelle..." : "Space erstellen"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
