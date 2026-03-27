"use client";

import {
	Download,
	ExternalLink,
	File,
	FileText,
	Film,
	LayoutGrid,
	Lock,
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
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
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
		<div className="flex flex-col gap-0.5 mb-2 pl-2.5 border-l-2 border-blue-400/50 max-w-full">
			<span className="text-sm font-semibold text-blue-400">{replyTo.sender}</span>
			<span className="text-sm text-muted-foreground line-clamp-2">{replyTo.body}</span>
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
	// URL Preview deaktiviert (SSRF-Risiko, siehe specs/16-security.md)
	// Aktivieren: const previewUrl = !message.isOwn ? extractFirstUrl(message.body) : null;
	const previewUrl: string | null = null;

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
			<p className="whitespace-pre-wrap break-words text-sm">{linkifyText(message.body)}</p>
			{previewUrl && <UrlPreview url={previewUrl} />}
		</div>
	);
}

/** URLs im Text als klickbare Links rendern */
function linkifyText(text: string): (string | React.ReactElement)[] {
	const urlRegex = /https?:\/\/[^\s<>"{}|\\^[\]`]+/g;
	const parts: (string | React.ReactElement)[] = [];
	let lastIndex = 0;
	for (const match of text.matchAll(urlRegex)) {
		const idx = match.index ?? 0;
		if (idx > lastIndex) parts.push(text.slice(lastIndex, idx));
		parts.push(
			<a
				key={idx}
				href={match[0]}
				target="_blank"
				rel="noopener noreferrer"
				className="text-blue-400 hover:underline"
			>
				{match[0]}
			</a>,
		);
		lastIndex = idx + match[0].length;
	}
	if (lastIndex < text.length) parts.push(text.slice(lastIndex));
	return parts;
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

	const hasCaption = message.body && message.body !== message.fileName;

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
					style={{ width: 150, height: 150, maxWidth: 150, maxHeight: 150, objectFit: "contain" }}
					className="rounded-lg bg-muted/30"
					loading="lazy"
				/>
			</button>
			{hasCaption && <p className="text-sm mt-1">{message.body}</p>}
			{/* Lightbox-Dialog mit Download */}
			{lightbox && (
				<Dialog open={lightbox} onOpenChange={setLightbox}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 bg-black/95 border-none overflow-hidden data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=open]:slide-in-from-left-0 data-[state=open]:slide-in-from-top-0"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "Bild"}</DialogTitle>
						<div className="relative flex flex-col items-center justify-center h-full">
							{/* biome-ignore lint/performance/noImgElement: Matrix-URLs sind dynamisch */}
							<img
								src={message.url ?? src}
								alt={message.fileName ?? message.body}
								className="max-w-full max-h-[75vh] object-contain"
							/>
							<div className="absolute top-2 right-2 flex items-center gap-1">
								<a
									href={message.url ?? src}
									download={message.fileName ?? "image"}
									className="h-8 w-8 flex items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
									title="Herunterladen"
								>
									<Download className="h-4 w-4" />
								</a>
								<a
									href={message.url ?? src}
									target="_blank"
									rel="noopener noreferrer"
									className="h-8 w-8 flex items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
									title="In neuem Tab öffnen"
								>
									<ExternalLink className="h-4 w-4" />
								</a>
							</div>
							{message.fileName && (
								<p className="text-xs text-white/70 mt-2 pb-2">{message.fileName}</p>
							)}
						</div>
					</DialogContent>
				</Dialog>
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
				className="rounded-lg bg-black"
				style={{ width: 250, height: 140, maxWidth: 250, maxHeight: 200, objectFit: "contain" }}
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

function DocxContent({ message }: { message: ResolvedMessage }) {
	const [showPreview, setShowPreview] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (!showPreview || !message.url || !containerRef.current) return;
		let cancelled = false;
		(async () => {
			try {
				const { renderAsync } = await import("docx-preview");
				const res = await fetch(message.url!);
				const blob = await res.blob();
				if (cancelled || !containerRef.current) return;
				containerRef.current.innerHTML = "";
				await renderAsync(blob, containerRef.current, undefined, { className: "docx-preview" });
			} catch (err) {
				console.error("[DocxContent] render failed:", err);
				if (containerRef.current)
					containerRef.current.innerHTML =
						"<p class='p-4 text-sm text-muted-foreground'>Vorschau nicht verfügbar</p>";
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [showPreview, message.url]);

	return (
		<>
			<button
				type="button"
				onClick={() => setShowPreview(true)}
				className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors max-w-[280px] border-0 cursor-pointer text-left"
			>
				<FileText className="h-5 w-5 text-blue-500 shrink-0" />
				<div className="flex-1 min-w-0">
					<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
					{message.fileSize !== undefined && (
						<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
					)}
				</div>
			</button>
			{showPreview && (
				<Dialog open={showPreview} onOpenChange={setShowPreview}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 border-none overflow-hidden"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "Dokument"}</DialogTitle>
						<div ref={containerRef} className="w-full h-[80vh] overflow-auto bg-white p-4" />
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

function XlsxContent({ message }: { message: ResolvedMessage }) {
	const [showPreview, setShowPreview] = useState(false);
	const [tableHtml, setTableHtml] = useState<string>("");

	useEffect(() => {
		if (!showPreview || !message.url) return;
		let cancelled = false;
		(async () => {
			try {
				const XLSX = await import("xlsx");
				const res = await fetch(message.url!);
				const buf = await res.arrayBuffer();
				if (cancelled) return;
				const wb = XLSX.read(buf, { type: "array" });
				const sheetName = wb.SheetNames[0];
				const ws = sheetName ? wb.Sheets[sheetName] : undefined;
				if (ws) {
					setTableHtml(XLSX.utils.sheet_to_html(ws));
				}
			} catch (err) {
				console.error("[XlsxContent] render failed:", err);
				setTableHtml("<p class='p-4 text-sm'>Vorschau nicht verfügbar</p>");
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [showPreview, message.url]);

	return (
		<>
			<button
				type="button"
				onClick={() => setShowPreview(true)}
				className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors max-w-[280px] border-0 cursor-pointer text-left"
			>
				<LayoutGrid className="h-5 w-5 text-emerald-500 shrink-0" />
				<div className="flex-1 min-w-0">
					<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
					{message.fileSize !== undefined && (
						<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
					)}
				</div>
			</button>
			{showPreview && (
				<Dialog open={showPreview} onOpenChange={setShowPreview}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 border-none overflow-hidden"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "Tabelle"}</DialogTitle>
						{/* biome-ignore lint/security/noDangerouslySetInnerHtml: SheetJS generiert sicheres HTML aus Zelldaten */}
						<div
							className="w-full h-[80vh] overflow-auto bg-white p-4 text-black [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:border-gray-300 [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs [&_th]:border [&_th]:border-gray-300 [&_th]:px-2 [&_th]:py-1 [&_th]:text-xs [&_th]:bg-gray-100 [&_th]:font-semibold"
							dangerouslySetInnerHTML={{ __html: tableHtml }}
						/>
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

function PdfContent({ message }: { message: ResolvedMessage }) {
	const [showPreview, setShowPreview] = useState(false);
	if (!message.url) return <GenericFileContent message={message} />;
	return (
		<>
			<button
				type="button"
				onClick={() => setShowPreview(true)}
				className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors max-w-[280px] border-0 cursor-pointer text-left"
			>
				<FileText className="h-5 w-5 text-red-500 shrink-0" />
				<div className="flex-1 min-w-0">
					<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
					{message.fileSize !== undefined && (
						<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
					)}
				</div>
			</button>
			{showPreview && (
				<Dialog open={showPreview} onOpenChange={setShowPreview}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 border-none overflow-hidden"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "PDF"}</DialogTitle>
						<iframe
							src={message.url}
							title={message.fileName ?? "PDF"}
							className="w-full h-[80vh] border-0"
						/>
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

function GenericFileContent({ message }: { message: ResolvedMessage }) {
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

function FileContent({ message }: { message: ResolvedMessage }) {
	const mime = message.mimeType ?? "";
	const ext = (message.fileName ?? "").split(".").pop()?.toLowerCase();

	if (mime === "application/pdf") return <PdfContent message={message} />;
	if (
		mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
		ext === "docx"
	)
		return <DocxContent message={message} />;
	if (
		mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
		ext === "xlsx" ||
		ext === "xls" ||
		ext === "csv"
	)
		return <XlsxContent message={message} />;

	return <GenericFileContent message={message} />;
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

function Reactions({
	reactions,
	myReactions,
	onReact,
	eventId,
}: {
	reactions: Record<string, number>;
	myReactions?: Record<string, string>;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
	eventId: string;
}) {
	const entries = Object.entries(reactions);
	if (entries.length === 0) return null;
	return (
		<div className="flex flex-wrap gap-1 mt-1">
			{entries.map(([emoji, count]) => {
				const isMine = !!myReactions?.[emoji];
				return (
					<button
						key={emoji}
						type="button"
						className={cn(
							"inline-flex items-center gap-1 rounded-full px-2 py-1 text-sm transition-colors",
							isMine ? "bg-primary/20 hover:bg-destructive/20 cursor-pointer" : "bg-muted/60",
						)}
						title={isMine ? "Reaktion entfernen" : emoji}
						onClick={() => {
							if (onReact && isMine) {
								onReact(eventId, emoji, myReactions);
							}
						}}
					>
						<span className="text-base">{emoji}</span>
						{count > 1 && (
							<span className="text-xs text-muted-foreground font-medium">{count}</span>
						)}
					</button>
				);
			})}
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
				"inline-block rounded-2xl px-3 py-2 text-sm",
				message.isOwn
					? "bg-zinc-800/90 text-white rounded-tr-sm"
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

const QUICK_REACTIONS = ["👍", "👎", "😂", "🔥", "😮", "😢"];

interface ActionProps {
	message: ResolvedMessage;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
}

function MessageActions({ message, onReact, onReply, onEdit, onRedact, onForward }: ActionProps) {
	const [showReactions, setShowReactions] = useState(false);

	if (message.isRedacted) return null;

	return (
		<div
			className={cn(
				"absolute -top-4 flex flex-col items-end opacity-0 group-hover:opacity-100 transition-opacity z-10",
				message.isOwn ? "right-2" : "left-10",
			)}
		>
			{/* Quick-Reactions Leiste — oberhalb der Action-Buttons */}
			{showReactions && onReact && (
				<div className="flex items-center gap-0.5 bg-popover border border-border/50 rounded-lg shadow-lg px-1.5 py-1 mb-1">
					{QUICK_REACTIONS.map((emoji) => (
						<button
							key={emoji}
							type="button"
							className={cn(
								"h-8 w-8 flex items-center justify-center text-base rounded hover:scale-125 transition-transform",
								message.myReactions?.[emoji] ? "bg-primary/20" : "hover:bg-muted",
							)}
							title={message.myReactions?.[emoji] ? "Reaktion entfernen" : emoji}
							onClick={() => {
								onReact(message.eventId, emoji, message.myReactions);
								setShowReactions(false);
							}}
						>
							{emoji}
						</button>
					))}
				</div>
			)}

			{/* Action-Buttons Leiste */}
			<div className="flex items-center gap-0.5 bg-popover border border-border/50 rounded-lg shadow-sm px-1 py-0.5">
				{onReact && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Reagieren"
						onClick={() => setShowReactions((v) => !v)}
					>
						<SmilePlus className="h-3.5 w-3.5" />
					</Button>
				)}

				{onReply && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Antworten"
						onClick={() => onReply(message.eventId, message.senderDisplayName, message.body)}
					>
						<Reply className="h-3.5 w-3.5" />
					</Button>
				)}

				{onForward && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Weiterleiten"
						onClick={() => onForward(message.body, message.senderDisplayName)}
					>
						<Share className="h-3.5 w-3.5" />
					</Button>
				)}

				{onEdit && message.isOwn && message.msgType === "m.text" && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Bearbeiten"
						onClick={() => onEdit(message.eventId, message.body)}
					>
						<Pencil className="h-3.5 w-3.5" />
					</Button>
				)}

				{onRedact && message.isOwn && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7 hover:bg-destructive/20 hover:text-destructive"
						title="Löschen"
						onClick={() => {
							if (confirm("Nachricht löschen?")) onRedact(message.eventId);
						}}
					>
						<Trash2 className="h-3.5 w-3.5" />
					</Button>
				)}
			</div>
		</div>
	);
}

// ─── MessageRaw ───────────────────────────────────────────────────────────────

// Hash-basierte Sender-Farben (wie Element X Web)
const SENDER_COLORS = [
	"text-blue-400",
	"text-emerald-400",
	"text-violet-400",
	"text-amber-400",
	"text-rose-400",
	"text-cyan-400",
	"text-indigo-400",
	"text-pink-400",
	"text-teal-400",
	"text-orange-400",
	"text-lime-400",
	"text-fuchsia-400",
];
function senderColor(sender: string): string {
	let hash = 0;
	for (let i = 0; i < sender.length; i++) hash = ((hash << 5) - hash + sender.charCodeAt(i)) | 0;
	return SENDER_COLORS[Math.abs(hash) % SENDER_COLORS.length] ?? "text-blue-400";
}

interface Props {
	message: ResolvedMessage;
	isGrouped?: boolean;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
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
	isGrouped,
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
	const timeStr = new Date(message.timestamp).toLocaleTimeString("de-DE", {
		hour: "2-digit",
		minute: "2-digit",
	});
	const isEmote = message.msgType === "m.emote";
	const isDecryptError =
		message.body.startsWith("** Unable to decrypt") || message.body.includes("DecryptionError");

	return (
		<div
			className={cn(
				"relative flex gap-3 px-4 group hover:bg-accent/20 transition-colors",
				message.isOwn && "flex-row-reverse",
				isGrouped ? "py-0.5" : "py-1.5",
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
			{/* Avatar — ausblenden bei gruppierten Messages */}
			{!isGrouped ? (
				<Avatar className="h-8 w-8 shrink-0 mt-0.5">
					{message.avatarUrl && (
						<AvatarImage src={message.avatarUrl} alt={message.senderDisplayName} />
					)}
					<AvatarFallback
						className={cn(
							"text-xs font-semibold text-white",
							message.isBot ? "bg-primary/20 text-primary" : "bg-violet-600",
						)}
					>
						{message.isBot ? "AI" : initials}
					</AvatarFallback>
				</Avatar>
			) : (
				<div className="w-8 shrink-0" />
			)}

			{/* Inhalt */}
			<div className={cn("flex flex-col", message.isOwn ? "items-end max-w-[75%]" : "max-w-[75%]")}>
				{/* Sender + Zeit — nur bei erstem in der Gruppe */}
				{!isGrouped && !isEmote && (
					<div className="flex items-baseline gap-2 mb-0.5">
						<span
							className={cn(
								"text-sm font-semibold leading-none",
								message.isOwn ? "text-foreground" : senderColor(message.sender),
							)}
						>
							{message.senderDisplayName}
						</span>
						{message.isBot && (
							<Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
								Agent
							</Badge>
						)}
						<span className="text-[10px] text-muted-foreground">{timeStr}</span>
						{message.isEdited && (
							<span className="text-[10px] text-muted-foreground italic">(bearbeitet)</span>
						)}
					</div>
				)}

				{/* Nachrichtenblase — B-7: Polls als Sonderfall */}
				{isDecryptError ? (
					<div className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-muted/30 border border-border/50 text-muted-foreground italic text-sm">
						<Lock className="h-4 w-4 shrink-0 text-muted-foreground/60" />
						<span>Diese Nachricht kann nicht entschlüsselt werden</span>
					</div>
				) : message.isPoll && message.pollEventId && client && roomId ? (
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
					<Reactions
						reactions={message.reactions}
						myReactions={message.myReactions}
						onReact={onReact}
						eventId={message.eventId}
					/>
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
