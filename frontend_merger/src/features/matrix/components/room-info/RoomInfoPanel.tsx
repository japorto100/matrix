"use client";

import { usePinnedMessages } from "@matrix/lib/hooks/usePinnedMessages";
import { useRoomMembers } from "@matrix/lib/hooks/useRoomMembers";
import { mxcToHttp } from "@matrix/lib/utils";
import { Camera, Check, Copy, Pencil, Pin, PinOff, Trash2, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { EventType } from "matrix-js-sdk";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EncryptionBadge } from "../shared/EncryptionBadge";
import { PermissionsPanel, RoleManagement } from "./AdminSettings";
import { EncryptionSection } from "./EncryptionSection";
import { MemberList } from "./MemberList";
import { RoomAdminExtensions } from "./RoomAdminExtensions";
import { RoomNotificationsTab } from "./RoomNotificationsTab";
import { SharedMedia } from "./SharedMedia";

interface Props {
	client: MatrixClient;
	roomId: string;
	onClose: () => void;
}

export function RoomInfoPanel({ client, roomId, onClose }: Props) {
	const [roomName, setRoomName] = useState("");
	const [roomTopic, setRoomTopic] = useState("");
	const [editingName, setEditingName] = useState(false);
	const [editingTopic, setEditingTopic] = useState(false);
	const [isLeaving, setIsLeaving] = useState(false);
	const [leaveConfirm, setLeaveConfirm] = useState(false);
	const [avatarPreview, setAvatarPreview] = useState<string | undefined>();
	const avatarInputRef = useRef<HTMLInputElement>(null);
	const { pinnedIds } = usePinnedMessages(client, roomId);
	const { members, refresh: refreshMembers } = useRoomMembers(client, roomId);

	const room = client.getRoom(roomId);
	const myUserId = client.getUserId() ?? "";
	const membership = room?.getMyMembership() ?? "leave";
	const isEncrypted = !!room?.currentState.getStateEvents("m.room.encryption", "");
	const powerLevelsContent = room?.currentState
		.getStateEvents("m.room.power_levels", "")
		?.getContent();
	const usersDefault = (powerLevelsContent?.users_default as number) ?? 0;
	const myPowerLevel =
		(powerLevelsContent?.users as Record<string, number> | undefined)?.[myUserId] ?? usersDefault;
	const stateDefault = (powerLevelsContent?.state_default as number) ?? 50;
	const canEditRoomInfo = myPowerLevel >= stateDefault;

	// biome-ignore lint/correctness/useExhaustiveDependencies: room ist abgeleiteter Wert
	useEffect(() => {
		if (!room) return;
		setRoomName(room.name || "");
		setRoomTopic(room.currentState.getStateEvents("m.room.topic", "")?.getContent()?.topic ?? "");
		setAvatarPreview(undefined);
	}, [client, roomId, myUserId]);

	const saveName = useCallback(async () => {
		setEditingName(false);
		try {
			await client.setRoomName(roomId, roomName.trim());
		} catch {
			toast.error("Raumname konnte nicht gespeichert werden.");
		}
	}, [client, roomId, roomName]);

	const saveTopic = useCallback(async () => {
		setEditingTopic(false);
		try {
			await client.setRoomTopic(roomId, roomTopic.trim());
		} catch {
			toast.error("Thema konnte nicht gespeichert werden.");
		}
	}, [client, roomId, roomTopic]);

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
				)(roomId, "m.room.avatar", { url: upload.content_uri }, "");
			} catch {
				toast.error("Avatar konnte nicht gesetzt werden.");
				setAvatarPreview(undefined);
			}
		},
		[client, roomId],
	);

	const kickMember = useCallback(
		async (userId: string) => {
			try {
				await client.kick(roomId, userId, "Entfernt durch Moderator");
				refreshMembers();
				toast.success("Benutzer entfernt.");
			} catch {
				toast.error("Benutzer konnte nicht entfernt werden.");
			}
		},
		[client, roomId, refreshMembers],
	);

	const banMember = useCallback(
		async (userId: string) => {
			try {
				await client.ban(roomId, userId, "Gesperrt durch Moderator");
				refreshMembers();
				toast.success("Benutzer gesperrt.");
			} catch {
				toast.error("Benutzer konnte nicht gesperrt werden.");
			}
		},
		[client, roomId, refreshMembers],
	);

	const leaveOrDelete = useCallback(async () => {
		setIsLeaving(true);
		try {
			if (myPowerLevel >= 100) {
				for (const m of members) {
					if (m.userId !== myUserId)
						await client.kick(roomId, m.userId, "Raum gelöscht").catch(() => {});
				}
			}
			await client.leave(roomId);
			await client.forget(roomId).catch(() => {});
			onClose();
		} catch {
			toast.error("Raum konnte nicht verlassen werden.");
		} finally {
			setIsLeaving(false);
		}
	}, [client, roomId, onClose, members, myUserId, myPowerLevel]);

	const displayName = room?.name ?? "";
	const initials = displayName.slice(0, 2).toUpperCase() || "?";
	const mxcAvatar = room?.getMxcAvatarUrl();
	const avatarSrc = avatarPreview ?? (mxcAvatar ? mxcToHttp(mxcAvatar) : undefined);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border bg-background overflow-hidden">
			<div className="flex items-center justify-between h-[57px] px-4 border-b border-border bg-background shrink-0">
				<span className="text-sm font-semibold">Raum Info</span>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<Tabs
				defaultValue="info"
				className="flex-1 flex flex-col overflow-hidden"
				onValueChange={() => {
					// Tab-Switch soll offene Edit-States resetten (UX-Fix vom Verify).
					setEditingName(false);
					setEditingTopic(false);
				}}
			>
				<TabsList className="shrink-0 w-full justify-start rounded-none h-9 border-b bg-background px-2">
					<TabsTrigger value="info" className="text-xs h-7">
						Info
					</TabsTrigger>
					<TabsTrigger value="members" className="text-xs h-7">
						Mitglieder
					</TabsTrigger>
					<TabsTrigger value="notifications" className="text-xs h-7">
						Benachrichtigungen
					</TabsTrigger>
					{myPowerLevel >= 100 && (
						<TabsTrigger value="admin" className="text-xs h-7">
							Admin
						</TabsTrigger>
					)}
					<TabsTrigger value="advanced" className="text-xs h-7">
						Erweitert
					</TabsTrigger>
				</TabsList>

				<TabsContent
					value="info"
					className="flex-1 overflow-y-auto p-4 space-y-5 mt-0 data-[state=inactive]:hidden"
				>
					{/* Header: Avatar + Name + Encryption */}
					<div className="flex flex-col items-center text-center gap-2">
						<div className="relative">
							<Avatar className="h-[72px] w-[72px]">
								{avatarSrc && <AvatarImage src={avatarSrc} alt={displayName} />}
								<AvatarFallback className="text-lg font-semibold bg-muted">
									{initials}
								</AvatarFallback>
							</Avatar>
							{canEditRoomInfo && (
								<button
									type="button"
									className="absolute bottom-0 right-0 h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors"
									title="Raum-Avatar ändern"
									onClick={() => avatarInputRef.current?.click()}
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
						<div className="w-full">
							{editingName ? (
								<Input
									value={roomName}
									onChange={(e) => setRoomName(e.target.value)}
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
									<p className="font-semibold text-base">{displayName}</p>
									{canEditRoomInfo && (
										<button
											type="button"
											onClick={() => setEditingName(true)}
											className="text-muted-foreground hover:text-foreground transition-colors"
										>
											<Pencil className="h-3 w-3" />
										</button>
									)}
								</div>
							)}
							<p className="text-xs text-muted-foreground mt-0.5">{members.length} Mitglieder</p>
						</div>
						<EncryptionBadge isEncrypted={isEncrypted} />
					</div>

					{/* Topic */}
					<div>
						<div className="flex items-center gap-1 mb-1">
							<label className="text-xs font-medium text-muted-foreground">Thema</label>
							{!editingTopic && canEditRoomInfo && (
								<button
									type="button"
									onClick={() => setEditingTopic(true)}
									className="text-muted-foreground hover:text-foreground transition-colors"
								>
									<Pencil className="h-2.5 w-2.5" />
								</button>
							)}
						</div>
						{editingTopic ? (
							<textarea
								value={roomTopic}
								onChange={(e) => setRoomTopic(e.target.value)}
								onKeyDown={(e) => {
									if (e.key === "Enter" && !e.shiftKey) {
										e.preventDefault();
										saveTopic();
									}
									if (e.key === "Escape") setEditingTopic(false);
								}}
								onBlur={saveTopic}
								rows={2}
								placeholder="Worum geht es in diesem Raum?"
								autoFocus
								className="w-full rounded-lg border border-primary bg-muted/30 px-3 py-1.5 text-sm resize-none placeholder:text-muted-foreground/60 focus:outline-none"
							/>
						) : (
							<p
								className={
									canEditRoomInfo
										? "text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
										: "text-sm text-muted-foreground"
								}
								onClick={canEditRoomInfo ? () => setEditingTopic(true) : undefined}
							>
								{roomTopic || (canEditRoomInfo ? "Thema hinzufügen…" : "Kein Thema")}
							</p>
						)}
					</div>

					{/* Pinned Messages */}
					{pinnedIds.length > 0 &&
						(() => {
							const timeline = room?.getLiveTimeline().getEvents() ?? [];
							const pinnedMessages = pinnedIds
								.map((id) => timeline.find((ev) => ev.getId() === id))
								.filter(Boolean)
								.slice(0, 5);
							const handleUnpin = (eventId: string) => {
								const newPinned = pinnedIds.filter((id) => id !== eventId);
								client
									.sendStateEvent(roomId, EventType.RoomPinnedEvents, { pinned: newPinned }, "")
									.then(() => toast.success("Nachricht entpinnt."))
									.catch(() => toast.error("Entpinnen fehlgeschlagen."));
							};
							return (
								<div>
									<label className="text-xs font-medium text-muted-foreground mb-2 block">
										<Pin className="h-3 w-3 inline mr-1" />
										Angepinnt ({pinnedIds.length})
									</label>
									<div className="flex flex-col gap-1">
										{pinnedMessages.map((ev) => (
											<div
												key={ev!.getId()}
												className="group flex items-center gap-1 text-xs text-muted-foreground bg-muted/30 rounded px-2 py-1.5"
											>
												<div className="truncate flex-1">
													<span className="font-medium">
														{ev!.getSender()?.split(":")[0]?.replace("@", "")}:
													</span>{" "}
													{(ev!.getContent()?.body as string)?.slice(0, 60) ?? "..."}
												</div>
												{canEditRoomInfo && (
													<button
														type="button"
														className="hidden group-hover:block shrink-0 text-muted-foreground hover:text-destructive"
														onClick={() => handleUnpin(ev!.getId()!)}
														title="Entpinnen"
													>
														<PinOff className="h-3 w-3" />
													</button>
												)}
											</div>
										))}
										{pinnedIds.length > pinnedMessages.length && (
											<p className="text-[10px] text-muted-foreground">
												+{pinnedIds.length - pinnedMessages.length} weitere (nicht in Timeline)
											</p>
										)}
									</div>
								</div>
							);
						})()}

					{/* Shared Media */}
					<SharedMedia room={room} />
				</TabsContent>

				{/* Members Tab */}
				<TabsContent
					value="members"
					className="flex-1 overflow-y-auto p-4 space-y-4 mt-0 data-[state=inactive]:hidden"
				>
					<MemberList
						members={members}
						myUserId={myUserId}
						myPowerLevel={myPowerLevel}
						onKick={kickMember}
						onBan={banMember}
					/>
				</TabsContent>

				{/* Notifications Tab (G4): 4-Mode-Selector via useRoomNotificationMode */}
				<TabsContent
					value="notifications"
					className="flex-1 overflow-y-auto p-4 space-y-4 mt-0 data-[state=inactive]:hidden"
				>
					<RoomNotificationsTab client={client} roomId={roomId} />
				</TabsContent>

				{/* Admin Tab: Roles + Permissions (nur fuer Admins sichtbar) */}
				{myPowerLevel >= 100 && (
					<TabsContent
						value="admin"
						className="flex-1 overflow-y-auto p-4 space-y-5 mt-0 data-[state=inactive]:hidden"
					>
						<RoleManagement members={members} myUserId={myUserId} client={client} roomId={roomId} />
						<PermissionsPanel
							powerLevelsContent={powerLevelsContent}
							client={client}
							roomId={roomId}
						/>
						<RoomAdminExtensions client={client} roomId={roomId} canEdit={canEditRoomInfo} />
						<EncryptionSection
							client={client}
							roomId={roomId}
							isEncrypted={isEncrypted}
							canEdit={canEditRoomInfo}
						/>
					</TabsContent>
				)}

				{/* Advanced Tab: Invite-Link + Room-ID */}
				<TabsContent
					value="advanced"
					className="flex-1 overflow-y-auto p-4 space-y-4 mt-0 data-[state=inactive]:hidden"
				>
					{(() => {
						const alias = room?.getCanonicalAlias();
						const link = alias ? `https://matrix.to/#/${alias}` : `https://matrix.to/#/${roomId}`;
						return (
							<div>
								<label className="text-xs font-medium text-muted-foreground mb-1 block">
									Einladungslink
								</label>
								<div className="flex items-center gap-2">
									<code className="flex-1 text-[10px] text-muted-foreground bg-muted/30 px-2 py-1 rounded truncate">
										{link}
									</code>
									<Button
										variant="ghost"
										size="icon"
										className="h-7 w-7 shrink-0"
										title="Kopieren"
										onClick={() => {
											navigator.clipboard.writeText(link);
											toast.success("Link kopiert");
										}}
									>
										<Copy className="h-3 w-3" />
									</Button>
								</div>
							</div>
						);
					})()}
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">Raum-ID</label>
						<div className="flex items-center gap-2">
							<code className="flex-1 text-[10px] text-muted-foreground bg-muted/30 px-2 py-1 rounded truncate">
								{roomId}
							</code>
							<Button
								variant="ghost"
								size="icon"
								className="h-7 w-7 shrink-0"
								title="Kopieren"
								onClick={() => {
									navigator.clipboard.writeText(roomId);
									toast.success("Raum-ID kopiert");
								}}
							>
								<Copy className="h-3 w-3" />
							</Button>
						</div>
					</div>
					<p className="text-xs text-muted-foreground">
						Weitere Einstellungen (Join-Rule, History-Visibility, Aliases) folgen in D8.
					</p>
				</TabsContent>
			</Tabs>

			{/* Footer */}
			<div className="p-3 border-t border-border shrink-0">
				{membership === "invite" ? (
					<div className="flex gap-2">
						<Button
							className="flex-1 gap-1"
							onClick={() => {
								client
									.joinRoom(roomId)
									.then(() => toast.success("Beigetreten"))
									.catch(() => toast.error("Fehlgeschlagen"));
							}}
						>
							<Check className="h-4 w-4" /> Annehmen
						</Button>
						<Button
							variant="outline"
							className="flex-1 gap-1 text-destructive"
							onClick={() => {
								client.leave(roomId).catch(() => {});
								onClose();
							}}
						>
							<X className="h-4 w-4" /> Ablehnen
						</Button>
					</div>
				) : leaveConfirm ? (
					<div className="flex items-center gap-2">
						<span className="text-xs text-muted-foreground flex-1">
							{myPowerLevel >= 100 ? "Raum wirklich löschen?" : "Raum wirklich verlassen?"}
						</span>
						<Button size="sm" variant="ghost" onClick={() => setLeaveConfirm(false)}>
							Abbrechen
						</Button>
						<Button size="sm" variant="destructive" onClick={leaveOrDelete} disabled={isLeaving}>
							{isLeaving ? "…" : "Bestätigen"}
						</Button>
					</div>
				) : (
					<Button
						variant="outline"
						className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive"
						onClick={() => setLeaveConfirm(true)}
					>
						<Trash2 className="h-4 w-4 mr-2" />
						{myPowerLevel >= 100 ? "Raum löschen" : "Raum verlassen"}
					</Button>
				)}
			</div>
		</div>
	);
}
