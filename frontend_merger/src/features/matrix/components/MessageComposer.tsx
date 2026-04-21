"use client";

import { useCommands } from "@matrix/lib/hooks/useCommands";
import { useRoomMembers } from "@matrix/lib/hooks/useRoomMembers";
import { sendTyping } from "@matrix/lib/hooks/useTyping";
import { useUploadQueue } from "@matrix/lib/hooks/useUploadQueue";
import type { RoomInfo } from "@matrix/lib/types";
import { Mic, MicOff, Paperclip, Pencil, Reply, Send, SmilePlus, X } from "lucide-react";
import { EventType, type MatrixClient, MsgType, RelationType } from "matrix-js-sdk";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { UploadQueueBar } from "./composer/UploadQueueBar";
import { WysiwygEditor, type WysiwygEditorRef } from "./composer/WysiwygEditor";
import { EmojiPicker } from "./EmojiPicker";

export interface EditState {
	eventId: string;
	body: string;
}

interface Props {
	client: MatrixClient;
	roomId: string;
	disabled?: boolean;
	editState?: EditState | null;
	onEditCancel?: () => void;
	replyState?: { eventId: string; sender: string; body: string } | null;
	onReplyCancel?: () => void;
	threadId?: string | null; // B-8: Thread-Reply senden
}

const TYPING_TIMEOUT_MS = 4000;

// ─── Komponente ───────────────────────────────────────────────────────────────

