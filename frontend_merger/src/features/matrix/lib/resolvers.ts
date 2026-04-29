/**
 * Matrix event/room resolvers — convert SDK objects to UI types.
 * Extracted from types.ts (Phase 1, exec-07).
 */

import { EventType, type MatrixClient, type MatrixEvent, type Room } from "matrix-js-sdk";
import type { ResolvedMessage, RoomInfo } from "./types";
import { mxcToHttp, mxcToThumbnail } from "./utils";
import { parseMatrixWidgetEvent } from "./widgets";

/** Konfigurierbarer Agent-Prefix (aus NEXT_PUBLIC_MATRIX_AGENT_PREFIX oder Standard "agent-"). */
const AGENT_PREFIX = `@${process.env.NEXT_PUBLIC_MATRIX_AGENT_PREFIX ?? "agent-"}`;

/** Prueft ob eine User-ID aus dem Agent-Namespace kommt. */
export function isAgentUser(userId: string): boolean {
	return userId.startsWith(AGENT_PREFIX);
}

function readString(value: unknown): string | undefined {
	const trimmed = typeof value === "string" ? value.trim() : "";
	return trimmed || undefined;
}

/**
 * Konvertiert einen MatrixEvent in eine ResolvedMessage.
 *
 * @param ev             Das MatrixEvent
 * @param myUserId       Eigene User-ID (fuer isOwn)
 * @param homeserverUrl  Homeserver-Basis-URL (fuer mxc:// → HTTP)
 * @param replyLookup    Bereits aufgeloeste Events fuer Reply-Kontext
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

	// Geloeschte Nachrichten anzeigen
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
		const widget = parseMatrixWidgetEvent(ev);
		const widgetName =
			widget?.name ?? readString(content.name) ?? readString(content.type) ?? "Widget";
		return {
			eventId: ev.getId() ?? "",
			sender,
			senderDisplayName: sender.split(":")[0]?.replace("@", "") ?? sender,
			body: `[Widget: ${widgetName}]${widget?.blockedReason === "unsafe-widget-url" ? " (blocked URL)" : ""}`,
			timestamp: ev.getTs(),
			isOwn: sender === myUserId,
			isBot: isAgentUser(sender),
			isEdited: false,
			isRedacted: false,
			msgType: "m.widget",
			url: widget?.url,
			widget: widget ?? undefined,
		};
	}

	// m.room.message und aehnliche
	if (!content || content.msgtype === undefined) return null;

	const sender = ev.getSender() ?? "";
	const info = content.info as Record<string, unknown> | undefined;
	const relates = content["m.relates_to"] as Record<string, unknown> | undefined;

	// Edit-Events (m.replace) nicht als separate Nachricht anzeigen
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

/** Konvertiert einen Room in RoomInfo. SDK-Methoden fuer Name, DM-Erkennung, Avatar. */
export function resolveRoom(room: Room, client?: MatrixClient): RoomInfo {
	const membership = room.getMyMembership() as "join" | "invite" | "leave";
	const lastEvent = room.getLastLiveEvent();
	const lastContent = lastEvent?.getContent() as Record<string, unknown> | undefined;
	const notifs = room.getUnreadNotificationCount();

	// DM-Erkennung: m.direct Account-Data — einzige zuverlaessige Quelle
	let dmUserId: string | undefined;
	if (client) {
		const directEvent = client.getAccountData(EventType.Direct);
		const directMap: Record<string, string[]> = directEvent?.getContent() ?? {};
		for (const [userId, roomIds] of Object.entries(directMap)) {
			if (roomIds.includes(room.roomId)) {
				dmUserId = userId;
				break;
			}
		}
	}
	const inviterUserId = room.getDMInviter() || undefined;

	// SDK: Presence fuer DMs
	const dmUser = dmUserId ? client?.getUser(dmUserId) : undefined;

	// Name: Bei DMs immer Display-Name des anderen Users, sonst SDK room.name
	let name: string;
	if (dmUserId) {
		const dmMember = room.getMember(dmUserId);
		const sdkName = room.name;
		const sdkNameUsable =
			sdkName && sdkName !== "Empty room" && sdkName !== room.roomId && !sdkName.startsWith("@");
		name =
			(sdkNameUsable ? sdkName : null) ??
			(dmMember?.name && dmMember.name !== dmUserId ? dmMember.name : null) ??
			dmUser?.displayName ??
			dmUserId.split(":")[0]?.replace("@", "") ??
			dmUserId;
	} else {
		name = room.name ?? room.roomId;
	}

	return {
		roomId: room.roomId,
		name,
		topic: (
			room.currentState.getStateEvents("m.room.topic", "")?.getContent() as
				| Record<string, unknown>
				| undefined
		)?.topic as string | undefined,
		memberCount: room.getInvitedAndJoinedMemberCount(),
		unreadCount: typeof notifs === "number" ? notifs : 0,
		lastMessage: membership === "invite" ? undefined : (lastContent?.body as string | undefined),
		lastTimestamp: lastEvent?.getTs(),
		avatarUrl: room.getMxcAvatarUrl() ?? undefined,
		membership,
		dmUserId,
		inviterUserId,
		isOnline: dmUser?.currentlyActive ?? false,
		isFavourite: !!room.tags?.["m.favourite"],
		isLowPriority: !!room.tags?.["m.lowpriority"],
	};
}
