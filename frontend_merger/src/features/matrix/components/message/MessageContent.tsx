"use client";

import type { ResolvedMessage } from "@matrix/lib/types";
import type { MatrixWidgetStatus } from "@matrix/lib/widgets";
import {
	AlertTriangle,
	CheckCircle2,
	Clock3,
	ExternalLink,
	LayoutGrid,
	ShieldCheck,
	XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
	AudioContent,
	EmoteContent,
	FileContent,
	ImageContent,
	LocationContent,
	NoticeContent,
	StickerContent,
	TextContent,
	VideoContent,
} from "./content";

export { TextContent } from "./content";

export function ReplyBanner({ replyTo }: { replyTo: NonNullable<ResolvedMessage["replyTo"]> }) {
	return (
		<div className="flex flex-col gap-0.5 mb-2 pl-2.5 border-l-2 border-blue-400/50 max-w-full">
			<span className="text-sm font-semibold text-blue-400">{replyTo.sender}</span>
			<span className="text-sm text-muted-foreground line-clamp-2">{replyTo.body}</span>
		</div>
	);
}

const WIDGET_STATUS_LABEL: Record<MatrixWidgetStatus, string> = {
	approved: "approved",
	pending: "pending",
	blocked: "blocked",
	denied: "denied",
	revoked: "revoked",
	expired: "expired",
	unsupported: "fallback",
};

const WIDGET_STATUS_CLASS: Record<MatrixWidgetStatus, string> = {
	approved: "border-emerald-500/40 text-emerald-500",
	pending: "border-amber-500/40 text-amber-500",
	blocked: "border-rose-500/40 text-rose-500",
	denied: "border-rose-500/40 text-rose-500",
	revoked: "border-zinc-500/40 text-zinc-500",
	expired: "border-zinc-500/40 text-zinc-500",
	unsupported: "border-sky-500/40 text-sky-500",
};

function WidgetStatusIcon({ status }: { status: MatrixWidgetStatus }) {
	if (status === "approved") return <CheckCircle2 className="h-3.5 w-3.5" />;
	if (status === "pending") return <Clock3 className="h-3.5 w-3.5" />;
	if (status === "blocked" || status === "denied") return <XCircle className="h-3.5 w-3.5" />;
	if (status === "unsupported") return <AlertTriangle className="h-3.5 w-3.5" />;
	return <ShieldCheck className="h-3.5 w-3.5" />;
}

function WidgetContent({ message }: { message: ResolvedMessage }) {
	const widget = message.widget;
	const title = widget?.name ?? message.body.replace(/^\[Widget:\s*/, "").replace(/\]$/, "");
	const status = widget?.status ?? (message.url ? "unsupported" : "blocked");
	const reason = widget?.blockedReason ?? widget?.fallbackText;
	const report = widget?.reportArtifact;

	return (
		<div
			className={cn(
				"flex max-w-[360px] items-start gap-2 rounded-lg border border-border/50 bg-background/60 px-2.5 py-2 text-left text-foreground",
				status === "blocked" || status === "denied" ? "border-rose-500/30" : "",
			)}
		>
			<LayoutGrid className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
			<span className="min-w-0 flex-1 space-y-1">
				<span className="flex min-w-0 items-center gap-1.5">
					<span className="min-w-0 flex-1 truncate text-xs font-medium">{title}</span>
					<span
						className={cn(
							"inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 text-[10px]",
							WIDGET_STATUS_CLASS[status],
						)}
					>
						<WidgetStatusIcon status={status} />
						{WIDGET_STATUS_LABEL[status]}
					</span>
				</span>
				{message.url && (
					<span className="block truncate text-[10px] text-muted-foreground">{message.url}</span>
				)}
				{report?.manifestId || report?.outputPath ? (
					<span className="block space-y-0.5 text-[10px] text-muted-foreground">
						<span className="block truncate">report {report.manifestId ?? "manifest pending"}</span>
						{report.outputPath ? <span className="block truncate">{report.outputPath}</span> : null}
						{report.renderer ? <span className="block truncate">{report.renderer}</span> : null}
					</span>
				) : null}
				{reason && <span className="block text-[10px] text-muted-foreground">{reason}</span>}
			</span>
			{message.url && status !== "blocked" && status !== "denied" && (
				<a
					href={message.url}
					target="_blank"
					rel="noopener noreferrer"
					title="Widget in neuem Tab öffnen"
					className="mt-0.5 shrink-0 text-muted-foreground transition-colors hover:text-foreground"
				>
					<ExternalLink className="h-3.5 w-3.5" />
				</a>
			)}
		</div>
	);
}

export function MessageBubble({ message }: { message: ResolvedMessage }) {
	if (message.msgType === "m.sticker") return <StickerContent message={message} />;
	if (message.msgType === "m.emote") return <EmoteContent message={message} />;

	return (
		<div
			className={cn(
				"inline-block rounded-2xl px-3 py-2 text-sm",
				message.isOwn
					? "bg-zinc-800/90 text-white rounded-tr-sm"
					: message.msgType === "m.notice"
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
						return <WidgetContent message={message} />;
					default:
						return <TextContent message={message} />;
				}
			})()}
		</div>
	);
}
