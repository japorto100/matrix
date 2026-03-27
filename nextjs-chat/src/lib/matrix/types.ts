"use client";

import type { MatrixEvent, Room } from "matrix-js-sdk";

/** Matrix-Credentials die der Client braucht. */
export interface MatrixCredentials {
	homeserverUrl: string;
	userId: string;
	accessToken: string;
	deviceId?: string;
}

/** Eine aufgelöste Nachricht für die UI. */
export interface ResolvedMessage {
	eventId: string;
	sender: string;
	senderDisplayName: string;
	body: string;
	formattedBody?: string; // org.matrix.custom.html
	timestamp: number;
	isOwn: boolean;
	isBot: boolean;
	isEdited: boolean;
	isRedacted: boolean; // B-4: Event wurde gelöscht
	msgType: string; // m.text, m.image, m.video, m.audio, m.file, m.location, m.emote, m.notice …
	// Media
	url?: string; // aufgelöste HTTP-URL (mxc:// → /_matrix/media/v3/download/...)
	thumbnailUrl?: string;
	mimeType?: string;
	fileSize?: number; // Bytes
	fileName?: string;
	width?: number; // Pixel
	height?: number;
	duration?: number; // ms
	isVoice?: boolean; // m.audio + org.matrix.msc3245.voice
	// Reply-Kontext (in_reply_to)
	replyTo?: { eventId: string; sender: string; body: string };
	// Location
	location?: { geoUri: string };
	// Reaktionen { Emoji → Anzahl }
	reactions?: Record<string, number>;
	// Eigene Reactions: { Emoji → Reaction-Event-ID } (zum Entfernen/Ersetzen)
	myReactions?: Record<string, string>;
	// Mention-Highlight (MSC3952: m.mentions.user_ids enthält eigene User-ID)
	isMentioned?: boolean;
	// UI-11: Avatar-URL des Senders
	avatarUrl?: string;
	// B-2: Wer hat diese Nachricht gelesen (userId[])
	readBy?: string[];
	// B-7: Poll (MSC3381)
	isPoll?: boolean;
	pollEventId?: string;
	pollQuestion?: string;
	// B-8: Threads (MSC3440)
	isThreadRoot?: boolean;
	threadReplyCount?: number;
}

/** Raum-Info für die Raumliste. */
export interface RoomInfo {
	roomId: string;
	name: string;
	topic?: string;
	memberCount: number;
	unreadCount: number;
	lastMessage?: string;
	lastTimestamp?: number;
	avatarUrl?: string;
	// B-6: Presence — nur für DMs (2 Mitglieder)
	otherUserId?: string; // userId des anderen Users bei DMs
	isOnline?: boolean; // true = currently active
	// Favourites (m.favourite Tag)
	isFavourite?: boolean;
}

/** Konfigurierbarer Agent-Prefix (aus NEXT_PUBLIC_MATRIX_AGENT_PREFIX oder Standard "agent-"). */
const AGENT_PREFIX = `@${process.env.NEXT_PUBLIC_MATRIX_AGENT_PREFIX ?? "agent-"}`;

/** Prüft ob eine User-ID aus dem Agent-Namespace kommt. */
function isAgentUser(userId: string): boolean {
	return userId.startsWith(AGENT_PREFIX);
}

// ─── Helfer ─────────────────────────────────────────────────────────────────

/**
 * mxc://server/mediaId → HTTP-Download-URL
 * QW-4: Nutzt den lokalen Media-Proxy (/api/matrix/media) für Authenticated Media.
 * Der Proxy sendet den Auth-Header server-seitig, Browser braucht keinen.
 */
export function mxcToHttp(mxcUrl: string, _homeserverUrl: string): string {
	if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
	return `/api/matrix/media?mxc=${encodeURIComponent(mxcUrl.slice(6))}`;
}

/**
 * mxc://server/mediaId → HTTP-Thumbnail-URL
 * QW-4: Nutzt den lokalen Media-Proxy mit Thumbnail-Parameter.
 */
export function mxcToThumbnail(
	mxcUrl: string,
	_homeserverUrl: string,
	width = 800,
	height = 600,
): string {
	if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
	return `/api/matrix/media?mxc=${encodeURIComponent(mxcUrl.slice(6))}&thumbnail=1&w=${width}&h=${height}`;
}

/** Formatiert Bytes in lesbare Größe (KB, MB, …) */
export function formatFileSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── resolveMessage ──────────────────────────────────────────────────────────

/**
 * Konvertiert einen MatrixEvent in eine ResolvedMessage.
 *
 * @param ev             Das MatrixEvent
 * @param myUserId       Eigene User-ID (für isOwn)
 * @param homeserverUrl  Homeserver-Basis-URL (für mxc:// → HTTP)
 * @param replyLookup    Bereits aufgelöste Events für Reply-Kontext
 */
