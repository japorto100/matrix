"use client";

import { AlertCircle, BarChart2, Loader2, MessageCircle, Pin, WifiOff } from "lucide-react";
import { ClientEvent, NotificationCountType, SyncState } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useAutoAcceptInvites } from "@/lib/matrix/hooks/useAutoAcceptInvites";
import { useCrossSigning } from "@/lib/matrix/hooks/useCrossSigning";
import { useKeyboardShortcuts } from "@/lib/matrix/hooks/useKeyboardShortcuts";
import { useMatrixClient } from "@/lib/matrix/hooks/useMatrixClient";
import { useMatrixRTCCall } from "@/lib/matrix/hooks/useMatrixRTCCall";
import { useMessageActions } from "@/lib/matrix/hooks/useMessageActions";
import { useNotifications } from "@/lib/matrix/hooks/useNotifications";
import { usePinnedMessages } from "@/lib/matrix/hooks/usePinnedMessages";
import { useRooms } from "@/lib/matrix/hooks/useRooms";
import { useSpaces } from "@/lib/matrix/hooks/useSpaces";
import { useTimeline } from "@/lib/matrix/hooks/useTimeline";
import { useTyping } from "@/lib/matrix/hooks/useTyping";
import { ActivityCentre } from "./ActivityCentre";
import { CallOverlay } from "./CallOverlay";
import { CreatePollDialog } from "./CreatePollDialog";
import { CrossSigningSetup } from "./CrossSigningSetup";
import { DMInfoPanel } from "./DMInfoPanel";
import { ForwardDialog } from "./ForwardDialog";
import { type EditState, MessageComposer } from "./MessageComposer";
import { RoomHeader } from "./RoomHeader";
import { RoomInfoPanel } from "./room-info/RoomInfoPanel";
import { RoomList } from "./room-list/RoomList";
import { SearchPanel } from "./SearchPanel";
import { SpaceSelector } from "./spaces/SpaceSelector";
import { SpaceSettings } from "./spaces/SpaceSettings";
import { Timeline } from "./Timeline";
import { TypingIndicator } from "./TypingIndicator";
import { ThreadOverview } from "./threads/ThreadOverview";
import { ThreadPanel } from "./threads/ThreadPanel";

