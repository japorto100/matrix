"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import { EventType, type MatrixClient, MsgType } from "matrix-js-sdk";
import { useCallback, useRef, useState } from "react";

/**
 * Eine einzelne File in der Upload-Queue.
 *
 * Lifecycle: `pending` → `uploading` → `done` | `error`.
 * Bei `error` kann per `retry()` zurueck auf `pending` gesetzt werden.
 */
export interface UploadQueueItem {
	id: string;
	file: File;
	previewUrl?: string;
	status: "pending" | "uploading" | "done" | "error";
	progress: number;
	error?: string;
}

export interface UseUploadQueueReturn {
	items: UploadQueueItem[];
	addFiles: (files: FileList | File[]) => void;
	removeItem: (id: string) => void;
	retryItem: (id: string) => void;
	clearDone: () => void;
	/**
	 * N4: ersetzt die Datei eines Queue-Items (z.B. nach Crop/Rotate im
	 * ImageEditor). Revoked den alten previewUrl vor Ersatz.
	 */
	replaceFile: (id: string, newFile: File) => void;
	uploadAll: (caption: string) => Promise<void>;
	isUploading: boolean;
	/** `true` wenn mindestens eine Datei in der Queue ist (beliebiger Status). */
	hasItems: boolean;
}

const MAX_FILE_SIZE_MB = 500;

function mimeToMsgtype(mime: string): MsgType {
	if (mime.startsWith("image/")) return MsgType.Image;
	if (mime.startsWith("video/")) return MsgType.Video;
	if (mime.startsWith("audio/")) return MsgType.Audio;
	return MsgType.File;
}

async function compressImage(file: File): Promise<File> {
	if (!file.type.startsWith("image/") || file.size <= 5 * 1024 * 1024) return file;
	const imageCompression = (await import("browser-image-compression")).default;
	return imageCompression(file, {
		maxSizeMB: 5,
		maxWidthOrHeight: 3840,
		useWebWorker: true,
	});
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

function makePreviewUrl(file: File): string | undefined {
	if (file.type.startsWith("image/") || file.type.startsWith("video/")) {
		return URL.createObjectURL(file);
	}
	return undefined;
}

/**
 * Multi-File Upload-Queue Hook fuer MessageComposer.
 *
 * Verwaltet eine Liste von Dateien mit je eigenem Status und Fortschritt.
 * Erweiterung des frueheren Single-File-pendingFile-State: unterstuetzt
 * Drag-Drop-mehrfach-Auswahl, Per-Item Progress, Retry bei Fehler, Cancel
 * pro Item.
 *
 * Uploads laufen sequentiell durch die Queue — das schont die Bandbreite
 * und vermeidet dass bei Homeserver-Rate-Limits alle files gleichzeitig
 * 429en.
 */
export function useUploadQueue(
	client: MatrixClient,
	roomId: string,
	onError: (message: string) => void,
): UseUploadQueueReturn {
	const alive = useAlive();
	const [items, setItems] = useState<UploadQueueItem[]>([]);
	const [isUploading, setIsUploading] = useState(false);
	const counterRef = useRef(0);

	const addFiles = useCallback(
		(files: FileList | File[]) => {
			const list = Array.from(files);
			const accepted: UploadQueueItem[] = [];
			for (const file of list) {
				if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
					onError(`${file.name}: zu gross (max. ${MAX_FILE_SIZE_MB} MB)`);
					continue;
				}
				counterRef.current += 1;
				accepted.push({
					id: `upload-${Date.now()}-${counterRef.current}`,
					file,
					previewUrl: makePreviewUrl(file),
					status: "pending",
					progress: 0,
				});
			}
			if (accepted.length > 0) setItems((prev) => [...prev, ...accepted]);
		},
		[onError],
	);

	const removeItem = useCallback((id: string) => {
		setItems((prev) => {
			const target = prev.find((it) => it.id === id);
			if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
			return prev.filter((it) => it.id !== id);
		});
	}, []);

	const replaceFile = useCallback((id: string, newFile: File) => {
		setItems((prev) =>
			prev.map((it) => {
				if (it.id !== id) return it;
				if (it.previewUrl) URL.revokeObjectURL(it.previewUrl);
				return {
					...it,
					file: newFile,
					previewUrl: makePreviewUrl(newFile),
					status: "pending",
					progress: 0,
					error: undefined,
				};
			}),
		);
	}, []);

	const retryItem = useCallback((id: string) => {
		setItems((prev) =>
			prev.map((it) =>
				it.id === id && it.status === "error"
					? { ...it, status: "pending", progress: 0, error: undefined }
					: it,
			),
		);
	}, []);

	const clearDone = useCallback(() => {
		setItems((prev) => {
			// Object-URLs von done-Items vor dem Filter revozieren (Memory-Leak-Fix).
			for (const it of prev) {
				if (it.status === "done" && it.previewUrl) URL.revokeObjectURL(it.previewUrl);
			}
			return prev.filter((it) => it.status !== "done");
		});
	}, []);

	const uploadOne = useCallback(
		async (item: UploadQueueItem, caption: string) => {
			const setStatus = (patch: Partial<UploadQueueItem>) => {
				setItems((prev) => prev.map((it) => (it.id === item.id ? { ...it, ...patch } : it)));
			};

			setStatus({ status: "uploading", progress: 0, error: undefined });

			try {
				const fileToUpload = await compressImage(item.file);
				const dims = await readFileDimensions(fileToUpload);
				const info: Record<string, unknown> = {
					mimetype: fileToUpload.type,
					size: fileToUpload.size,
				};
				if (dims.w) info.w = dims.w;
				if (dims.h) info.h = dims.h;
				if (dims.duration) info.duration = dims.duration;

				const uploadRes = await client.uploadContent(fileToUpload, {
					name: item.file.name,
					progressHandler: ({ loaded, total }) => {
						if (alive()) {
							setStatus({
								progress: total > 0 ? Math.round((loaded / total) * 100) : 0,
							});
						}
					},
				});

				await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
					roomId,
					EventType.RoomMessage,
					{
						msgtype: mimeToMsgtype(item.file.type),
						body: caption || item.file.name,
						url: uploadRes.content_uri,
						filename: item.file.name,
						info,
					},
				);

				if (alive()) setStatus({ status: "done", progress: 100 });
			} catch (err) {
				const message = err instanceof Error ? err.message : String(err);
				console.error("[uploadQueue] upload failed:", err);
				if (alive()) setStatus({ status: "error", error: message });
			}
		},
		[client, roomId, alive],
	);

	const uploadAll = useCallback(
		async (caption: string) => {
			setIsUploading(true);
			try {
				// Snapshot der aktuellen pending-items. Retrys waehrend laufendem Upload
				// werden erst im naechsten uploadAll-Call beruecksichtigt.
				const pending: UploadQueueItem[] = [];
				setItems((prev) => {
					for (const it of prev) if (it.status === "pending") pending.push(it);
					return prev;
				});
				for (const item of pending) {
					if (!alive()) break;
					await uploadOne(item, caption);
				}
			} finally {
				if (alive()) setIsUploading(false);
			}
		},
		[uploadOne, alive],
	);

	return {
		items,
		addFiles,
		removeItem,
		retryItem,
		clearDone,
		replaceFile,
		uploadAll,
		isUploading,
		hasItems: items.length > 0,
	};
}