export function resolveMessage(
	ev: MatrixEvent,
	myUserId: string,
	homeserverUrl?: string,
	replyLookup?: Record<string, { sender: string; body: string }>,
): ResolvedMessage | null {
	const evType = ev.getType();
	const content = ev.getContent() as Record<string, unknown>;

	// Redacted non-message Events (z.B. m.reaction) komplett ausblenden
	if (ev.isRedacted() && evType !== "m.room.message") {
		return null;
	}

	// Gelöschte Nachrichten anzeigen
	if (ev.isRedacted()) {
		const sender = ev.getSender() ?? "";
		return {
			eventId: ev.getId() ?? "",
			sender,
			senderDisplayName: sender.split(":")[0]?.replace("@", "") ?? sender,
			body: "[Nachricht gelöscht]",
			timestamp: ev.getTs(),
			isOwn: sender === myUserId,
			isBot: isAgentUser(sender),
			isEdited: false,
			isRedacted: true,
			msgType: "m.text",
		};
	}

	// Sticker (m.sticker top-level event, kein msgtype)
	if (evType === "m.sticker") {
		const sender = ev.getSender() ?? "";
		const info = content.info as Record<string, unknown> | undefined;
		const resolveUrl = (mxcUrl: unknown): string | undefined => {
			if (typeof mxcUrl !== "string" || !mxcUrl.startsWith("mxc://") || !homeserverUrl)
				return undefined;
			return mxcToHttp(mxcUrl, homeserverUrl);
		};
		const resolveThumbnail = (mxcUrl: unknown): string | undefined => {
			if (typeof mxcUrl !== "string" || !mxcUrl.startsWith("mxc://") || !homeserverUrl)
				return undefined;
			return mxcToThumbnail(mxcUrl, homeserverUrl);
		};
		return {
			eventId: ev.getId() ?? "",
			sender,
			senderDisplayName: sender.split(":")[0]?.replace("@", "") ?? sender,
			body: (content.body as string | undefined) ?? "",
			timestamp: ev.getTs(),
			isOwn: sender === myUserId,
			isBot: isAgentUser(sender),
			isEdited: false,
			isRedacted: false,
			msgType: "m.sticker",
			url: resolveUrl(content.url),
			thumbnailUrl: resolveThumbnail(info?.thumbnail_url ?? content.url),
			mimeType: info?.mimetype as string | undefined,
			width: info?.w as number | undefined,
			height: info?.h as number | undefined,
		};
	}

	// B-7: Poll start event (MSC3381) — event type, nicht msgtype
	if (evType === "m.poll.start" || evType === "org.matrix.msc3381.poll.start") {
		const sender = ev.getSender() ?? "";
		const pollContent = (content["m.poll.start"] ?? content["org.matrix.msc3381.poll.start"]) as
			| { question?: { "m.text"?: Array<{ body?: string }> } }
			| undefined;
		const question =
			pollContent?.question?.["m.text"]?.[0]?.body ??
			(content["m.text"] as Array<{ body?: string }> | undefined)?.[0]?.body ??
			(content.body as string | undefined) ??
			"Abstimmung";
		return {
			eventId: ev.getId() ?? "",
			sender,
			senderDisplayName: sender.split(":")[0]?.replace("@", "") ?? sender,
			body: question,
			timestamp: ev.getTs(),
			isOwn: sender === myUserId,
			isBot: isAgentUser(sender),
			isEdited: false,
			isRedacted: false,
			msgType: "m.poll.start",
			isPoll: true,
			pollEventId: ev.getId() ?? "",
			pollQuestion: question,
		};
	}

	// F-5: Widget placeholder (m.widget / im.vector.modular.widgets)
	if (evType === "m.widget" || evType === "im.vector.modular.widgets") {
		const sender = ev.getSender() ?? "";
		const widgetName = (content.name as string) ?? (content.type as string) ?? "Widget";
		const widgetUrl = content.url as string | undefined;
		return {
			eventId: ev.getId() ?? "",
			sender,
			senderDisplayName: sender.split(":")[0]?.replace("@", "") ?? sender,
			body: `[Widget: ${widgetName}]${widgetUrl ? ` — ${widgetUrl}` : ""}`,
			timestamp: ev.getTs(),
			isOwn: sender === myUserId,
			isBot: isAgentUser(sender),
			isEdited: false,
			isRedacted: false,
			msgType: "m.widget",
		};
	}

	// m.room.message und ähnliche
	if (!content || content.msgtype === undefined) return null;

	const sender = ev.getSender() ?? "";
	const info = content.info as Record<string, unknown> | undefined;
	const relates = content["m.relates_to"] as Record<string, unknown> | undefined;

	// Edit-Events (m.replace) nicht als separate Nachricht anzeigen — sie werden vom SDK
	// auf dem Original-Event gemergt und über ev.replacingEvent() abgefragt
	if (relates?.rel_type === "m.replace") return null;

	// mxc:// → HTTP
	function resolveUrl(mxcUrl: unknown): string | undefined {
		if (typeof mxcUrl !== "string" || !mxcUrl.startsWith("mxc://") || !homeserverUrl)
			return undefined;
		return mxcToHttp(mxcUrl, homeserverUrl);
	}

	function resolveThumbnail(mxcUrl: unknown): string | undefined {
		if (typeof mxcUrl !== "string" || !mxcUrl.startsWith("mxc://") || !homeserverUrl)
			return undefined;
		return mxcToThumbnail(mxcUrl, homeserverUrl);
	}

	// Reply-Kontext
	const inReplyTo = relates?.["m.in_reply_to"] as { event_id?: string } | undefined;
	const replyToId = inReplyTo?.event_id;

	// Bei editierten Nachrichten: m.new_content Body bevorzugen (ohne * Prefix)
	const replacingEv = ev.replacingEvent?.();
	const effectiveContent = replacingEv
		? ((replacingEv.getContent()["m.new_content"] as Record<string, unknown> | undefined) ??
			content)
		: content;

	// Fallback-Quote aus Body entfernen (Matrix-Spec: Zeilen mit "> " am Anfang)
	let body =
		(effectiveContent.body as string | undefined) ?? (content.body as string | undefined) ?? "";
	if (replyToId && body.startsWith("> ")) {
		const lines = body.split("\n");
		const firstNonQuote = lines.findIndex((l) => l !== "" && !l.startsWith("> "));
		if (firstNonQuote > 0) {
			body = lines.slice(firstNonQuote).join("\n").trim();
		}
	}

	// Thumbnail: erst info.thumbnail_url, sonst Haupt-URL skaliert
	const thumbnailMxc =
		(info?.thumbnail_url as string | undefined) ?? (content.url as string | undefined);

	return {
		eventId: ev.getId() ?? "",
		sender,
		senderDisplayName: sender.split(":")[0]?.replace("@", "") ?? sender,
		body,
		formattedBody:
			content.format === "org.matrix.custom.html"
				? (content.formatted_body as string | undefined)
				: undefined,
		timestamp: ev.getTs(),
		isOwn: sender === myUserId,
		isBot: isAgentUser(sender),
		isEdited: !!ev.replacingEvent(),
		isRedacted: false,
		msgType: (content.msgtype as string | undefined) ?? "m.text",
		// Media
		url: resolveUrl(content.url),
		thumbnailUrl: resolveThumbnail(thumbnailMxc),
		mimeType: info?.mimetype as string | undefined,
		fileSize: info?.size as number | undefined,
		fileName:
			(content.filename as string | undefined) ??
			(content.msgtype !== "m.text" &&
			content.msgtype !== "m.notice" &&
			content.msgtype !== "m.emote"
				? body
				: undefined),
		width: info?.w as number | undefined,
		height: info?.h as number | undefined,
		duration: info?.duration as number | undefined,
		isVoice: !!content["org.matrix.msc3245.voice"],
		// Reply
		replyTo:
			replyToId && replyLookup?.[replyToId]
				? { eventId: replyToId, ...replyLookup[replyToId] }
				: undefined,
		// Location
		location:
			content.msgtype === "m.location" ? { geoUri: (content.geo_uri as string) ?? "" } : undefined,
		// Mention-Highlight (MSC3952)
		isMentioned: (() => {
			const mentions = content["m.mentions"] as { user_ids?: string[] } | undefined;
			return Array.isArray(mentions?.user_ids) && mentions.user_ids.includes(myUserId);
		})(),
	};
}

