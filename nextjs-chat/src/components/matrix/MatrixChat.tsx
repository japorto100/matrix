"use client";

import { AlertCircle, BarChart2, Loader2 } from "lucide-react";
import { EventType, RelationType } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useCall } from "@/lib/matrix/hooks/useCall";
import { useCrossSigning } from "@/lib/matrix/hooks/useCrossSigning";
import { useMatrixClient } from "@/lib/matrix/hooks/useMatrixClient";
import { useRooms } from "@/lib/matrix/hooks/useRooms";
import { useSpaces } from "@/lib/matrix/hooks/useSpaces";
import { useTimeline } from "@/lib/matrix/hooks/useTimeline";
import { useTyping } from "@/lib/matrix/hooks/useTyping";
import { CallOverlay } from "./CallOverlay";
import { CreatePollDialog } from "./CreatePollDialog";
import { CrossSigningSetup } from "./CrossSigningSetup";
import { ForwardDialog } from "./ForwardDialog";
import { type EditState, MessageComposer } from "./MessageComposer";
import { RoomHeader } from "./RoomHeader";
import { RoomList } from "./RoomList";
import { RoomSettingsPanel } from "./RoomSettingsPanel";
import { SearchPanel } from "./SearchPanel";
import { ThreadPanel } from "./ThreadPanel";
import { Timeline } from "./Timeline";
import { TypingIndicator } from "./TypingIndicator";

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
	const [forwardState, setForwardState] = useState<{ body: string; senderName: string } | null>(
		null,
	);
	const callState = useCall();
	const crossSigning = useCrossSigning(isReady ? client : null);

	const rooms = useRooms(isReady ? client : null);
	const { spaces } = useSpaces(isReady ? client : null);
	const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);
	const { messages, isLoading, canLoadMore, loadMore } = useTimeline(
		isReady ? client : null,
		selectedRoomId,
	);
	const typers = useTyping(isReady ? client : null, selectedRoomId);

	const selectedRoom = rooms.find((r) => r.roomId === selectedRoomId) ?? null;

	// B-8: Thread-Panel schließen bei Raumwechsel
	useEffect(() => {
		setActiveThreadId(null);
		setReplyState(null);
		setShowRoomSettings(false);
		setShowSearch(false);
	}, [selectedRoomId]);

	// B-3: Reaction senden
	const handleReact = useCallback(
		(eventId: string, emoji: string) => {
			if (!client || !selectedRoomId) return;
			(client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
				selectedRoomId,
				EventType.Reaction,
				{ "m.relates_to": { rel_type: RelationType.Annotation, event_id: eventId, key: emoji } },
			).catch((err) => console.error("[react] failed:", err));
		},
		[client, selectedRoomId],
	);

	// UI-4: Reply starten
	const handleReply = useCallback((eventId: string, sender: string, body: string) => {
		setReplyState({ eventId, sender, body });
	}, []);

	// B-1: Edit-Modus starten
	const handleEdit = useCallback((eventId: string, body: string) => {
		setEditState({ eventId, body });
	}, []);

	// B-4: Nachricht löschen (Redaction)
	const handleRedact = useCallback(
		(eventId: string) => {
			if (!client || !selectedRoomId) return;
			client
				.redactEvent(selectedRoomId, eventId)
				.catch((err) => console.error("[redact] failed:", err));
		},
		[client, selectedRoomId],
	);

	// B-8: Thread öffnen
	const handleThreadOpen = useCallback((eventId: string) => {
		setActiveThreadId(eventId);
	}, []);

	// UI-13: Forward
	const handleForward = useCallback((body: string, senderName: string) => {
		setForwardState({ body, senderName });
	}, []);

	// QW-2: Read Receipt für die letzte Nachricht senden wenn Raum aktiv
	useEffect(() => {
		if (!client || !selectedRoomId || messages.length === 0) return;
		const room = client.getRoom(selectedRoomId);
		if (!room) return;
		const events = room.getLiveTimeline().getEvents();
		const lastEv = events[events.length - 1];
		if (lastEv) {
			client.sendReadReceipt(lastEv).catch(() => {});
		}
	}, [client, selectedRoomId, messages]);

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

			<div className="flex h-full overflow-hidden">
				{/* Sidebar — Raumliste */}
				<RoomList
					rooms={rooms}
					selectedRoomId={selectedRoomId}
					onSelect={setSelectedRoomId}
					isLoading={!isReady}
					client={client}
					spaces={spaces}
					selectedSpaceId={selectedSpaceId}
					onSpaceSelect={setSelectedSpaceId}
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
									onCall={(withVideo) => callState.placeCall(selectedRoomId!, withVideo)}
									onSettingsOpen={() => setShowRoomSettings(true)}
									onSearchOpen={() => {
										setShowSearch(true);
										setActiveThreadId(null);
										setShowRoomSettings(false);
									}}
								/>
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
									client={client}
									roomId={selectedRoomId}
									onThreadOpen={handleThreadOpen}
								/>
								<TypingIndicator typers={typers} />
								<div className="flex items-end border-t bg-background">
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
						) : (
							<div className="flex-1 flex items-center justify-center text-muted-foreground">
								<div className="text-center">
									<p className="font-medium">Raum auswählen</p>
									<p className="text-sm mt-1">Wähle links einen Raum aus, um zu chatten.</p>
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

					{/* UI-8: Search Side-Panel */}
					{showSearch && !activeThreadId && !showRoomSettings && selectedRoom && client && (
						<SearchPanel
							client={client}
							roomId={selectedRoomId!}
							onClose={() => setShowSearch(false)}
						/>
					)}

					{/* UI-5+6: Room Settings Side-Panel */}
					{showRoomSettings && !activeThreadId && selectedRoom && client && (
						<RoomSettingsPanel
							client={client}
							roomId={selectedRoomId!}
							onClose={() => setShowRoomSettings(false)}
						/>
					)}
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
