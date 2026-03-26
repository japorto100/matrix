"use client";

import { formatDistanceToNow } from "date-fns";
import { de } from "date-fns/locale";
import {
	Download,
	File,
	FileText,
	Film,
	LayoutGrid,
	MapPin,
	MessageSquare,
	Mic,
	Music,
	Pencil,
	Reply,
	Share,
	SmilePlus,
	Trash2,
} from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeParse from "rehype-parse";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeStringify from "rehype-stringify";
import remarkGfm from "remark-gfm";
import { unified } from "unified";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { formatFileSize, type ResolvedMessage } from "@/lib/matrix/types";
import { cn } from "@/lib/utils";
import { PollMessage } from "./PollMessage";
import { ReadByDialog } from "./ReadByDialog";
import { extractFirstUrl, UrlPreview } from "./UrlPreview";

// ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

function fileIcon(mimeType?: string) {
	if (!mimeType) return <File className="h-5 w-5" />;
	if (mimeType.startsWith("video/")) return <Film className="h-5 w-5" />;
	if (mimeType.startsWith("audio/")) return <Music className="h-5 w-5" />;
	if (mimeType.includes("pdf") || mimeType.includes("text"))
		return <FileText className="h-5 w-5" />;
	return <File className="h-5 w-5" />;
}

function formatDuration(ms: number): string {
	const s = Math.floor(ms / 1000);
	const m = Math.floor(s / 60);
	const sec = s % 60;
	return `${m}:${sec.toString().padStart(2, "0")}`;
}