// ─── resolveRoom ─────────────────────────────────────────────────────────────

/** Konvertiert einen Room in RoomInfo. Optionaler client für Presence (B-6). */
export function resolveRoom(room: Room, client?: import("matrix-js-sdk").MatrixClient): RoomInfo {
	const lastEvent = room.getLastLiveEvent();
	const lastContent = lastEvent?.getContent() as Record<string, unknown> | undefined;
	const notifs = room.getUnreadNotificationCount();

	// B-6: Presence für DMs (2 joined ODER 1 joined + 1 invited)
	const members = room.getJoinedMembers();
	const myId = client?.getUserId();
	let otherMember = members.length === 2 ? members.find((m) => m.userId !== myId) : undefined;
	// Fallback: invited Members (DM wo anderer noch nicht akzeptiert hat)
	if (!otherMember && members.length === 1) {
		const invited = room.getMembersWithMembership("invite");
		if (invited.length === 1) otherMember = invited[0];
	}
	const otherUser = otherMember ? client?.getUser(otherMember.userId) : undefined;

	return {
		roomId: room.roomId,
		name: room.name ?? room.roomId,
		topic: (
			room.currentState.getStateEvents("m.room.topic", "")?.getContent() as
				| Record<string, unknown>
				| undefined
		)?.topic as string | undefined,
		memberCount: room.getJoinedMemberCount(),
		unreadCount: typeof notifs === "number" ? notifs : 0,
		lastMessage: lastContent?.body as string | undefined,
		lastTimestamp: lastEvent?.getTs(),
		avatarUrl: room.getMxcAvatarUrl() ?? undefined,
		otherUserId: otherMember?.userId,
		isOnline: otherUser?.currentlyActive ?? false,
		isFavourite: !!room.tags?.["m.favourite"],
	};
}
