"use client";

import { useRoomMembers } from "@matrix/lib/hooks/useRoomMembers";
import { sendTyping } from "@matrix/lib/hooks/useTyping";
import type { RoomInfo } from "@matrix/lib/types";
import { FileIcon, Mic, MicOff, Paperclip, Pencil, Reply, Send, SmilePlus, X } from "lucide-react";
import { EventType, type MatrixClient, MsgType, RelationType } from "matrix-js-sdk";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { WysiwygEditor, type WysiwygEditorRef } from "./composer/WysiwygEditor";
import { EmojiPicker } from "./EmojiPicker";

async function compressImage(file: File): Promise<File> {
	// Nur Bilder > 5MB komprimieren
	if (!file.type.startsWith("image/") || file.size <= 5 * 1024 * 1024) return file;
	const imageCompression = (await import("browser-image-compression")).default;
	return imageCompression(file, {
		maxSizeMB: 5,
		maxWidthOrHeight: 3840,
		useWebWorker: true,
	});
}

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

// ─── Datei → Matrix msgtype ──────────────────────────────────────────────────

function mimeToMsgtype(mime: string): MsgType {
	if (mime.startsWith("image/")) return MsgType.Image;
	if (mime.startsWith("video/")) return MsgType.Video;
	if (mime.startsWith("audio/")) return MsgType.Audio;
	return MsgType.File;
}

