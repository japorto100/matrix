/**
 * Matrix type definitions — interfaces only.
 * Utility functions: see ./utils.ts
 * Resolvers: see ./resolvers.ts
 */

/** Matrix-Credentials die der Client braucht. */
export interface MatrixCredentials {
	homeserverUrl: string;
	userId: string;
	accessToken: string;
	deviceId?: string;
}

import type { MatrixWidgetSummary } from "./widgets";

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
	// Feature 030: Matrix widget/app host metadata.
	widget?: MatrixWidgetSummary;
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
	// Membership-State des eigenen Users
	membership: "join" | "invite" | "leave";
	// DM: User-ID des anderen Users (SDK guessDMUserId)
	dmUserId?: string;
	// DM: Wer hat uns eingeladen (SDK getDMInviter)
	inviterUserId?: string;
	// B-6: Presence
	isOnline?: boolean;
	// Favourites (m.favourite Tag)
	isFavourite?: boolean;
	// Low-Priority (m.lowpriority Tag)
	isLowPriority?: boolean;
}

export { isAgentUser, resolveMessage, resolveRoom } from "./resolvers";
// ─── Re-Exports für Backward-Kompatibilität ──────────────────────────────────
// Bestehende Imports wie `import { mxcToHttp } from "@matrix/lib/types"` funktionieren weiterhin.
// Neue Imports sollten direkt aus ./utils oder ./resolvers kommen.
export { formatFileSize, mxcToHttp, mxcToThumbnail } from "./utils";
