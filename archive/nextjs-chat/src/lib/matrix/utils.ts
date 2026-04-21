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