export function MessageComposer({
	client,
	roomId,
	disabled,
	editState,
	onEditCancel,
	replyState,
	onReplyCancel,
	threadId,
}: Props) {
	const editorRef = useRef<WysiwygEditorRef>(null);
	const [hasContent, setHasContent] = useState(false);
	const [isSending, setIsSending] = useState(false);
	const [isRecordingUploading, setIsRecordingUploading] = useState(false);
	const [isRecording, setIsRecording] = useState(false);
	const [recordingDuration, setRecordingDuration] = useState(0);
	const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
	const [isDragOver, setIsDragOver] = useState(false);
	const emojiPickerRef = useRef<HTMLDivElement>(null);
	const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const recorderRef = useRef<MediaRecorder | null>(null);
	const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const audioChunksRef = useRef<Blob[]>([]);

	// Multi-file Upload-Queue: Drag-Drop, Per-Item-Progress, Retry bei Fehler.
	const uploadQueue = useUploadQueue(client, roomId, (message) => toast.error(message));

	// Slash-Command-Parser: /me, /shrug, /kick, /ban, /invite, /plain, /html etc.
	const runCommand = useCommands(client, roomId);

	// Room-Members für @-Mention-Autocomplete
	const { members } = useRoomMembers(client, roomId);
	const myUserId = client.getUserId() ?? "";

	// Joined Rooms für #-Room-Pills (leichtgewichtig, kein Sync-Hook nötig)
	const joinedRooms = useMemo((): RoomInfo[] => {
		return (client.getRooms?.() ?? [])
			.filter((r) => r.getMyMembership() === "join")
			.map((r) => ({
				roomId: r.roomId,
				name: r.name ?? r.roomId,
				memberCount: r.getInvitedAndJoinedMemberCount(),
				unreadCount: 0,
				membership: "join" as const,
			}));
	}, [client]);

	// Edit-Modus: Editor mit aktuellem Body füllen
	useEffect(() => {
		if (editState) {
			editorRef.current?.setContent(editState.body);
			editorRef.current?.focus();
			setHasContent(true);
		}
	}, [editState]);

	// Click-Outside schließt den Emoji-Picker
	useEffect(() => {
		if (!emojiPickerOpen) return;
		function handleClickOutside(e: MouseEvent) {
			if (emojiPickerRef.current && !emojiPickerRef.current.contains(e.target as Node)) {
				setEmojiPickerOpen(false);
			}
		}
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, [emojiPickerOpen]);

	const handleTyping = useCallback(() => {
		sendTyping(client, roomId, true);
		if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
		typingTimerRef.current = setTimeout(() => {
			sendTyping(client, roomId, false);
		}, TYPING_TIMEOUT_MS);
	}, [client, roomId]);

	// ─── Audio-Aufnahme ─────────────────────────────────────────────────────────
	const startRecording = useCallback(async () => {
		if (!navigator.mediaDevices?.getUserMedia) {
			toast.error("Mikrofon nicht verfügbar (HTTPS erforderlich).");
			return;
		}
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			const recorder = new MediaRecorder(stream, {
				mimeType: MediaRecorder.isTypeSupported("audio/ogg; codecs=opus")
					? "audio/ogg; codecs=opus"
					: "audio/webm; codecs=opus",
			});
			audioChunksRef.current = [];
			recorder.ondataavailable = (e) => {
				if (e.data.size > 0) audioChunksRef.current.push(e.data);
			};
			recorder.onstop = async () => {
				for (const t of stream.getTracks()) t.stop();
				if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
				const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType });
				if (blob.size < 100) return; // zu kurz
				setIsRecordingUploading(true);
				try {
					const file = new File([blob], "voice-message.ogg", { type: recorder.mimeType });
					const uploadRes = await client.uploadContent(file, { name: file.name });
					const durationMs = recordingDuration * 1000;
					await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
						roomId,
						EventType.RoomMessage,
						{
							msgtype: MsgType.Audio,
							body: "Sprachnachricht",
							url: uploadRes.content_uri,
							info: { mimetype: recorder.mimeType, size: blob.size, duration: durationMs },
							"org.matrix.msc3245.voice": {},
						},
					);
				} catch (err) {
					console.error("[composer] voice upload failed:", err);
					toast.error("Sprachnachricht konnte nicht gesendet werden.");
				} finally {
					setIsRecordingUploading(false);
					setRecordingDuration(0);
				}
			};
			recorder.start();
			recorderRef.current = recorder;
			setIsRecording(true);
			setRecordingDuration(0);
			recordingTimerRef.current = setInterval(() => setRecordingDuration((d) => d + 1), 1000);
		} catch (err) {
			console.error("[composer] mic access failed:", err);
			const msg =
				err instanceof DOMException && err.name === "NotAllowedError"
					? "Mikrofon-Zugriff verweigert. Bitte in den Browser-Einstellungen erlauben."
					: err instanceof DOMException && err.name === "NotFoundError"
						? "Kein Mikrofon gefunden."
						: "Mikrofon konnte nicht aktiviert werden.";
			toast.error(msg);
		}
	}, [client, roomId, recordingDuration]);

	const stopRecording = useCallback(() => {
		if (recorderRef.current?.state === "recording") {
			recorderRef.current.stop();
		}
		setIsRecording(false);
	}, []);

	const cancelRecording = useCallback(() => {
		if (recorderRef.current?.state === "recording") {
			recorderRef.current.ondataavailable = null;
			recorderRef.current.onstop = () => {
				for (const t of recorderRef.current?.stream.getTracks() ?? []) t.stop();
			};
			recorderRef.current.stop();
		}
		if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
		setIsRecording(false);
		setRecordingDuration(0);
	}, []);

	const send = useCallback(async () => {
		const editor = editorRef.current;
		if (!editor || editor.isEmpty() || isSending) return;

		let text = editor.getText().trim();
		let html = editor.getHTML();

		// Slash-Command-Handling (Edit/Reply/Thread ueberspringen Commands —
		// Commands sind nur im "freien" Send-Modus relevant).
		const currentEditState = editState;
		const currentReplyState = replyState;
		const inSpecialMode = !!currentEditState || !!currentReplyState || !!threadId;

		if (!inSpecialMode) {
			const outcome = await runCommand(text);
			if (outcome) {
				if (outcome.kind === "handled") {
					// Command hat selbst gesendet — Editor leeren und fertig.
					editor.clear();
					setHasContent(false);
					if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
					sendTyping(client, roomId, false);
					return;
				}
				if (outcome.kind === "error") {
					toast.error(outcome.message);
					return;
				}
				// "pass-through": Text durch Command-Output ersetzen (Shrug/Tableflip/Plain).
				text = outcome.body;
				html = outcome.htmlBody ?? "";
			}
		}

		const mentionedUserIds = editor.getMentionedUserIds();
		const isRoomMention = editor.hasRoomMention();
		// Nur formatted senden wenn tatsächlich HTML-Formatierung vorliegt
		const hasFormatting = html !== "" && html !== `<p>${text}</p>`;

		if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
		sendTyping(client, roomId, false);

		setIsSending(true);
		editor.clear();
		setHasContent(false);
		// Clear edit/reply immediately so a second Enter can't re-trigger
		if (currentEditState) onEditCancel?.();
		if (currentReplyState) onReplyCancel?.();

		// Message-Content aufbauen — mit optionalem formatted_body + m.mentions
		const msgContent: Record<string, unknown> = {
			msgtype: MsgType.Text,
			body: text,
		};
		if (hasFormatting) {
			msgContent.format = "org.matrix.custom.html";
			msgContent.formatted_body = html;
		}
		if (mentionedUserIds.length > 0 || isRoomMention) {
			const mentions: Record<string, unknown> = {};
			if (mentionedUserIds.length > 0) mentions.user_ids = mentionedUserIds;
			if (isRoomMention) mentions.room = true; // MSC3952: @room Notification
			msgContent["m.mentions"] = mentions;
		}

		try {
			if (currentEditState) {
				// B-1: Edit — m.replace Relation
				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					{
						...msgContent,
						body: `* ${text}`,
						"m.new_content": msgContent,
						"m.relates_to": { rel_type: RelationType.Replace, event_id: currentEditState.eventId },
					},
				);
			} else if (currentReplyState) {
				// UI-4: Reply — m.in_reply_to Relation
				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					{
						...msgContent,
						"m.relates_to": { "m.in_reply_to": { event_id: currentReplyState.eventId } },
					},
				);
			} else if (threadId) {
				// B-8: Thread-Reply — SDK sendMessage mit threadId (setzt m.thread Relation intern)
				await (client.sendMessage as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					threadId,
					msgContent,
				);
			} else if (hasFormatting || mentionedUserIds.length > 0 || isRoomMention) {
				// Formatted/Mention → sendEvent statt sendTextMessage
				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					msgContent,
				);
			} else {
				await client.sendTextMessage(roomId, text);
			}
		} catch (err) {
			console.error("[composer] send failed:", err);
			toast.error("Nachricht konnte nicht gesendet werden.");
			editor.setContent(text);
			setHasContent(true);
		} finally {
			setIsSending(false);
		}
	}, [
		client,
		roomId,
		isSending,
		editState,
		onEditCancel,
		replyState,
		onReplyCancel,
		threadId,
		runCommand,
	]);

	const handleFileChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			const files = e.target.files;
			if (!files || files.length === 0) return;
			uploadQueue.addFiles(files);
			e.target.value = "";
			// Fokus zurueck auf Editor damit Enter direkt funktioniert.
			setTimeout(() => editorRef.current?.focus(), 50);
		},
		[uploadQueue],
	);

	const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
		if (e.dataTransfer.types.includes("Files")) {
			e.preventDefault();
			setIsDragOver(true);
		}
	}, []);

	const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
		// Nur wenn Drag den kompletten Container verlaesst (nicht Child-Kreuzung).
		if (e.currentTarget === e.target) setIsDragOver(false);
	}, []);

	const handleDrop = useCallback(
		(e: React.DragEvent<HTMLDivElement>) => {
			e.preventDefault();
			setIsDragOver(false);
			const files = e.dataTransfer.files;
			if (files && files.length > 0) {
				uploadQueue.addFiles(files);
				setTimeout(() => editorRef.current?.focus(), 50);
			}
		},
		[uploadQueue],
	);

	const sendQueuedFiles = useCallback(async () => {
		const caption = editorRef.current?.getText().trim() ?? "";
		editorRef.current?.clear();
		setHasContent(false);
		await uploadQueue.uploadAll(caption);
		// Fertige Items nach Upload aus der Leiste entfernen, Fehler bleiben sichtbar.
		uploadQueue.clearDone();
	}, [uploadQueue]);

	const handleEditorSubmit = useCallback(() => {
		if (uploadQueue.hasItems) {
			void sendQueuedFiles();
		} else {
			send();
		}
	}, [send, uploadQueue.hasItems, sendQueuedFiles]);

	const handleEditorEscape = useCallback(() => {
		if (uploadQueue.hasItems) {
			// Esc leert alle pendenten Items; laufende Uploads bleiben, Fehler werden entfernt.
			for (const item of uploadQueue.items) {
				if (item.status === "pending" || item.status === "error") {
					uploadQueue.removeItem(item.id);
				}
			}
		} else if (replyState) {
			onReplyCancel?.();
		} else if (editState) {
			onEditCancel?.();
			editorRef.current?.clear();
			setHasContent(false);
		}
	}, [editState, onEditCancel, replyState, onReplyCancel, uploadQueue]);

	const isDisabled = disabled || isSending || isRecordingUploading || uploadQueue.isUploading;

	return (
		<div
			className={`flex flex-col bg-background ${isDragOver ? "ring-2 ring-primary ring-inset" : ""}`}
			onDragOver={handleDragOver}
			onDragLeave={handleDragLeave}
			onDrop={handleDrop}
		>
			{/* Reply-Banner */}
			{replyState && (
				<div className="flex items-center justify-between px-3 pt-2 pb-1 text-xs text-muted-foreground border-b border-border/30">
					<span className="flex items-center gap-1 min-w-0">
						<Reply className="h-3 w-3 shrink-0" />
						<span className="font-medium shrink-0">{replyState.sender}:</span>
						<span className="truncate">{replyState.body}</span>
					</span>
					<button
						type="button"
						className="hover:text-foreground transition-colors"
						onClick={() => {
							onReplyCancel?.();
						}}
						title="Antwort abbrechen (Esc)"
					>
						<X className="h-3.5 w-3.5" />
					</button>
				</div>
			)}
			{/* Edit-Banner (B-1) */}
			{editState && (
				<div className="flex items-center justify-between px-3 pt-2 pb-1 text-xs text-muted-foreground border-b border-border/30">
					<span className="flex items-center gap-1">
						<Pencil className="h-3 w-3" />
						Nachricht bearbeiten
					</span>
					<button
						type="button"
						className="hover:text-foreground transition-colors"
						onClick={() => {
							onEditCancel?.();
							editorRef.current?.clear();
							setHasContent(false);
						}}
						title="Bearbeiten abbrechen (Esc)"
					>
						<X className="h-3.5 w-3.5" />
					</button>
				</div>
			)}
			{/* Upload-Queue (mehrere Files, Retry, Per-Item-Progress) */}
			<UploadQueueBar
				items={uploadQueue.items}
				onRemove={uploadQueue.removeItem}
				onRetry={uploadQueue.retryItem}
				onReplaceFile={uploadQueue.replaceFile}
			/>
			<div className="flex items-end gap-2 p-3">
				{/* Datei-Upload (mehrere Files gleichzeitig erlaubt) */}
				<input
					ref={fileInputRef}
					type="file"
					accept="*/*"
					className="hidden"
					multiple
					onChange={handleFileChange}
					disabled={isDisabled}
				/>

				{isRecording ? (
					/* Recording-UI */
					<>
						<Button
							type="button"
							variant="ghost"
							size="icon"
							onClick={cancelRecording}
							className="shrink-0 h-10 w-10 text-muted-foreground hover:text-foreground"
							title="Aufnahme abbrechen"
						>
							<MicOff className="h-4 w-4" />
						</Button>
						<div className="flex-1 flex items-center gap-3 px-4 py-2 rounded-xl bg-destructive/10 border border-destructive/20">
							<span className="h-2 w-2 rounded-full bg-destructive animate-pulse" />
							<span className="text-sm text-destructive font-medium">
								{Math.floor(recordingDuration / 60)}:
								{(recordingDuration % 60).toString().padStart(2, "0")}
							</span>
							<span className="text-xs text-muted-foreground">Aufnahme läuft...</span>
						</div>
						<Button
							size="icon"
							onClick={stopRecording}
							className="shrink-0 h-10 w-10 rounded-full bg-destructive hover:bg-destructive/80"
							title="Aufnahme senden"
						>
							<Send className="h-4 w-4" />
						</Button>
					</>
				) : (
					/* Normal-UI */
					<>
						<Button
							type="button"
							variant="ghost"
							size="icon"
							onClick={() => fileInputRef.current?.click()}
							disabled={isDisabled}
							className="shrink-0 h-10 w-10 text-muted-foreground hover:text-foreground"
							title="Datei anhängen"
						>
							<Paperclip className="h-4 w-4" />
						</Button>

						{/* WYSIWYG Editor mit Emoji-Button */}
						<div className="relative flex-1" ref={emojiPickerRef}>
							<Button
								type="button"
								variant="ghost"
								size="icon"
								onClick={() => setEmojiPickerOpen((v) => !v)}
								disabled={isDisabled}
								className="absolute right-1.5 bottom-1.5 h-7 w-7 text-muted-foreground hover:text-foreground z-10"
								title="Emoji einfügen"
							>
								<SmilePlus className="h-4 w-4" />
							</Button>
							{emojiPickerOpen && (
								<div className="absolute bottom-full right-0 mb-2 z-50">
									<EmojiPicker
										onSelect={(emoji) => {
											editorRef.current?.focus();
											// Emoji in den Editor einfügen (als Text)
											document.execCommand("insertText", false, emoji);
											setEmojiPickerOpen(false);
										}}
									/>
								</div>
							)}
							<WysiwygEditor
								ref={editorRef}
								members={members}
								rooms={joinedRooms}
								roomId={roomId}
								myUserId={myUserId}
								placeholder={
									uploadQueue.isUploading
										? "Dateien werden hochgeladen…"
										: uploadQueue.hasItems
											? "Bildunterschrift (optional) — Enter zum Senden"
											: "Nachricht schreiben..."
								}
								disabled={isDisabled}
								onUpdate={(isEmpty) => {
									setHasContent(!isEmpty);
									if (!isEmpty) handleTyping();
								}}
								onSubmit={handleEditorSubmit}
								onEscape={handleEditorEscape}
							/>
						</div>

						{hasContent ? (
							<Button
								size="icon"
								onClick={send}
								disabled={isDisabled}
								className="shrink-0 h-10 w-10 rounded-full"
							>
								<Send className="h-4 w-4" />
							</Button>
						) : (
							<Button
								type="button"
								variant="ghost"
								size="icon"
								onClick={startRecording}
								disabled={isDisabled}
								className="shrink-0 h-10 w-10 text-muted-foreground hover:text-foreground"
								title="Sprachnachricht aufnehmen"
							>
								<Mic className="h-4 w-4" />
							</Button>
						)}
					</>
				)}
			</div>
		</div>
	);
}
