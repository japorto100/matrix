"use client";

// useAttachments — Phase 22f / AC51-AC56
// Manages staged image attachments before sending.
// toRequestAttachments() converts to base64 for BFF.

import { useCallback, useRef, useState } from "react";

export interface StagedAttachment {
	id: string;
	file: File;
	previewUrl: string;
	name: string;
}

export interface RequestAttachment {
	base64: string;
	mime_type: string;
	name: string;
}

const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/gif", "image/webp"]);
const MAX_FILES = 5;
const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

let attachIdCounter = 0;
function attachId() {
	return `att-${Date.now()}-${(attachIdCounter++).toString(36)}`;
}

async function fileToBase64(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => {
			const result = reader.result as string;
			// Strip the data:mime/type;base64, prefix
			resolve(result.split(",")[1] ?? "");
		};
		reader.onerror = () => reject(reader.error);
		reader.readAsDataURL(file);
	});
}

export interface UseAttachmentsReturn {
	attachments: StagedAttachment[];
	addFiles: (files: FileList | File[]) => void;
	removeAttachment: (id: string) => void;
	clearAttachments: () => void;
	toRequestAttachments: () => Promise<RequestAttachment[]>;
	hasAttachments: boolean;
}

export function useAttachments(): UseAttachmentsReturn {
	const [attachments, setAttachments] = useState<StagedAttachment[]>([]);
	// Keep track of object URLs to revoke on cleanup
	const urlsRef = useRef<Set<string>>(new Set());

	const addFiles = useCallback((files: FileList | File[]) => {
		const arr = Array.from(files).filter((f) => ALLOWED_TYPES.has(f.type) && f.size <= MAX_BYTES);
		setAttachments((prev) => {
			const slots = MAX_FILES - prev.length;
			if (slots <= 0) return prev;
			const toAdd: StagedAttachment[] = arr.slice(0, slots).map((file) => {
				const previewUrl = URL.createObjectURL(file);
				urlsRef.current.add(previewUrl);
				return { id: attachId(), file, previewUrl, name: file.name };
			});
			return [...prev, ...toAdd];
		});
	}, []);

	const removeAttachment = useCallback((id: string) => {
		setAttachments((prev) => {
			const found = prev.find((a) => a.id === id);
			if (found) {
				URL.revokeObjectURL(found.previewUrl);
				urlsRef.current.delete(found.previewUrl);
			}
			return prev.filter((a) => a.id !== id);
		});
	}, []);

	const clearAttachments = useCallback(() => {
		setAttachments((prev) => {
			for (const a of prev) {
				URL.revokeObjectURL(a.previewUrl);
				urlsRef.current.delete(a.previewUrl);
			}
			return [];
		});
	}, []);

	const toRequestAttachments = useCallback(async (): Promise<RequestAttachment[]> => {
		return Promise.all(
			attachments.map(async (a) => ({
				base64: await fileToBase64(a.file),
				mime_type: a.file.type,
				name: a.name,
			})),
		);
	}, [attachments]);

	return {
		attachments,
		addFiles,
		removeAttachment,
		clearAttachments,
		toRequestAttachments,
		hasAttachments: attachments.length > 0,
	};
}
