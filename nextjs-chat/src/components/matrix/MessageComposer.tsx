"use client";

import { Paperclip, Pencil, Reply, Send, X } from "lucide-react";
import { EventType, type MatrixClient, MsgType, RelationType } from "matrix-js-sdk";
import { type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { sendTyping } from "@/lib/matrix/hooks/useTyping";
import { cn } from "@/lib/utils";

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
			media.onloadedmetadata = () => {
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
				URL.revokeObjectURL(url);
				resolve({});
			};
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
	const [value, setValue] = useState("");
	const [isSending, setIsSending] = useState(false);
	const [isUploading, setIsUploading] = useState(false);
	const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);

	// Edit-Modus: Textarea mit aktuellem Body füllen
	useEffect(() => {
		if (editState) setValue(editState.body);
	}, [editState]);

	const handleTyping = useCallback(() => {
		sendTyping(client, roomId, true);
		if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
		typingTimerRef.current = setTimeout(() => {
			sendTyping(client, roomId, false);
		}, TYPING_TIMEOUT_MS);
	}, [client, roomId]);

	const send = useCallback(async () => {
		const text = value.trim();
		if (!text || isSending) return;

		if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
		sendTyping(client, roomId, false);

		setIsSending(true);
		setValue("");

		try {
			if (editState) {
				// B-1: Edit — m.replace Relation
				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					{
						msgtype: MsgType.Text,
						body: `* ${text}`,
						"m.new_content": { msgtype: MsgType.Text, body: text },
						"m.relates_to": { rel_type: RelationType.Replace, event_id: editState.eventId },
					},
				);
				onEditCancel?.();
			} else if (replyState) {
				// UI-4: Reply — m.in_reply_to Relation
				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					{
						msgtype: MsgType.Text,
						body: text,
						"m.relates_to": { "m.in_reply_to": { event_id: replyState.eventId } },
					},
				);
				onReplyCancel?.();
			} else if (threadId) {
				// B-8: Thread-Reply — drei-Argument-Overload mit threadId
				await (client.sendMessage as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					threadId,
					{ msgtype: MsgType.Text, body: text },
				);
			} else {
				await client.sendTextMessage(roomId, text);
			}
		} catch (err) {
			console.error("[composer] send failed:", err);
			setValue(text);
		} finally {
			setIsSending(false);
		}
	}, [
		client,
		roomId,
		value,
		isSending,
		editState,
		onEditCancel,
		replyState,
		onReplyCancel,
		threadId,
	]);

	const handleKeyDown = useCallback(
		(e: KeyboardEvent<HTMLTextAreaElement>) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				send();
			} else if (e.key === "Escape" && replyState) {
				onReplyCancel?.();
			} else if (e.key === "Escape" && editState) {
				onEditCancel?.();
				setValue("");
			}
		},
		[send, editState, onEditCancel, replyState, onReplyCancel],
	);

	const handleFileChange = useCallback(
		async (e: React.ChangeEvent<HTMLInputElement>) => {
			const file = e.target.files?.[0];
			if (!file) return;
			// Input zurücksetzen damit man dieselbe Datei nochmal wählen kann
			e.target.value = "";

			setIsUploading(true);
			try {
				// 1. Datei hochladen → mxc:// URI
				const uploadRes = await client.uploadContent(file, { name: file.name });
				const mxcUrl = uploadRes.content_uri;

				// 2. Dimensionen / Dauer auslesen (Browser-seitig)
				const dims = await readFileDimensions(file);

				// 3. Info-Objekt zusammenbauen
				const info: Record<string, unknown> = {
					mimetype: file.type,
					size: file.size,
				};
				if (dims.w) info.w = dims.w;
				if (dims.h) info.h = dims.h;
				if (dims.duration) info.duration = dims.duration;

				const msgtype = mimeToMsgtype(file.type);

				// 4. Event senden (cast nötig: sendEvent-Overloads kennen kein url-Feld auf MsgType.Text)
				const mediaContent: Record<string, unknown> = {
					msgtype,
					body: file.name,
					url: mxcUrl,
					filename: file.name,
					info,
				};
				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					mediaContent,
				);
			} catch (err) {
				console.error("[composer] upload failed:", err);
			} finally {
				setIsUploading(false);
			}
		},
		[client, roomId],
	);

	const isDisabled = disabled || isSending || isUploading;

	return (
		<div className="flex flex-col border-t bg-background">
			{/* Reply-Banner (UI-4) */}
			{replyState && (
				<div className="flex items-center justify-between px-3 pt-2 pb-1 text-xs text-muted-foreground border-b border-dashed">
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
				<div className="flex items-center justify-between px-3 pt-2 pb-1 text-xs text-muted-foreground border-b border-dashed">
					<span className="flex items-center gap-1">
						<Pencil className="h-3 w-3" />
						Nachricht bearbeiten
					</span>
					<button
						type="button"
						className="hover:text-foreground transition-colors"
						onClick={() => {
							onEditCancel?.();
							setValue("");
						}}
						title="Bearbeiten abbrechen (Esc)"
					>
						<X className="h-3.5 w-3.5" />
					</button>
				</div>
			)}
			<div className="flex items-end gap-2 p-3">
				{/* Datei-Upload-Button */}
				<input
					ref={fileInputRef}
					type="file"
					accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.zip,.tar,.gz"
					className="hidden"
					onChange={handleFileChange}
					disabled={isDisabled}
				/>
				<Button
					type="button"
					variant="ghost"
					size="icon"
					onClick={() => fileInputRef.current?.click()}
					disabled={isDisabled}
					className="shrink-0 h-[44px] w-[44px] text-muted-foreground hover:text-foreground"
					title="Datei anhängen"
				>
					<Paperclip className="h-4 w-4" />
				</Button>

				<Textarea
					value={value}
					onChange={(e) => {
						setValue(e.target.value);
						if (e.target.value) handleTyping();
					}}
					onKeyDown={handleKeyDown}
					placeholder={
						isUploading
							? "Datei wird hochgeladen…"
							: "Nachricht schreiben… (Enter zum Senden, Shift+Enter für Zeilenumbruch)"
					}
					className={cn(
						"min-h-[44px] max-h-[160px] resize-none text-sm",
						"focus-visible:ring-1 focus-visible:ring-primary",
					)}
					disabled={isDisabled}
					rows={1}
				/>
				<Button
					size="icon"
					onClick={send}
					disabled={!value.trim() || isDisabled}
					className="shrink-0 h-[44px] w-[44px]"
				>
					<Send className="h-4 w-4" />
				</Button>
			</div>
		</div>
	);
}
