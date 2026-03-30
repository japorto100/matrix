"use client";

import { Camera, Pencil, Plus, Trash2, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SpaceChildRoom, SpaceInfo } from "@/lib/matrix/hooks/useSpaces";
import { mxcToHttp } from "@/lib/matrix/utils";

interface Props {
	client: MatrixClient;
	space: SpaceInfo;
	hierarchy?: SpaceChildRoom[];
	onFetchHierarchy: () => void;
	onClose: () => void;
}

export function SpaceSettings({ client, space, hierarchy, onFetchHierarchy, onClose }: Props) {
	const [spaceName, setSpaceName] = useState(space.name);
	const [editingName, setEditingName] = useState(false);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const [addRoomId, setAddRoomId] = useState("");
	const avatarInputRef = useRef<HTMLInputElement>(null);

	const room = client.getRoom(space.roomId);
	const mxcAvatar = room?.getMxcAvatarUrl();
	const avatarSrc = avatarPreview ?? (mxcAvatar ? mxcToHttp(mxcAvatar) : undefined);
	const initials = space.name.slice(0, 2).toUpperCase() || "?";

	// Hierarchie beim Öffnen laden
	useEffect(() => {
		if (!hierarchy) onFetchHierarchy();
	}, [hierarchy, onFetchHierarchy]);

	const saveName = useCallback(async () => {
		setEditingName(false);
		const trimmed = spaceName.trim();
		if (!trimmed || trimmed === space.name) return;
		try {
			await client.setRoomName(space.roomId, trimmed);
			toast.success("Space-Name gespeichert.");
		} catch {
			toast.error("Name konnte nicht gespeichert werden.");
		}
	}, [client, space.roomId, space.name, spaceName]);

	const handleAvatarUpload = useCallback(
		async (e: React.ChangeEvent<HTMLInputElement>) => {
			const file = e.target.files?.[0];
			if (!file) return;
			e.target.value = "";
			setAvatarPreview(URL.createObjectURL(file));
			try {
				const upload = await client.uploadContent(file);
				await (
					client.sendStateEvent as (r: string, t: string, c: unknown, s: string) => Promise<unknown>
				)(space.roomId, "m.room.avatar", { url: upload.content_uri }, "");
				toast.success("Space-Avatar gespeichert.");
			} catch {
				toast.error("Avatar konnte nicht gesetzt werden.");
				setAvatarPreview(undefined);
			}
		},
		[client, space.roomId],
	);

	const addRoomToSpace = useCallback(async () => {
		const trimmed = addRoomId.trim();
		if (!trimmed) return;
		try {
			await client.sendStateEvent(
				space.roomId,
				"m.space.child" as any,
				{ via: [client.getDomain() ?? "matrix.local"] },
				trimmed,
			);
			toast.success("Raum zum Space hinzugefügt.");
			setAddRoomId("");
			onFetchHierarchy();
		} catch {
			toast.error("Raum konnte nicht hinzugefügt werden.");
		}
	}, [client, space.roomId, addRoomId, onFetchHierarchy]);

	const removeRoomFromSpace = useCallback(
		async (roomId: string) => {
			try {
				// Leerer Content = Kind entfernt
				await client.sendStateEvent(space.roomId, "m.space.child" as any, {}, roomId);
				toast.success("Raum aus Space entfernt.");
				onFetchHierarchy();
			} catch {
				toast.error("Raum konnte nicht entfernt werden.");
			}
		},
		[client, space.roomId, onFetchHierarchy],
	);

	const joinRoom = useCallback(
		async (roomId: string) => {
			try {
				await client.joinRoom(roomId);
				toast.success("Beigetreten.");
				onFetchHierarchy();
			} catch {
				toast.error("Beitreten fehlgeschlagen.");
			}
		},
		[client, onFetchHierarchy],
	);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border bg-background overflow-hidden">
			<div className="flex items-center justify-between h-[57px] px-4 border-b border-border shrink-0">
				<span className="text-sm font-semibold">Space-Einstellungen</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<div className="flex-1 overflow-y-auto p-4 space-y-5">
				{/* Avatar + Name */}
				<div className="flex flex-col items-center text-center gap-2">
					<div className="relative">
						<Avatar className="h-[72px] w-[72px]">
							{avatarSrc && <AvatarImage src={avatarSrc} alt={space.name} />}
							<AvatarFallback className="text-lg font-semibold bg-muted">{initials}</AvatarFallback>
						</Avatar>
						<button
							type="button"
							className="absolute bottom-0 right-0 h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
							onClick={() => avatarInputRef.current?.click()}
						>
							<Camera className="h-3.5 w-3.5" />
						</button>
						<input
							ref={avatarInputRef}
							type="file"
							accept="image/*"
							className="hidden"
							onChange={handleAvatarUpload}
						/>
					</div>
					<div className="w-full">
						{editingName ? (
							<Input
								value={spaceName}
								onChange={(e) => setSpaceName(e.target.value)}
								onKeyDown={(e) => {
									if (e.key === "Enter") saveName();
									if (e.key === "Escape") setEditingName(false);
								}}
								onBlur={saveName}
								autoFocus
								className="text-center font-semibold text-base"
							/>
						) : (
							<div className="flex items-center justify-center gap-1">
								<p className="font-semibold text-base">{space.name}</p>
								<button
									type="button"
									onClick={() => setEditingName(true)}
									className="text-muted-foreground hover:text-foreground transition-colors"
								>
									<Pencil className="h-3 w-3" />
								</button>
							</div>
						)}
						<p className="text-xs text-muted-foreground mt-0.5">
							{space.childRoomIds.length} Räume
						</p>
					</div>
				</div>

				{/* Räume im Space */}
				<div>
					<label className="text-xs font-medium text-muted-foreground mb-2 block">
						Räume in diesem Space
					</label>
					<div className="flex flex-col gap-1">
						{(hierarchy ?? []).map((child) => (
							<div
								key={child.roomId}
								className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-muted/50 group/room"
							>
								<div className="flex-1 min-w-0">
									<p className="text-sm font-medium truncate">{child.name}</p>
									<p className="text-[10px] text-muted-foreground">
										{child.memberCount} Mitglieder{!child.isJoined && " · Nicht beigetreten"}
									</p>
								</div>
								{!child.isJoined ? (
									<Button
										size="sm"
										variant="outline"
										className="shrink-0 h-6 text-[10px]"
										onClick={() => joinRoom(child.roomId)}
									>
										Beitreten
									</Button>
								) : (
									<button
										type="button"
										className="shrink-0 opacity-0 group-hover/room:opacity-100 text-muted-foreground hover:text-destructive transition-all"
										onClick={() => removeRoomFromSpace(child.roomId)}
										title="Aus Space entfernen"
									>
										<Trash2 className="h-3.5 w-3.5" />
									</button>
								)}
							</div>
						))}
						{(!hierarchy || hierarchy.length === 0) && (
							<p className="text-xs text-muted-foreground py-2 text-center">
								Keine Räume in diesem Space
							</p>
						)}
					</div>
				</div>

				{/* Raum hinzufügen */}
				<div>
					<label className="text-xs font-medium text-muted-foreground mb-1 block">
						Raum hinzufügen
					</label>
					<div className="flex gap-2">
						<Input
							value={addRoomId}
							onChange={(e) => setAddRoomId(e.target.value)}
							placeholder="!roomId:matrix.local"
							className="flex-1 h-8 text-xs"
							onKeyDown={(e) => {
								if (e.key === "Enter") addRoomToSpace();
							}}
						/>
						<Button
							size="sm"
							variant="outline"
							className="shrink-0 h-8"
							onClick={addRoomToSpace}
							disabled={!addRoomId.trim()}
						>
							<Plus className="h-3.5 w-3.5" />
						</Button>
					</div>
				</div>
			</div>
		</div>
	);
}
