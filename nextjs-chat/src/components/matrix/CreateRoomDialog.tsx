"use client";

import { Camera } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useRef, useState } from "react";
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

type RoomType = "private" | "public";

export function CreateRoomDialog({ client, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [name, setName] = useState("");
	const [topic, setTopic] = useState("");
	const [roomType, setRoomType] = useState<RoomType>("private");
	const [isSending, setIsSending] = useState(false);
	const [avatarFile, setAvatarFile] = useState<File | null>(null);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const avatarInputRef = useRef<HTMLInputElement>(null);

	async function submit() {
		const trimmedName = name.trim();
		if (!trimmedName) return;

		setIsSending(true);
		try {
			const isPrivate = roomType === "private";
			const opts: Record<string, unknown> = {
				name: trimmedName,
				preset: isPrivate ? "private_chat" : "public_chat",
				visibility: isPrivate ? "private" : "public",
			};
			if (topic.trim()) opts.topic = topic.trim();
			if (isPrivate) {
				opts.initial_state = [
					{
						type: "m.room.encryption",
						state_key: "",
						content: { algorithm: "m.megolm.v1.aes-sha2" },
					},
				];
			}
			const result = await client.createRoom(opts);
			// Avatar hochladen wenn gewählt
			if (avatarFile && result.room_id) {
				try {
					const upload = await client.uploadContent(avatarFile);
					await (
						client.sendStateEvent as (
							r: string,
							t: string,
							c: unknown,
							s: string,
						) => Promise<unknown>
					)(result.room_id, "m.room.avatar", { url: upload.content_uri }, "");
				} catch (err) {
					console.error("[CreateRoomDialog] avatar upload failed:", err);
				}
			}
			setName("");
			setTopic("");
			setRoomType("private");
			setAvatarFile(null);
			setAvatarPreview(undefined);
			setOpen(false);
		} catch (err) {
			console.error("[CreateRoomDialog] failed:", err);
		} finally {
			setIsSending(false);
		}
	}

	const canSubmit = name.trim().length > 0 && !isSending;

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle>Raum erstellen</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					{/* Avatar */}
					<div className="flex justify-center">
						<div className="relative">
							<Avatar className="h-16 w-16">
								{avatarPreview && <AvatarImage src={avatarPreview} alt="Raum-Avatar" />}
								<AvatarFallback className="text-lg font-semibold bg-muted">
									{name.trim() ? name.trim().slice(0, 2).toUpperCase() : "?"}
								</AvatarFallback>
							</Avatar>
							<button
								type="button"
								className="absolute bottom-0 right-0 h-6 w-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
								title="Avatar wählen"
								onClick={() => avatarInputRef.current?.click()}
							>
								<Camera className="h-3 w-3" />
							</button>
							<input
								ref={avatarInputRef}
								type="file"
								accept="image/*"
								className="hidden"
								onChange={(e) => {
									const file = e.target.files?.[0];
									if (!file) return;
									setAvatarFile(file);
									setAvatarPreview(URL.createObjectURL(file));
								}}
							/>
						</div>
					</div>

					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Name (erforderlich)
						</label>
						<input
							type="text"
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="Raumname"
							className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>

					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Thema (optional)
						</label>
						<textarea
							value={topic}
							onChange={(e) => setTopic(e.target.value)}
							placeholder="Worum geht es in diesem Raum?"
							rows={2}
							className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>

					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1.5 block">
							Raumtyp
						</label>
						<div className="flex gap-2">
							<button
								type="button"
								onClick={() => setRoomType("private")}
								className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
									roomType === "private"
										? "border-primary bg-primary/10 text-foreground"
										: "border-border bg-background text-muted-foreground hover:bg-muted/50"
								}`}
							>
								<span className="font-medium">Privat</span>
								<p className="text-[10px] mt-0.5 opacity-70">Nur auf Einladung, verschlüsselt</p>
							</button>
							<button
								type="button"
								onClick={() => setRoomType("public")}
								className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
									roomType === "public"
										? "border-primary bg-primary/10 text-foreground"
										: "border-border bg-background text-muted-foreground hover:bg-muted/50"
								}`}
							>
								<span className="font-medium">Offen</span>
								<p className="text-[10px] mt-0.5 opacity-70">Jeder kann beitreten</p>
							</button>
						</div>
						{roomType === "private" && (
							<p className="text-[10px] text-amber-500 mt-1.5">
								Verschlüsselung kann nicht rückgängig gemacht werden
							</p>
						)}
					</div>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={submit} disabled={!canSubmit}>
						{isSending ? "Erstelle…" : "Raum erstellen"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
