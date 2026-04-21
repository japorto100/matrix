/**
 * Matrix utility functions — media URLs, formatting, colors.
 * Extracted from types.ts (Phase 1, exec-07).
 */

/**
 * mxc://server/mediaId → HTTP-Download-URL
 * QW-4: Nutzt den lokalen Media-Proxy (/api/matrix/media) für Authenticated Media.
 * Der Proxy sendet den Auth-Header server-seitig, Browser braucht keinen.
 */
export function mxcToHttp(mxcUrl: string, _homeserverUrl?: string): string {
	if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
	return `/api/matrix/media?mxc=${encodeURIComponent(mxcUrl.slice(6))}`;
}

/**
 * mxc://server/mediaId → HTTP-Thumbnail-URL
 * QW-4: Nutzt den lokalen Media-Proxy mit Thumbnail-Parameter.
 */
export function mxcToThumbnail(
	mxcUrl: string,
	_homeserverUrl?: string,
	width = 800,
	height = 600,
): string {
	if (!mxcUrl.startsWith("mxc://")) return mxcUrl;
	return `/api/matrix/media?mxc=${encodeURIComponent(mxcUrl.slice(6))}&thumbnail=1&w=${width}&h=${height}`;
}

/** Hash-basierte Farbzuordnung fuer Avatare/Sender. */
export function hashColor(name: string, palette: string[]): string {
	let hash = 0;
	for (let i = 0; i < name.length; i++) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
	return palette[Math.abs(hash) % palette.length] ?? palette[0] ?? "";
}

/** Formatiert Bytes in lesbare Groesse (KB, MB, …) */
export function formatFileSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Aggregiert `unreadCount` pro Space durch Summierung der Counts aller
 * direkten Child-Rooms. Sub-Spaces werden (noch) nicht rekursiv aufsummiert.
 *
 * Parameter sind minimal getyped (duck-typing) damit Consumer nicht den
 * vollen SpaceInfo/RoomInfo-Import brauchen.
 *
 * Returns: Record<spaceId, totalUnread> — Spaces ohne unread erscheinen mit 0.
 */
export function aggregateSpaceUnread(
	spaces: Array<{ roomId: string; childRoomIds: string[] }>,
	rooms: Array<{ roomId: string; unreadCount: number }>,
): Record<string, number> {
	const unreadById = new Map<string, number>();
	for (const r of rooms) unreadById.set(r.roomId, r.unreadCount ?? 0);

	const result: Record<string, number> = {};
	for (const space of spaces) {
		let total = 0;
		for (const childId of space.childRoomIds) {
			total += unreadById.get(childId) ?? 0;
		}
		result[space.roomId] = total;
	}
	return result;
}