async function readFileDimensions(
	file: File,
): Promise<{ w?: number; h?: number; duration?: number }> {
	return new Promise((resolve) => {
		if (file.type.startsWith("image/")) {
			const img = new Image();
			const url = URL.createObjectURL(file);
			img.onload = () => {
				URL.revokeObjectURL(url);
				resolve({ w: img.naturalWidth, h: img.naturalHeight });
			};
			img.onerror = () => {
				URL.revokeObjectURL(url);
				resolve({});
			};
			img.src = url;
		} else if (file.type.startsWith("video/") || file.type.startsWith("audio/")) {
			const media = document.createElement(file.type.startsWith("video/") ? "video" : "audio") as
				| HTMLVideoElement
				| HTMLAudioElement;
			const url = URL.createObjectURL(file);
			const timeout = setTimeout(() => {
				URL.revokeObjectURL(url);
				resolve({});
			}, 5000);
			media.onloadedmetadata = () => {
				clearTimeout(timeout);
				URL.revokeObjectURL(url);
				const result: { w?: number; h?: number; duration?: number } = {
					duration: Math.round(media.duration * 1000),
				};
				if ("videoWidth" in media) {
					result.w = media.videoWidth;
					result.h = media.videoHeight;
				}
				resolve(result);
			};
			media.onerror = () => {
				clearTimeout(timeout);
				URL.revokeObjectURL(url);
				resolve({});
			};
			media.preload = "metadata";
			media.src = url;
		} else {
			resolve({});
		}
	});
}

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
	const [isUploading, setIsUploading] = useState(false);
	const [pendingFile, setPendingFile] = useState<File | null>(null);
	const [pendingFilePreview, setPendingFilePreview] = useState<string | undefined>();
	const [uploadProgress, setUploadProgress] = useState<number | null>(null);
	const [isRecording, setIsRecording] = useState(false);
	const [recordingDuration, setRecordingDuration] = useState(0);
	const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
	const emojiPickerRef = useRef<HTMLDivElement>(null);
	const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const recorderRef = useRef<MediaRecorder | null>(null);
	const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const audioChunksRef = useRef<Blob[]>([]);

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
				setIsUploading(true);
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
					setIsUploading(false);
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

		const text = editor.getText().trim();
		const html = editor.getHTML();
		const mentionedUserIds = editor.getMentionedUserIds();
		const isRoomMention = editor.hasRoomMention();
		// Nur formatted senden wenn tatsächlich HTML-Formatierung vorliegt
		const hasFormatting = html !== "" && html !== `<p>${text}</p>`;

		if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
		sendTyping(client, roomId, false);

		// Capture current mode BEFORE clearing state to prevent double-send
		const currentEditState = editState;
		const currentReplyState = replyState;

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
	}, [client, roomId, isSending, editState, onEditCancel, replyState, onReplyCancel, threadId]);

	const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;
		e.target.value = "";
		// Max 500MB (Tuwunel Config)
		if (file.size > 500 * 1024 * 1024) {
			toast.error("Datei zu groß (max. 500 MB).");
			return;
		}
		setPendingFile(file);
		if (file.type.startsWith("image/") || file.type.startsWith("video/")) {
			setPendingFilePreview(URL.createObjectURL(file));
		} else {
			setPendingFilePreview(undefined);
		}
		// Fokus zurück auf Editor damit Enter direkt funktioniert
		setTimeout(() => editorRef.current?.focus(), 50);
	}, []);

	const cancelPendingFile = useCallback(() => {
		if (pendingFilePreview) URL.revokeObjectURL(pendingFilePreview);
		setPendingFile(null);
		setPendingFilePreview(undefined);
	}, [pendingFilePreview]);

	const sendPendingFile = useCallback(async () => {
		if (!pendingFile) return;
		const caption = editorRef.current?.getText().trim() ?? "";
		setIsUploading(true);
		editorRef.current?.clear();
		setHasContent(false);
		try {
			// 1. Bilder > 5MB komprimieren
			const fileToUpload = await compressImage(pendingFile);
			// 2. Dimensions lesen (mit 5s Timeout für Videos)
			const dims = await readFileDimensions(fileToUpload);
			const info: Record<string, unknown> = {
				mimetype: fileToUpload.type,
				size: fileToUpload.size,
			};
			if (dims.w) info.w = dims.w;
			if (dims.h) info.h = dims.h;
			if (dims.duration) info.duration = dims.duration;
			// 3. Upload mit Progress (kann bei großen Videos dauern)
			setUploadProgress(0);
			const uploadRes = await client.uploadContent(fileToUpload, {
				name: pendingFile.name,
				progressHandler: ({ loaded, total }) => {
					setUploadProgress(total > 0 ? Math.round((loaded / total) * 100) : 0);
				},
			});
			// 4. Event senden — Caption als body (unter dem Bild angezeigt)
			await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
				roomId,
				EventType.RoomMessage,
				{
					msgtype: mimeToMsgtype(pendingFile.type),
					body: caption || pendingFile.name,
					url: uploadRes.content_uri,
					filename: pendingFile.name,
					info,
				},
			);
			cancelPendingFile();
		} catch (err) {
			console.error("[composer] upload failed:", err);
			toast.error("Datei konnte nicht hochgeladen werden.");
		} finally {
			setIsUploading(false);
			setUploadProgress(null);
		}
	}, [client, roomId, pendingFile, cancelPendingFile]);

	const handleEditorSubmit = useCallback(() => {
		if (pendingFile) {
			sendPendingFile();
		} else {
			send();
		}
	}, [send, pendingFile, sendPendingFile]);

	const handleEditorEscape = useCallback(() => {
		if (pendingFile) {
			cancelPendingFile();
		} else if (replyState) {
			onReplyCancel?.();
		} else if (editState) {
			onEditCancel?.();
			editorRef.current?.clear();
			setHasContent(false);
		}
	}, [editState, onEditCancel, replyState, onReplyCancel, pendingFile, cancelPendingFile]);

	const isDisabled = disabled || isSending || isUploading;

	return (
		<div className="flex flex-col bg-background">
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
			{/* File Preview Banner (WhatsApp-Style) */}
			{pendingFile && (
				<div className="flex items-center gap-3 px-3 pt-2 pb-1 border-b border-border/30">
					{pendingFilePreview && pendingFile.type.startsWith("video/") ? (
						<video
							src={pendingFilePreview}
							className="h-16 w-16 object-cover rounded-lg shrink-0"
							muted
							preload="metadata"
						/>
					) : pendingFilePreview ? (
						// biome-ignore lint/performance/noImgElement: Blob-URL, next/image nicht geeignet
						<img
							src={pendingFilePreview}
							alt={pendingFile.name}
							className="h-16 w-16 object-cover rounded-lg shrink-0"
						/>
					) : (
						<div className="h-16 w-16 flex items-center justify-center rounded-lg bg-muted shrink-0">
							<FileIcon className="h-6 w-6 text-muted-foreground" />
						</div>
					)}
					<div className="flex-1 min-w-0">
						<p className="text-sm font-medium truncate">{pendingFile.name}</p>
						<p className="text-[10px] text-muted-foreground">
							{pendingFile.size < 1024 * 1024
								? `${(pendingFile.size / 1024).toFixed(1)} KB`
								: `${(pendingFile.size / (1024 * 1024)).toFixed(1)} MB`}
							{uploadProgress !== null
								? ` — Upload ${uploadProgress}%`
								: " — Enter zum Senden, Esc zum Abbrechen"}
						</p>
						{uploadProgress !== null && (
							<div className="w-full h-1 bg-muted rounded-full mt-1 overflow-hidden">
								<div
									className="h-full bg-primary rounded-full transition-all duration-300"
									style={{ width: `${uploadProgress}%` }}
								/>
							</div>
						)}
					</div>
					<Button
						variant="ghost"
						size="icon"
						className="shrink-0 h-8 w-8"
						onClick={cancelPendingFile}
						title="Abbrechen (Esc)"
					>
						<X className="h-4 w-4" />
					</Button>
				</div>
			)}
			<div className="flex items-end gap-2 p-3">
				{/* Datei-Upload */}
				<input
					ref={fileInputRef}
					type="file"
					accept="*/*"
					className="hidden"
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
								placeholder={isUploading ? "Datei wird hochgeladen…" : "Nachricht schreiben..."}
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