export function MatrixChat() {
	const { client, isReady, error } = useMatrixClient();
	const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
	const [editState, setEditState] = useState<EditState | null>(null);
	const [replyState, setReplyState] = useState<{
		eventId: string;
		sender: string;
		body: string;
	} | null>(null);
	const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
	const [showRoomSettings, setShowRoomSettings] = useState(false);
	const [showSearch, setShowSearch] = useState(false);
	const [showThreadOverview, setShowThreadOverview] = useState(false);
	const [showActivity, setShowActivity] = useState(false);
	const [spaceSettingsId, setSpaceSettingsId] = useState<string | null>(null);
	const [forwardState, setForwardState] = useState<{ body: string; senderName: string } | null>(
		null,
	);
	const [syncStatus, setSyncStatus] = useState<"syncing" | "reconnecting" | "error">("syncing");
	const callState = useMatrixRTCCall(isReady ? client : null);
	const crossSigning = useCrossSigning(isReady ? client : null);
	useAutoAcceptInvites(isReady ? client : null);

	// Sync-Status Listener
	useEffect(() => {
		if (!client) return;
		function onSync(state: SyncState) {
			if (state === SyncState.Syncing || state === SyncState.Prepared) setSyncStatus("syncing");
			else if (state === SyncState.Reconnecting) setSyncStatus("reconnecting");
			else if (state === SyncState.Error) setSyncStatus("error");
		}
		client.on(ClientEvent.Sync, onSync);
		return () => {
			client.off(ClientEvent.Sync, onSync);
		};
	}, [client]);

	const rooms = useRooms(isReady ? client : null);
	const { spaces, fetchHierarchy } = useSpaces(isReady ? client : null);
	const { items: activityItems } = useNotifications(isReady ? client : null);
	const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);
	const { messages, isLoading, canLoadMore, loadMore } = useTimeline(
		isReady ? client : null,
		selectedRoomId,
	);
	const typers = useTyping(isReady ? client : null, selectedRoomId);

	const selectedRoom = rooms.find((r) => r.roomId === selectedRoomId) ?? null;

	// B-8: Thread-Panel schließen bei Raumwechsel
	// biome-ignore lint/correctness/useExhaustiveDependencies: setState-Funktionen sind stabil (React-Garantie)
	useEffect(() => {
		setActiveThreadId(null);
		setReplyState(null);
		setShowRoomSettings(false);
		setShowSearch(false);
		setShowThreadOverview(false);
		setShowActivity(false);
	}, [selectedRoomId]);

	// Permalink-Navigation: matrix.to Links in Nachrichten → Raum öffnen
	useEffect(() => {
		function onNavigate(e: Event) {
			const detail = (e as CustomEvent).detail as
				| { type: "user" | "room" | "event"; id: string; eventId?: string }
				| undefined;
			if (!detail) return;
			if (detail.type === "room") {
				// Raum-ID (!xxx:server) oder Alias (#xxx:server) → Raum öffnen
				const room = rooms.find(
					(r) => r.roomId === detail.id || r.name === detail.id.replace(/^#/, "").split(":")[0],
				);
				if (room) setSelectedRoomId(room.roomId);
				else toast.error(`Raum ${detail.id} nicht gefunden`);
			} else if (detail.type === "user" && client) {
				// User-Profil → DM öffnen falls vorhanden
				const dm = rooms.find((r) => r.dmUserId === detail.id);
				if (dm) setSelectedRoomId(dm.roomId);
			}
		}
		window.addEventListener("matrix:navigate", onNavigate);
		return () => window.removeEventListener("matrix:navigate", onNavigate);
	}, [rooms, client]);

	// Keyboard Shortcuts
	useKeyboardShortcuts({
		onQuickSwitch: () => setShowSearch(true),
		onEscape: () => {
			if (activeThreadId) setActiveThreadId(null);
			else if (showSearch) setShowSearch(false);
			else if (showRoomSettings) setShowRoomSettings(false);
			else if (showThreadOverview) setShowThreadOverview(false);
			else if (showActivity) setShowActivity(false);
			else if (spaceSettingsId) setSpaceSettingsId(null);
		},
		onEditLastMessage: () => {
			const lastOwn = [...messages].reverse().find((m) => m.isOwn && m.msgType === "m.text");
			if (lastOwn) setEditState({ eventId: lastOwn.eventId, body: lastOwn.body });
		},
	});

	// Message Actions (React, Redact) via Hook
	const { handleReact, handleRedact } = useMessageActions(client, selectedRoomId);

	// UI-4: Reply starten
	const handleReply = useCallback((eventId: string, sender: string, body: string) => {
		setReplyState({ eventId, sender, body });
	}, []);

	// B-1: Edit-Modus starten
	const handleEdit = useCallback((eventId: string, body: string) => {
		setEditState({ eventId, body });
	}, []);

	// Pin/Unpin Messages (Hook)
	const {
		pinnedIds: pinnedEventIds,
		canPin,
		togglePin: handlePin,
	} = usePinnedMessages(client, selectedRoomId);

	// B-8: Thread öffnen
	const handleThreadOpen = useCallback((eventId: string) => {
		setActiveThreadId(eventId);
	}, []);

	// UI-13: Forward
	const handleForward = useCallback((body: string, senderName: string) => {
		setForwardState({ body, senderName });
	}, []);

	// QW-2: Read Receipt senden wenn Raum aktiv + Unread lokal zurücksetzen
	const lastMsg = messages.length > 0 ? messages[messages.length - 1] : undefined;
	const lastEventId = lastMsg?.eventId ?? null;
	useEffect(() => {
		if (!client || !selectedRoomId || !lastEventId) return;
		const room = client.getRoom(selectedRoomId);
		if (!room) return;
		const events = room.getLiveTimeline().getEvents();
		const lastEv = events[events.length - 1];
		if (lastEv) {
			client.sendReadReceipt(lastEv).catch(() => {});
			client.setRoomReadMarkers(selectedRoomId, lastEv.getId()!).catch(() => {});
		}
		// Sliding Sync aktualisiert den Count nicht sofort — lokal zurücksetzen + UI refresh
		for (const t of [NotificationCountType.Total, NotificationCountType.Highlight]) {
			room.setUnreadNotificationCount(t, 0);
		}
		// ClientEvent.Room triggert useRooms refresh
		setTimeout(() => {
			client.emit(ClientEvent.Room, room);
		}, 100);
	}, [client, selectedRoomId, lastEventId]);

	// Fehler-State
	if (error) {
		return (
			<div className="flex items-center justify-center h-full">
				<div className="flex flex-col items-center gap-3 text-center max-w-sm">
					<AlertCircle className="h-10 w-10 text-destructive" />
					<p className="font-medium">Matrix-Verbindung fehlgeschlagen</p>
					<p className="text-sm text-muted-foreground">{error}</p>
				</div>
			</div>
		);
	}

	// Lade-State
	if (!isReady) {
		return (
			<div className="flex items-center justify-center h-full">
				<div className="flex flex-col items-center gap-3">
					<Loader2 className="h-8 w-8 animate-spin text-primary" />
					<p className="text-sm text-muted-foreground">Verbinde mit Matrix…</p>
				</div>
			</div>
		);
	}

	return (
		<>
			{/* Cross-Signing Banner + Modal */}
			<CrossSigningSetup cs={crossSigning} />

			{/* Sync-Status Banner */}
			{syncStatus !== "syncing" && (
				<div className="flex items-center gap-2 px-4 py-1.5 text-xs bg-amber-500/10 text-amber-400 border-b border-amber-500/20">
					<WifiOff className="h-3.5 w-3.5" />
					{syncStatus === "reconnecting" ? "Verbindung wird hergestellt..." : "Verbindung verloren"}
				</div>
			)}

			<div className="flex h-full overflow-hidden" data-matrix-chat>
				{/* Space-Rail (vertikale Icon-Leiste links) */}
				{isReady && (
					<SpaceSelector
						spaces={spaces}
						selectedSpaceId={selectedSpaceId}
						onSelect={setSelectedSpaceId}
						onActivityOpen={() => {
							setShowActivity(true);
							setShowSearch(false);
							setShowRoomSettings(false);
							setShowThreadOverview(false);
							setActiveThreadId(null);
						}}
						onSpaceSettings={(spaceId) => {
							setSpaceSettingsId(spaceId);
							setShowActivity(false);
							setShowSearch(false);
							setShowRoomSettings(false);
							setShowThreadOverview(false);
							setActiveThreadId(null);
						}}
						activityCount={activityItems.length}
						client={client}
					/>
				)}

				{/* Sidebar — Raumliste */}
				<RoomList
					rooms={rooms}
					selectedRoomId={selectedRoomId}
					onSelect={setSelectedRoomId}
					isLoading={!isReady}
					client={client}
					spaces={spaces}
					selectedSpaceId={selectedSpaceId}
				/>

				{/* Hauptbereich + optionaler Thread-Panel */}
				<div className="flex-1 flex overflow-hidden">
					{/* Chat-Bereich */}
					<div className="flex-1 flex flex-col overflow-hidden">
						{selectedRoom && client ? (
							<>
								<RoomHeader
									room={selectedRoom}
									client={client}
									roomId={selectedRoomId!}
									onCall={(withVideo) =>
										callState.joinCall(selectedRoomId!, withVideo ? "m.video" : "m.voice")
									}
									onSettingsOpen={() => setShowRoomSettings(true)}
									onSearchOpen={() => {
										setShowSearch(true);
										setActiveThreadId(null);
										setShowRoomSettings(false);
										setShowThreadOverview(false);
									}}
									onThreadsOpen={() => {
										setShowThreadOverview(true);
										setActiveThreadId(null);
										setShowSearch(false);
										setShowRoomSettings(false);
									}}
								/>
								{selectedRoom.membership === "invite" ? (
									<div className="flex-1 flex items-center justify-center">
										<div className="text-center space-y-4 p-8">
											<div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
												<MessageCircle className="h-8 w-8 text-primary" />
											</div>
											<div>
												<p className="font-semibold text-lg">{selectedRoom.name}</p>
												<p className="text-sm text-muted-foreground mt-1">
													{selectedRoom.dmUserId ? "Direktnachricht" : "Gruppen-Einladung"}
												</p>
											</div>
											<div className="flex gap-3 justify-center">
												<Button
													className="gap-2"
													onClick={() => {
														client
															.joinRoom(selectedRoomId!)
															.catch(() => toast.error("Beitreten fehlgeschlagen."));
													}}
												>
													Annehmen
												</Button>
												<Button
													variant="outline"
													className="gap-2 text-destructive"
													onClick={() => {
														client.leave(selectedRoomId!).catch(() => {});
														setSelectedRoomId(null);
													}}
												>
													Ablehnen
												</Button>
											</div>
										</div>
									</div>
								) : (
									<>
										{/* DM mit invited Member — Hinweis-Banner */}
										{selectedRoom.dmUserId &&
											selectedRoom.membership === "join" &&
											(() => {
												const matrixRoom = client.getRoom(selectedRoomId!);
												const otherMembership = matrixRoom?.getMember(
													selectedRoom.dmUserId,
												)?.membership;
												if (otherMembership === "invite") {
													return (
														<div className="flex items-center justify-center gap-2 px-4 py-2 bg-amber-500/10 text-amber-500 text-sm border-b border-amber-500/20">
															<span>Warte auf Antwort von {selectedRoom.name}…</span>
														</div>
													);
												}
												return null;
											})()}
										{/* Pinned Messages Banner */}
										{pinnedEventIds.length > 0 && (
											<button
												type="button"
												className="flex items-center gap-2 w-full px-4 py-1.5 bg-muted/50 text-xs text-muted-foreground border-b border-border hover:bg-muted/80 transition-colors"
												onClick={() => setShowRoomSettings(true)}
											>
												<Pin className="h-3 w-3 text-amber-500 shrink-0" />
												<span>
													{pinnedEventIds.length === 1
														? "1 angepinnte Nachricht"
														: `${pinnedEventIds.length} angepinnte Nachrichten`}
												</span>
												<span className="ml-auto text-[10px] text-muted-foreground/60">
													Anzeigen
												</span>
											</button>
										)}
										<Timeline
											messages={messages}
											isLoading={isLoading}
											canLoadMore={canLoadMore}
											onLoadMore={loadMore}
											onReact={handleReact}
											onReply={handleReply}
											onEdit={handleEdit}
											onRedact={handleRedact}
											onForward={handleForward}
											onPin={canPin ? handlePin : undefined}
											pinnedEventIds={pinnedEventIds}
											client={client}
											roomId={selectedRoomId}
											onThreadOpen={handleThreadOpen}
										/>
										<TypingIndicator typers={typers} />
										<div className="flex items-end border-t border-border">
											<div className="flex-1">
												<MessageComposer
													client={client}
													roomId={selectedRoomId!}
													editState={editState}
													onEditCancel={() => setEditState(null)}
													replyState={replyState}
													onReplyCancel={() => setReplyState(null)}
												/>
											</div>
											{/* B-7: Poll erstellen Button */}
											<CreatePollDialog
												client={client}
												roomId={selectedRoomId!}
												trigger={
													<Button
														type="button"
														variant="ghost"
														size="icon"
														className="shrink-0 h-[44px] w-[44px] text-muted-foreground hover:text-foreground mr-1 mb-3"
														title="Abstimmung erstellen"
													>
														<BarChart2 className="h-4 w-4" />
													</Button>
												}
											/>
										</div>
									</>
								)}
							</>
						) : (
							<div className="flex-1 flex items-center justify-center text-muted-foreground">
								<div className="text-center space-y-3">
									<div className="flex items-center justify-center">
										<div className="h-16 w-16 rounded-full bg-muted/50 flex items-center justify-center">
											<MessageCircle className="h-8 w-8 text-muted-foreground/50" />
										</div>
									</div>
									<div>
										<p className="font-medium text-foreground">Raum auswählen</p>
										<p className="text-sm mt-1 text-muted-foreground">
											Wähle links einen Raum aus, um zu chatten.
										</p>
									</div>
								</div>
							</div>
						)}
					</div>

					{/* B-8: Thread Side-Panel */}
					{activeThreadId && selectedRoom && client && (
						<ThreadPanel
							client={client}
							roomId={selectedRoomId!}
							threadRootId={activeThreadId}
							threadRootMessage={messages.find((m) => m.eventId === activeThreadId) ?? null}
							onClose={() => setActiveThreadId(null)}
						/>
					)}

					{/* B-8: Thread Overview */}
					{showThreadOverview && !activeThreadId && selectedRoom && client && (
						<ThreadOverview
							client={client}
							roomId={selectedRoomId!}
							onClose={() => setShowThreadOverview(false)}
							onThreadSelect={(threadRootId) => {
								setActiveThreadId(threadRootId);
								setShowThreadOverview(false);
							}}
						/>
					)}

					{/* Activity Centre */}
					{showActivity && client && (
						<ActivityCentre
							client={client}
							onClose={() => setShowActivity(false)}
							onRoomSelect={(roomId) => {
								setSelectedRoomId(roomId);
								setShowActivity(false);
							}}
							onThreadSelect={(roomId, threadRootId) => {
								setSelectedRoomId(roomId);
								setActiveThreadId(threadRootId);
								setShowActivity(false);
							}}
						/>
					)}

					{/* Space Settings */}
					{spaceSettingsId &&
						client &&
						(() => {
							const space = spaces.find((s) => s.roomId === spaceSettingsId);
							if (!space) return null;
							return (
								<SpaceSettings
									client={client}
									space={space}
									hierarchy={space.hierarchy}
									onFetchHierarchy={() => fetchHierarchy(spaceSettingsId)}
									onClose={() => setSpaceSettingsId(null)}
								/>
							);
						})()}

					{/* UI-8: Search Side-Panel */}
					{showSearch && !activeThreadId && !showRoomSettings && selectedRoom && client && (
						<SearchPanel
							client={client}
							roomId={selectedRoomId!}
							onClose={() => setShowSearch(false)}
						/>
					)}

					{/* InfoPanel: DM oder Room */}
					{showRoomSettings &&
						!activeThreadId &&
						selectedRoom &&
						client &&
						(selectedRoom.dmUserId ? (
							<DMInfoPanel
								client={client}
								roomId={selectedRoomId!}
								dmUserId={selectedRoom.dmUserId}
								membership={selectedRoom.membership}
								onClose={() => setShowRoomSettings(false)}
							/>
						) : (
							<RoomInfoPanel
								client={client}
								roomId={selectedRoomId!}
								onClose={() => setShowRoomSettings(false)}
							/>
						))}
				</div>
			</div>
			{/* B-9: Call-Overlay (Klingeln + aktiver Call) */}
			<CallOverlay call={callState} />

			{/* UI-13: Forward-Dialog */}
			{forwardState && client && (
				<ForwardDialog
					open={!!forwardState}
					onOpenChange={(open) => {
						if (!open) setForwardState(null);
					}}
					client={client}
					rooms={rooms}
					messageBody={forwardState.body}
					senderName={forwardState.senderName}
				/>
			)}
		</>
	);
}