function osmUrl(geoUri: string): string {
	// geo:lat,lon;u=accuracy
	const [, coords] = geoUri.split(":");
	const [latLon] = (coords ?? "").split(";");
	const [lat, lon] = (latLon ?? "0,0").split(",");
	return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=15`;
}

// ─── Nachrichten-Inhalt-Komponenten ──────────────────────────────────────────

function ReplyBanner({ replyTo }: { replyTo: NonNullable<ResolvedMessage["replyTo"]> }) {
	return (
		<div className="flex items-start gap-1 mb-1.5 pl-2 border-l-2 border-primary/40 text-[11px] text-muted-foreground max-w-full">
			<span className="font-medium shrink-0">{replyTo.sender}:</span>
			<span className="truncate">{replyTo.body}</span>
		</div>
	);
}

// QW-1 Fix: Matrix-Spec erlaubte CSS-Properties filtern statt blanket style zulassen.
// Erlaubt: color, background-color, font-weight, font-style, text-decoration.
function filterMatrixStyle(value: string): string {
	const allowedProps = new Set([
		"color",
		"background-color",
		"font-weight",
		"font-style",
		"text-decoration",
	]);
	return value
		.split(";")
		.map((decl) => decl.trim())
		.filter((decl) => {
			const prop = decl.split(":")[0]?.trim().toLowerCase();
			return prop && allowedProps.has(prop);
		})
		.join("; ");
}

// Matrix erlaubt org.matrix.custom.html in formatted_body.
// Sanitize-Schema: defaultSchema erweitern um code-Attribute.
const sanitizeSchema = {
	...defaultSchema,
	attributes: {
		...defaultSchema.attributes,
		code: [...(defaultSchema.attributes?.code ?? []), "className"],
		span: [...(defaultSchema.attributes?.span ?? []), "className", "style"],
	},
	// QW-1 Fix: style-Attribut nur mit erlaubten CSS-Properties
	allowDangerousHtml: false,
};

/** Unified pipeline: parse HTML fragment → sanitize → stringify. No Markdown interpretation. */
const htmlProcessor = unified()
	.use(rehypeParse, { fragment: true })
	.use(rehypeSanitize, sanitizeSchema)
	.use(rehypeStringify);

function TextContent({ message }: { message: ResolvedMessage }) {
	const previewUrl = !message.isOwn ? extractFirstUrl(message.body) : null;

	// formatted_body vorhanden → HTML direkt verarbeiten (Matrix spec: format = "org.matrix.custom.html")
	// Unified + rehype-parse statt ReactMarkdown, damit Markdown-Metazeichen im HTML nicht fehlinterpretiert werden.
	const sanitizedHtml = useMemo(() => {
		if (!message.formattedBody) return null;
		// QW-1 Fix: Inline-Styles auf erlaubte CSS-Properties einschränken
		const styleFiltered = message.formattedBody.replace(/style="([^"]*)"/g, (_, styles: string) => {
			const filtered = filterMatrixStyle(styles);
			return filtered ? `style="${filtered}"` : "";
		});
		return String(htmlProcessor.processSync(styleFiltered));
	}, [message.formattedBody]);

	if (sanitizedHtml !== null) {
		return (
			<div>
				<div
					className="prose prose-sm dark:prose-invert max-w-none break-words"
					// biome-ignore lint/security/noDangerouslySetInnerHtml: HTML is sanitized by rehype-sanitize above
					dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
				/>
				{previewUrl && <UrlPreview url={previewUrl} />}
			</div>
		);
	}
	if (message.isBot) {
		return (
			<div>
				<div className="prose prose-sm dark:prose-invert max-w-none break-words">
					<ReactMarkdown remarkPlugins={[remarkGfm]}>{message.body}</ReactMarkdown>
				</div>
				{previewUrl && <UrlPreview url={previewUrl} />}
			</div>
		);
	}
	return (
		<div>
			<p className="whitespace-pre-wrap break-words text-sm">{message.body}</p>
			{previewUrl && <UrlPreview url={previewUrl} />}
		</div>
	);
}

function NoticeContent({ message }: { message: ResolvedMessage }) {
	return (
		<p className="whitespace-pre-wrap break-words text-sm italic text-muted-foreground">
			{message.body}
		</p>
	);
}

function EmoteContent({ message }: { message: ResolvedMessage }) {
	return (
		<p className="whitespace-pre-wrap break-words text-sm italic">
			<span className="font-medium not-italic">{message.senderDisplayName}</span> {message.body}
		</p>
	);
}

function ImageContent({ message }: { message: ResolvedMessage }) {
	const [lightbox, setLightbox] = useState(false);
	const src = message.thumbnailUrl ?? message.url;
	if (!src) return <TextContent message={message} />;

	return (
		<>
			<button
				type="button"
				className="block p-0 border-0 bg-transparent cursor-pointer"
				onClick={() => setLightbox(true)}
				title="Bild vergrößern"
			>
				{/* biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch, next/image würde remotePatterns für jeden Homeserver erfordern */}
				<img
					src={src}
					alt={message.fileName ?? message.body}
					className="rounded-lg max-w-[300px] max-h-[300px] object-contain"
					loading="lazy"
				/>
			</button>
			{message.fileName && (
				<p className="text-[10px] text-muted-foreground mt-1 truncate">{message.fileName}</p>
			)}
			{/* Lightbox-Overlay */}
			{lightbox && (
				<button
					type="button"
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 border-0 cursor-zoom-out"
					onClick={() => setLightbox(false)}
					aria-label="Lightbox schließen"
				>
					{/* biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch */}
					<img
						src={message.url ?? src}
						alt={message.fileName ?? message.body}
						className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
					/>
				</button>
			)}
		</>
	);
}

function VideoContent({ message }: { message: ResolvedMessage }) {
	if (!message.url) return <TextContent message={message} />;
	return (
		<div className="space-y-1">
			<video
				src={message.url}
				controls
				poster={message.thumbnailUrl}
				className="rounded-lg max-w-[300px] max-h-[240px]"
				preload="metadata"
			/>
			{message.fileName && (
				<p className="text-[10px] text-muted-foreground truncate">{message.fileName}</p>
			)}
		</div>
	);
}

function AudioContent({ message }: { message: ResolvedMessage }) {
	if (!message.url) return <TextContent message={message} />;

	if (message.isVoice) {
		return (
			<div className="flex items-center gap-2 bg-muted/50 rounded-xl px-3 py-2 min-w-[200px]">
				<Mic className="h-4 w-4 text-primary shrink-0" />
				<audio src={message.url} controls className="h-8 flex-1 min-w-0" preload="metadata" />
				{message.duration && (
					<span className="text-[10px] text-muted-foreground shrink-0">
						{formatDuration(message.duration)}
					</span>
				)}
			</div>
		);
	}

	return (
		<div className="space-y-1">
			<div className="flex items-center gap-2">
				<Music className="h-4 w-4 text-primary shrink-0" />
				{message.fileName && (
					<span className="text-xs font-medium truncate">{message.fileName}</span>
				)}
				{message.duration && (
					<span className="text-[10px] text-muted-foreground">
						{formatDuration(message.duration)}
					</span>
				)}
			</div>
			<audio src={message.url} controls className="w-full h-8" preload="metadata" />
		</div>
	);
}

function FileContent({ message }: { message: ResolvedMessage }) {
	return (
		<a
			href={message.url ?? "#"}
			target="_blank"
			rel="noopener noreferrer"
			download={message.fileName}
			className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors no-underline max-w-[280px]"
		>
			<div className="text-primary shrink-0">{fileIcon(message.mimeType)}</div>
			<div className="flex-1 min-w-0">
				<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
				{message.fileSize !== undefined && (
					<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
				)}
			</div>
			<Download className="h-4 w-4 text-muted-foreground shrink-0" />
		</a>
	);
}

function LocationContent({ message }: { message: ResolvedMessage }) {
	if (!message.location) return <TextContent message={message} />;
	const url = osmUrl(message.location.geoUri);
	return (
		<a
			href={url}
			target="_blank"
			rel="noopener noreferrer"
			className="flex items-center gap-2 text-sm text-primary hover:underline"
		>
			<MapPin className="h-4 w-4 shrink-0" />
			<span>Standort öffnen</span>
		</a>
	);
}

function StickerContent({ message }: { message: ResolvedMessage }) {
	const src = message.thumbnailUrl ?? message.url;
	if (!src) return null;
	return (
		// biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch
		<img
			src={src}
			alt={message.body}
			className="max-w-[128px] max-h-[128px] object-contain"
			loading="lazy"
		/>
	);
}

// ─── Reaktionen ──────────────────────────────────────────────────────────────

function Reactions({ reactions }: { reactions: Record<string, number> }) {
	const entries = Object.entries(reactions);
	if (entries.length === 0) return null;
	return (
		<div className="flex flex-wrap gap-1 mt-1">
			{entries.map(([emoji, count]) => (
				<span
					key={emoji}
					className="inline-flex items-center gap-0.5 bg-muted rounded-full px-1.5 py-0.5 text-xs"
				>
					{emoji}
					{count > 1 && <span className="text-[10px] text-muted-foreground">{count}</span>}
				</span>
			))}
		</div>
	);
}

// ─── B-8: Thread-Chip ────────────────────────────────────────────────────────

function ThreadChip({
	count,
	onOpen,
	isOwn,
}: {
	count: number;
	onOpen: () => void;
	isOwn: boolean;
}) {
	return (
		<button
			type="button"
			onClick={onOpen}
			className={cn(
				"mt-1 flex items-center gap-1 text-xs font-medium text-primary hover:underline",
				isOwn && "self-end",
			)}
		>
			<MessageSquare className="h-3 w-3" />
			{count} {count === 1 ? "Antwort" : "Antworten"}
		</button>
	);
}

// ─── Haupt-Message-Blase ──────────────────────────────────────────────────────

function messageBubble(message: ResolvedMessage) {
	const isEmote = message.msgType === "m.emote";
	const isNotice = message.msgType === "m.notice";
	const isSticker = message.msgType === "m.sticker";

	// Sticker: kein Bubble-Hintergrund
	if (isSticker) return <StickerContent message={message} />;

	// Emote: kein Bubble
	if (isEmote) return <EmoteContent message={message} />;

	return (
		<div
			className={cn(
				"rounded-2xl px-3 py-2 text-sm",
				message.isOwn
					? "bg-primary text-primary-foreground rounded-tr-sm"
					: isNotice
						? "bg-muted/40 rounded-tl-sm border border-border"
						: message.isMentioned
							? "bg-yellow-500/15 rounded-tl-sm border border-yellow-500/40"
							: "bg-muted rounded-tl-sm",
			)}
		>
			{message.replyTo && <ReplyBanner replyTo={message.replyTo} />}
			{(() => {
				switch (message.msgType) {
					case "m.image":
						return <ImageContent message={message} />;
					case "m.video":
						return <VideoContent message={message} />;
					case "m.audio":
						return <AudioContent message={message} />;
					case "m.file":
						return <FileContent message={message} />;
					case "m.location":
						return <LocationContent message={message} />;
					case "m.notice":
						return <NoticeContent message={message} />;
					case "m.widget":
						return (
							<div className="flex items-center gap-2 text-xs text-muted-foreground italic">
								<LayoutGrid className="h-4 w-4 shrink-0" />
								<span>{message.body}</span>
							</div>
						);
					default:
						return <TextContent message={message} />;
				}
			})()}
		</div>
	);
}

// ─── Hover-Aktionen (B-3 Reactions, B-1 Edit, B-4 Redact) ───────────────────

const EMOJI_CATEGORIES: Record<string, string[]> = {
	Häufig: ["👍", "❤️", "😂", "😮", "😢", "🔥", "🎉", "✅"],
	Gesichter: ["😊", "😄", "🤣", "😍", "🤔", "😎", "🥳", "😴"],
	Gesten: ["👋", "🤝", "👏", "💪", "🙏", "✌️", "🤞", "👌"],
	Herzen: ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "💯"],
	Objekte: ["📊", "📈", "📉", "💰", "🏦", "⚡", "🚀", "🎯"],
};

interface ActionProps {
	message: ResolvedMessage;
	onReact?: (eventId: string, emoji: string) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
}

function MessageActions({ message, onReact, onReply, onEdit, onRedact, onForward }: ActionProps) {
	const [pickerOpen, setPickerOpen] = useState(false);
	const [emojiFilter, setEmojiFilter] = useState("");
	const pickerRef = useRef<HTMLDivElement>(null);

	// B-3 Fix: Click-Outside schließt den Emoji-Picker
	useEffect(() => {
		if (!pickerOpen) return;
		function handleClickOutside(e: MouseEvent) {
			if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
				setPickerOpen(false);
			}
		}
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, [pickerOpen]);

	// B-4 Fix: isRedacted boolean statt fragiler String-Vergleich
	if (message.isRedacted) return null;

	return (
		<div
			className={cn(
				"absolute top-1 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity z-10",
				message.isOwn ? "left-2" : "right-2",
			)}
		>
			{/* Reaction-Picker (B-3) */}
			{onReact && (
				<div className="relative" ref={pickerRef}>
					<button
						type="button"
						className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
						title="Reagieren"
						onClick={() => setPickerOpen((v) => !v)}
					>
						<SmilePlus className="h-3.5 w-3.5" />
					</button>
					{pickerOpen && (
						<div
							className={cn(
								"absolute bottom-full mb-1 bg-popover border rounded-xl shadow-lg p-2 z-20 w-[240px]",
								message.isOwn ? "right-0" : "left-0",
							)}
						>
							{/* UI-12: Emoji-Filter */}
							<input
								type="text"
								value={emojiFilter}
								onChange={(e) => setEmojiFilter(e.target.value)}
								placeholder="Emoji suchen…"
								className="w-full rounded-md border bg-background px-2 py-1 text-xs mb-2 focus:outline-none focus:ring-1 focus:ring-primary"
							/>
							<div className="max-h-[200px] overflow-y-auto space-y-1.5">
								{Object.entries(EMOJI_CATEGORIES).map(([category, emojis]) => {
									const filtered = emojiFilter
										? emojis.filter((e) => e.includes(emojiFilter))
										: emojis;
									if (filtered.length === 0) return null;
									return (
										<div key={category}>
											<span className="text-[10px] text-muted-foreground font-medium px-0.5">
												{category}
											</span>
											<div className="flex flex-wrap gap-0.5 mt-0.5">
												{filtered.map((emoji) => (
													<button
														key={`${category}-${emoji}`}
														type="button"
														className="text-base hover:scale-125 transition-transform p-0.5 rounded hover:bg-muted"
														onClick={() => {
															onReact(message.eventId, emoji);
															setPickerOpen(false);
															setEmojiFilter("");
														}}
													>
														{emoji}
													</button>
												))}
											</div>
										</div>
									);
								})}
							</div>
						</div>
					)}
				</div>
			)}

			{/* Reply (UI-4) — alle nicht-gelöschten Nachrichten */}
			{onReply && (
				<button
					type="button"
					className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
					title="Antworten"
					onClick={() => onReply(message.eventId, message.senderDisplayName, message.body)}
				>
					<Reply className="h-3.5 w-3.5" />
				</button>
			)}

			{/* UI-13: Weiterleiten */}
			{onForward && (
				<button
					type="button"
					className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
					title="Weiterleiten"
					onClick={() => onForward(message.body, message.senderDisplayName)}
				>
					<Share className="h-3.5 w-3.5" />
				</button>
			)}

			{/* Edit (B-1) — nur eigene Textnachrichten */}
			{onEdit && message.isOwn && message.msgType === "m.text" && (
				<button
					type="button"
					className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
					title="Bearbeiten"
					onClick={() => onEdit(message.eventId, message.body)}
				>
					<Pencil className="h-3.5 w-3.5" />
				</button>
			)}

			{/* Redact (B-4) — nur eigene Nachrichten */}
			{onRedact && message.isOwn && (
				<button
					type="button"
					className="p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
					title="Löschen"
					onClick={() => {
						if (confirm("Nachricht löschen?")) onRedact(message.eventId);
					}}
				>
					<Trash2 className="h-3.5 w-3.5" />
				</button>
			)}
		</div>
	);
}

// ─── MessageRaw ───────────────────────────────────────────────────────────────

interface Props {
	message: ResolvedMessage;
	onReact?: (eventId: string, emoji: string) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
	client?: MatrixClient | null;
	roomId?: string | null;
	onThreadOpen?: (eventId: string) => void;
}

function MessageRaw({
	message,
	onReact,
	onReply,
	onEdit,
	onRedact,
	onForward,
	client,
	roomId,
	onThreadOpen,
}: Props) {
	const [showReadBy, setShowReadBy] = useState(false);
	const initials = message.senderDisplayName.slice(0, 2).toUpperCase();
	const timeAgo = formatDistanceToNow(message.timestamp, { addSuffix: true, locale: de });
	const isEmote = message.msgType === "m.emote";

	return (
		<div
			className={cn(
				"relative flex gap-3 px-4 py-2 group hover:bg-accent/30 transition-colors",
				message.isOwn && "flex-row-reverse",
			)}
		>
			<MessageActions
				message={message}
				onReact={onReact}
				onReply={onReply}
				onEdit={onEdit}
				onRedact={onRedact}
				onForward={onForward}
			/>
			{/* Avatar — bei Emote ebenfalls zeigen */}
			<Avatar className="h-8 w-8 shrink-0 mt-0.5">
				{message.avatarUrl && (
					<AvatarImage src={message.avatarUrl} alt={message.senderDisplayName} />
				)}
				<AvatarFallback
					className={cn(
						"text-xs font-semibold",
						message.isBot
							? "bg-primary/20 text-primary"
							: message.isOwn
								? "bg-accent text-accent-foreground"
								: "bg-muted text-muted-foreground",
					)}
				>
					{message.isBot ? "AI" : initials}
				</AvatarFallback>
			</Avatar>

			{/* Inhalt */}
			<div className={cn("flex flex-col max-w-[75%]", message.isOwn && "items-end")}>
				{/* Sender + Badges + Zeit (außer bei Emote: nur Zeit) */}
				{!isEmote && (
					<div className="flex items-baseline gap-2 mb-0.5">
						<span className="text-sm font-medium leading-none">{message.senderDisplayName}</span>
						{message.isBot && (
							<Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
								Agent
							</Badge>
						)}
						{message.isEdited && (
							<span className="text-[10px] text-muted-foreground">(bearbeitet)</span>
						)}
						<span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
							{timeAgo}
						</span>
					</div>
				)}

				{/* Nachrichtenblase — B-7: Polls als Sonderfall */}
				{message.isPoll && message.pollEventId && client && roomId ? (
					<PollMessage
						pollEventId={message.pollEventId}
						roomId={roomId}
						client={client}
						isOwn={message.isOwn}
					/>
				) : (
					messageBubble(message)
				)}

				{/* B-8: Thread-Chip unter der Blase */}
				{message.isThreadRoot &&
					message.threadReplyCount !== undefined &&
					message.threadReplyCount > 0 &&
					onThreadOpen && (
						<ThreadChip
							count={message.threadReplyCount}
							onOpen={() => onThreadOpen(message.eventId)}
							isOwn={message.isOwn}
						/>
					)}

				{/* Reaktionen */}
				{message.reactions && Object.keys(message.reactions).length > 0 && (
					<Reactions reactions={message.reactions} />
				)}

				{/* B-2: Read Receipts — Mini-Avatare für eigene Nachrichten (UI-14: klickbar) */}
				{message.isOwn && message.readBy && message.readBy.length > 0 && (
					<>
						<button
							type="button"
							className="flex items-center gap-0.5 mt-0.5 bg-transparent border-0 p-0 cursor-pointer hover:opacity-80 transition-opacity"
							onClick={() => setShowReadBy(true)}
							title="Gelesen von…"
						>
							{message.readBy.slice(0, 5).map((userId) => {
								const ini = userId.split(":")[0]?.replace("@", "").slice(0, 2).toUpperCase() ?? "?";
								return (
									<span
										key={userId}
										className="inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-primary/30 text-primary text-[8px] font-semibold"
									>
										{ini}
									</span>
								);
							})}
							{message.readBy.length > 5 && (
								<span className="text-[8px] text-muted-foreground ml-0.5">
									+{message.readBy.length - 5}
								</span>
							)}
						</button>
						{showReadBy && (
							<ReadByDialog
								open={showReadBy}
								onOpenChange={setShowReadBy}
								readBy={message.readBy}
							/>
						)}
					</>
				)}
			</div>
		</div>
	);
}

export const Message = memo(MessageRaw) as typeof MessageRaw;
